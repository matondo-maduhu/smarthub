"""Usajili, kuingia (barua pepe/simu/Google), kutoka na ulinzi wa fomu (CSRF)."""
import hmac
import json
import re
import secrets
import time
import urllib.parse
import urllib.request
from datetime import date
from functools import wraps

from flask import (Blueprint, abort, flash, g, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import db
import models
from config import Config

bp = Blueprint("auth", __name__)

USERNAME_RE = re.compile(r"^[a-z0-9_]{3,20}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


# ---------- Ulinzi wa fomu (CSRF) ----------
def csrf_token():
    tok = session.get("_csrf")
    if not tok:
        tok = secrets.token_hex(16)
        session["_csrf"] = tok
    return tok


@bp.before_app_request
def _csrf_protect():
    if request.method == "POST":
        sent = request.form.get("_csrf", "")
        if not sent or not hmac.compare_digest(sent, session.get("_csrf", "")):
            abort(400)


# ---------- Vifaa vidogo ----------
def google_enabled():
    return bool(Config.GOOGLE_CLIENT_ID and Config.GOOGLE_CLIENT_SECRET)


def safe_next(target):
    """Inaruhusu kurudi kwenye kurasa za ndani tu (inazuia open redirect)."""
    if target and target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    return None


def login_user(uid):
    session.clear()
    session["uid"] = uid
    session.pop("pv", None)  # alama ya nenosiri itawekwa kwenye ombi lijalo
    session.permanent = True


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user:
            flash("Ingia kwanza ili uendelee.", "info")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def normalize_phone(raw):
    """Namba ya Tanzania -> +255XXXXXXXXX, au None kama si sahihi."""
    s = re.sub(r"[\s\-()]", "", raw or "")
    if s.startswith("+"):
        s = s[1:]
    if s.startswith("255"):
        s = s[3:]
    elif s.startswith("0"):
        s = s[1:]
    return "+255" + s if re.fullmatch(r"[67]\d{8}", s) else None


def parse_identifier(raw):
    raw = (raw or "").strip()
    if "@" in raw:
        email = raw.lower()
        if len(email) <= 254 and EMAIL_RE.match(email):
            return "email", email
        return None, None
    phone = normalize_phone(raw)
    return ("phone", phone) if phone else (None, None)


def age_on(born, today=None):
    today = today or date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def check_common(display_name, username, birth_raw, age_ok):
    """Ukaguzi wa sehemu zinazofanana kwenye usajili wa kawaida na wa Google."""
    errors = []
    name = " ".join((display_name or "").split())
    if not 2 <= len(name) <= 40:
        errors.append("Jina la kuonyesha liwe na herufi 2 hadi 40.")

    uname = (username or "").strip().lower()
    if not USERNAME_RE.match(uname):
        errors.append("Jina la mtumiaji liwe na herufi 3 hadi 20: herufi ndogo, namba na _ tu.")
    elif models.username_exists(uname):
        errors.append("Jina hilo la mtumiaji tayari limechukuliwa.")

    born = None
    try:
        born = date.fromisoformat((birth_raw or "").strip())
        if born.year < 1900 or born > date.today():
            raise ValueError
    except ValueError:
        born = None
        errors.append("Weka tarehe sahihi ya kuzaliwa.")
    else:
        if age_on(born) < 18:
            errors.append("Unatakiwa kuwa na miaka 18 au zaidi ili kutumia app hii.")

    if not age_ok:
        errors.append("Thibitisha kuwa una miaka 18 au zaidi.")
    return {"display_name": name, "username": uname, "birth_date": born}, errors


# ---------- Kuzuia kujaribu nenosiri mara nyingi ----------
_FAILS = {}  # akiba ya kumbukumbu ikiwa database haipatikani
MAX_FAILS = 5
WINDOW = 600  # sekunde


def _fail_key(identifier):
    import hashlib
    raw = f"{request.remote_addr}|{identifier.lower()}"
    return "fail|" + hashlib.sha256(raw.encode()).hexdigest()[:32]


def _load_fails(key):
    """Majaribio yanahifadhiwa kwenye database (jedwali kv) ili yafanye kazi hata Vercel ikianzisha
    nakala nyingi za app; yasipopatikana tunatumia kumbukumbu."""
    now = time.time()
    try:
        row = db.query("SELECT value FROM kv WHERE key = %s", (key,), one=True)
        ts = [float(x) for x in (row["value"].split(",") if row and row["value"] else []) if x]
    except Exception:
        ts = list(_FAILS.get(key, []))
    return [t for t in ts if now - t < WINDOW]


def _store_fails(key, ts):
    try:
        if ts:
            db.execute("INSERT INTO kv (key, value, updated_at) VALUES (%s, %s, CURRENT_TIMESTAMP) "
                       "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP",
                       (key, ",".join(f"{t:.0f}" for t in ts[-MAX_FAILS * 2:])))
        else:
            db.execute("DELETE FROM kv WHERE key = %s", (key,))
    except Exception:
        if ts: _FAILS[key] = ts
        else: _clear_fails(key)


def _recent_fails(key):
    return _load_fails(key)


def _add_fail(key):
    _store_fails(key, _load_fails(key) + [time.time()])


def _clear_fails(key):
    _store_fails(key, [])


# ---------- Njia (routes) ----------
@bp.route("/jisajili", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("home"))
    form, errors = {}, []
    if request.method == "POST":
        form = {k: request.form.get(k, "").strip()
                for k in ("identifier", "display_name", "username", "birth_date")}
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")
        age_ok = request.form.get("age_ok") == "1"

        kind, ident = parse_identifier(form["identifier"])
        if not kind:
            errors.append("Weka barua pepe sahihi au namba ya simu ya Tanzania (mfano 0712345678).")
        common, errs = check_common(form["display_name"], form["username"], form["birth_date"], age_ok)
        errors += errs
        if len(password) < 8:
            errors.append("Nenosiri liwe na herufi 8 au zaidi.")
        elif len(password) > 128:
            errors.append("Nenosiri ni refu mno.")
        elif password != password2:
            errors.append("Manenosiri hayafanani.")

        if not errors:
            if kind == "email" and models.find_user_by_email(ident):
                errors.append("Barua pepe hii tayari imesajiliwa. Jaribu kuingia.")
            elif kind == "phone" and models.find_user_by_phone(ident):
                errors.append("Namba hii ya simu tayari imesajiliwa. Jaribu kuingia.")

        if not errors:
            try:
                uid = models.create_user(
                    username=common["username"],
                    display_name=common["display_name"],
                    birth_date=common["birth_date"],
                    email=ident if kind == "email" else None,
                    phone=ident if kind == "phone" else None,
                    password_hash=generate_password_hash(password),
                )
            except db.IntegrityError:
                errors.append("Taarifa hizi (barua pepe, simu au jina la mtumiaji) tayari zimetumika.")
            else:
                login_user(uid)
                flash("Karibu! Akaunti yako imeundwa.", "ok")
                return redirect(url_for("home"))
    return render_template("auth_register.html", form=form, errors=errors, active="wasifu"), (400 if errors else 200)


@bp.route("/ingia", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("home"))
    form, errors = {}, []
    next_url = safe_next(request.values.get("next"))
    if request.method == "POST":
        form = {"identifier": request.form.get("identifier", "").strip()}
        password = request.form.get("password", "")
        key = _fail_key(form["identifier"])

        if len(_recent_fails(key)) >= MAX_FAILS:
            errors.append("Umejaribu mara nyingi. Subiri dakika chache kisha ujaribu tena.")
        else:
            kind, ident = parse_identifier(form["identifier"])
            user = None
            if kind == "email":
                user = models.find_user_by_email(ident)
            elif kind == "phone":
                user = models.find_user_by_phone(ident)

            ok = bool(user and user["password_hash"]
                      and check_password_hash(user["password_hash"], password))
            if not ok:
                _add_fail(key)
                errors.append("Taarifa ulizoweka si sahihi.")
            elif user["is_banned"]:
                errors.append("Akaunti hii imesimamishwa.")
            else:
                _clear_fails(key)
                login_user(user["id"])
                return redirect(next_url or url_for("home"))
    return render_template("auth_login.html", form=form, errors=errors, next=next_url, active="wasifu"), (400 if errors else 200)


@bp.route("/weka-nenosiri/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Ukurasa wa kiungo alichotengeneza admin: mtumiaji anaweka nenosiri jipya mara moja."""
    key = _fail_key("reset")
    if len(_recent_fails(key)) >= MAX_FAILS:
        return render_template("auth_reset.html", state="limit", token=token, errors=[], active="wasifu"), 429
    user = models.reset_user_for_token(token)
    if not user:
        _add_fail(key)
        return render_template("auth_reset.html", state="invalid", token=token, errors=[], active="wasifu"), 404
    errors = []
    if request.method == "POST":
        pw, pw2 = request.form.get("password", ""), request.form.get("password2", "")
        if len(pw) < 8:
            errors.append("Nenosiri liwe na herufi 8 au zaidi.")
        elif len(pw) > 128:
            errors.append("Nenosiri ni refu mno.")
        elif pw != pw2:
            errors.append("Manenosiri hayafanani.")
        else:
            if models.consume_reset(token, generate_password_hash(pw)):
                _clear_fails(key)
                session.clear()
                flash("Nenosiri jipya limewekwa. Ingia sasa.", "ok")
                return redirect(url_for("auth.login"))
            return render_template("auth_reset.html", state="invalid", token=token, errors=[], active="wasifu"), 404
    return render_template("auth_reset.html", state="form", token=token, user=user, errors=errors,
                           active="wasifu"), (400 if errors else 200)


def password_stamp(user):
    """Alama inayobadilika nenosiri likibadilika: vikao vya vifaa vingine vinaisha."""
    import hashlib
    return hashlib.sha256((user["password_hash"] or "-").encode()).hexdigest()[:20]


@bp.route("/wasifu/nenosiri", methods=["POST"])
@login_required
def change_password():
    """Kubadilisha nenosiri. Anayeingia kwa Google tu (hana nenosiri) anaweza kuweka la kwanza."""
    key = f"pw|{g.user['id']}"
    current = request.form.get("current", "")
    new, new2 = request.form.get("new", ""), request.form.get("new2", "")
    has_pw = bool(g.user["password_hash"])
    msg = None
    if len(_recent_fails(key)) >= MAX_FAILS:
        msg = "Umejaribu mara nyingi mno. Subiri dakika chache kisha ujaribu tena."
    elif has_pw and not check_password_hash(g.user["password_hash"], current):
        _add_fail(key)
        msg = "Nenosiri la sasa si sahihi."
    elif len(new) < 8:
        msg = "Nenosiri jipya liwe na herufi 8 au zaidi."
    elif len(new) > 128:
        msg = "Nenosiri ni refu mno."
    elif new != new2:
        msg = "Manenosiri mapya hayafanani."
    elif has_pw and check_password_hash(g.user["password_hash"], new):
        msg = "Nenosiri jipya liwe tofauti na la sasa."
    if msg:
        flash(msg, "error")
    else:
        _clear_fails(key)
        models.set_password(g.user["id"], generate_password_hash(new))
        session["pv"] = password_stamp(models.get_user(g.user["id"]))  # kifaa hiki kinabaki ndani
        flash("Nenosiri limebadilishwa. Vifaa vingine vimetolewa kwenye akaunti.", "ok")
    return redirect(url_for("mipangilio"))


@bp.route("/toka", methods=["POST"])
def logout():
    session.clear()
    flash("Umetoka kwenye akaunti.", "info")
    return redirect(url_for("home"))


# ---------- Google ----------
def _post_form(url, data):
    req = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(data).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


def _get_json(url, access_token):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


def _redirect_uri():
    return Config.GOOGLE_REDIRECT_URI or url_for("auth.google_callback", _external=True)


@bp.route("/google")
def google():
    if not google_enabled():
        flash("Kuingia kwa Google bado hakijawashwa.", "error")
        return redirect(url_for("auth.login"))
    state = secrets.token_urlsafe(24)
    session["g_state"] = state
    session["g_next"] = safe_next(request.args.get("next")) or ""
    params = {
        "client_id": Config.GOOGLE_CLIENT_ID,
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    return redirect(GOOGLE_AUTH_URL + "?" + urllib.parse.urlencode(params))


@bp.route("/google/rudi")
def google_callback():
    expected = session.pop("g_state", "")
    next_url = session.pop("g_next", "") or None
    got = request.args.get("state", "")
    if (not google_enabled() or request.args.get("error") or not expected
            or not hmac.compare_digest(got, expected) or not request.args.get("code")):
        flash("Kuingia kwa Google kumeshindikana. Jaribu tena.", "error")
        return redirect(url_for("auth.login"))

    try:
        token = _post_form(GOOGLE_TOKEN_URL, {
            "code": request.args["code"],
            "client_id": Config.GOOGLE_CLIENT_ID,
            "client_secret": Config.GOOGLE_CLIENT_SECRET,
            "redirect_uri": _redirect_uri(),
            "grant_type": "authorization_code",
        })
        info = _get_json(GOOGLE_USERINFO_URL, token["access_token"])
    except Exception:
        flash("Hatukuweza kuwasiliana na Google. Jaribu tena.", "error")
        return redirect(url_for("auth.login"))

    gid = info.get("sub")
    email = (info.get("email") or "").lower()
    if not gid or not email or not info.get("email_verified"):
        flash("Akaunti yako ya Google haina barua pepe iliyothibitishwa.", "error")
        return redirect(url_for("auth.login"))

    user = models.find_user_by_google(gid)
    if user:
        if user["is_banned"]:
            flash("Akaunti hii imesimamishwa.", "error")
            return redirect(url_for("auth.login"))
        login_user(user["id"])
        return redirect(next_url or url_for("home"))

    if models.find_user_by_email(email):
        flash("Barua pepe hii tayari imesajiliwa kwa nenosiri. Ingia kwa nenosiri.", "error")
        return redirect(url_for("auth.login"))

    session["pending_google"] = {
        "sub": gid, "email": email,
        "name": (info.get("name") or "")[:40],
        "picture": info.get("picture") or "",
    }
    return redirect(url_for("auth.complete"))


@bp.route("/kamilisha", methods=["GET", "POST"])
def complete():
    """Mtumiaji mpya wa Google anakamilisha jina, tarehe ya kuzaliwa na uthibitisho wa umri."""
    pending = session.get("pending_google")
    if g.user or not pending:
        return redirect(url_for("home"))
    suggestion = re.sub(r"[^a-z0-9_]", "", pending["email"].split("@")[0].lower())[:20]
    form, errors = {"display_name": pending["name"], "username": suggestion}, []
    if request.method == "POST":
        form = {k: request.form.get(k, "").strip() for k in ("display_name", "username", "birth_date")}
        age_ok = request.form.get("age_ok") == "1"
        common, errors = check_common(form["display_name"], form["username"], form["birth_date"], age_ok)
        if not errors:
            try:
                uid = models.create_user(
                    username=common["username"],
                    display_name=common["display_name"],
                    birth_date=common["birth_date"],
                    email=pending["email"],
                    google_id=pending["sub"],
                    avatar_url=pending["picture"] or None,
                    is_verified=True,
                )
            except db.IntegrityError:
                errors.append("Taarifa hizi tayari zimetumika. Jaribu jina lingine la mtumiaji.")
            else:
                login_user(uid)
                flash("Karibu! Akaunti yako imeundwa.", "ok")
                return redirect(url_for("home"))
    return render_template("auth_complete.html", form=form, errors=errors, email=pending["email"], active="wasifu"), (400 if errors else 200)
