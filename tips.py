"""Jamvi la mikeka: kuweka, kuorodhesha, kununua, kupenda, maoni, matokeo na viwango."""
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from flask import (Blueprint, abort, flash, g, redirect, render_template,
                   request, url_for)

import auth
import db
import football
import models
from config import Config

bp = Blueprint("tips", __name__, url_prefix="/jamvi")

STATUS_FILTERS = {"zote": None, "open": "open", "won": "won", "lost": "lost"}
LEAGUES = ["Ligi Kuu Tanzania", "Premier League", "La Liga", "Serie A", "Bundesliga",
           "Ligue 1", "Champions League", "Europa League", "Mengineyo"]


def _int(raw):
    return int(raw) if re.fullmatch(r"[0-9]{1,9}", raw or "") else None


def _parse_odds(raw):
    raw = (raw or "").replace(",", ".").strip()
    if not re.fullmatch(r"[0-9]{1,4}(\.[0-9]{1,2})?", raw):
        return None
    d = Decimal(raw)
    return float(d) if Decimal("1.01") <= d <= Decimal("1000") else None


def _parse_local_time(raw):
    """Fomu inatuma saa za mtumiaji (Tanzania, UTC+3); tunahifadhi UTC."""
    try:
        d = datetime.strptime((raw or "").strip(), "%Y-%m-%dT%H:%M")
    except ValueError:
        return None
    return d.replace(tzinfo=models.EAT).astimezone(timezone.utc)


def _get_or_404(tip_id):
    tip = models.get_tip(tip_id, g.user["id"] if g.user else None)
    if not tip:
        abort(404)
    return tip


def _back(tip_id):
    return redirect(url_for("tips.detail", tip_id=tip_id))


# ---------- Orodha ----------
@bp.route("")
def index():
    football.maybe_settle()
    hali = request.args.get("hali", "zote")
    if hali not in STATUS_FILTERS:
        hali = "zote"
    page = max(1, _int(request.args.get("ukurasa")) or 1)
    per = Config.TIPS_PER_PAGE
    rows = models.list_tips(g.user["id"] if g.user else None, status=STATUS_FILTERS[hali],
                            limit=per + 1, offset=(page - 1) * per)
    return render_template("jamvi.html", active="jamvi", tips=rows[:per], hali=hali,
                           page=page, has_next=len(rows) > per)


@bp.route("/viwango")
def leaderboard():
    rows = models.leaderboard(Config.MIN_SETTLED_FOR_RANK)
    return render_template("viwango.html", active="jamvi", rows=rows, min_settled=Config.MIN_SETTLED_FOR_RANK)


@bp.route("/mtabiri/<username>")
def tipster(username):
    person = models.get_user_by_username(username.lower())
    if not person:
        abort(404)
    rows = models.list_tips(g.user["id"] if g.user else None, user_id=person["id"], limit=30)
    return render_template("mtabiri.html", active="jamvi", person=person, tips=rows,
                           stats=models.tipster_stats(person["id"]))


# ---------- Kuweka mkeka ----------
@bp.route("/weka", methods=["GET", "POST"])
@auth.login_required
def new():
    if football.configured() and not Config.ALLOW_MANUAL_TIPS:
        return _new_api()
    form, errors = {"price": "0"}, []
    if request.method == "POST":
        form = {k: request.form.get(k, "").strip()
                for k in ("title", "league", "pick", "odds", "price", "starts_at", "body")}
        title = " ".join(form["title"].split())
        league = " ".join(form["league"].split())
        pick = " ".join(form["pick"].split())
        body = form["body"].strip()
        odds = _parse_odds(form["odds"])
        price = _int(form["price"] or "0")
        starts = _parse_local_time(form["starts_at"])
        now = datetime.now(timezone.utc)

        if not 3 <= len(title) <= 80:
            errors.append("Jina la mchezo liwe na herufi 3 hadi 80 (mfano Simba vs Yanga).")
        if len(league) > 40:
            errors.append("Jina la ligi ni refu mno (herufi 40 juu).")
        if not 2 <= len(pick) <= 120:
            errors.append("Mkeka wako uwe na herufi 2 hadi 120.")
        if len(body) > 500:
            errors.append("Maelezo ya ziada yasizidi herufi 500.")
        if odds is None:
            errors.append("Odds ziwe namba kati ya 1.01 na 1000 (mfano 1.85).")
        if price is None or (price != 0 and not 5 <= price <= Config.TIP_MAX_PRICE):
            errors.append(f"Bei iwe 0 (bure) au kati ya coin 5 na {Config.TIP_MAX_PRICE}.")
        if starts is None:
            errors.append("Weka tarehe na saa sahihi ya mchezo.")
        elif starts <= now + timedelta(minutes=5):
            errors.append("Mchezo lazima uanze angalau dakika 5 kutoka sasa.")
        elif starts > now + timedelta(days=30):
            errors.append("Mchezo usizidi siku 30 mbele.")

        if not errors:
            times = models.recent_times("tips", g.user["id"], Config.MAX_TIPS_PER_DAY)
            if len(times) >= Config.MAX_TIPS_PER_DAY and times[-1] > now - timedelta(hours=24):
                errors.append(f"Umefikia kikomo cha mikeka {Config.MAX_TIPS_PER_DAY} kwa siku. Jaribu kesho.")

        if not errors:
            tip_id = models.create_tip(g.user["id"], title=title, league=league, pick=pick,
                                       body=body, odds=odds, price=price, starts_at=starts)
            flash("Mkeka wako umewekwa.", "ok")
            return _back(tip_id)
    return render_template("jamvi_weka.html", active="jamvi", form=form, errors=errors,
                           leagues=LEAGUES, max_price=Config.TIP_MAX_PRICE, fee=Config.TIP_FEE_PCT), (400 if errors else 200)


def _new_api():
    """Kuweka mkeka kwa mechi halisi: mechi -> chaguo -> kampuni -> bei. Odds zinatoka kwenye huduma, si kwa mtumiaji."""
    now = datetime.now(timezone.utc)
    q = request.values.get("q", "").strip()[:40]
    fid = _int(request.values.get("mechi"))
    ctx = dict(active="jamvi", api_mode=True, q=q, fixtures=[], fixture=None, markets=[], books=[],
               chosen=None, svc_error=None, errors=[], form={"price": "0", "body": ""},
               max_price=Config.TIP_MAX_PRICE, fee=Config.TIP_FEE_PCT, leagues=[])
    if fid is None:
        ctx["svc_error"] = football.ensure_fixtures()
        ctx["fixtures"] = football.list_fixtures(q)
        return render_template("jamvi_weka.html", **ctx)

    fx = football.get_fixture(fid)
    if not fx or fx["status"] != "NS" or fx["kickoff"] <= now + timedelta(minutes=5):
        flash("Mechi hii haipatikani tena kwa mikeka (imeanza au imeondolewa). Chagua nyingine.", "error")
        return redirect(url_for("tips.new"))
    ctx["fixture"] = fx
    rows = []
    try:
        rows = football.get_odds(fid)
    except football.FootballError as e:
        ctx["svc_error"] = str(e)
    ctx["markets"] = football.options(rows, fx["home"], fx["away"])
    valid = {o["key"]: o for mk in ctx["markets"] for o in mk["options"]}
    chosen = request.values.get("chaguo", "")
    if chosen in valid:
        market, selection = chosen.split(":", 1)
        ctx["chosen"] = valid[chosen]
        ctx["books"] = football.bookmakers_for(rows, market, selection)

    if request.method == "POST":
        errors = ctx["errors"]
        price = _int(request.form.get("price", "0") or "0")
        body = request.form.get("body", "").strip()
        book = _int(request.form.get("bookmaker", ""))
        ctx["form"] = {"price": request.form.get("price", "0"), "body": body, "bookmaker": book}
        picked = next((b for b in ctx["books"] if b["id"] == book), None)
        if not ctx["chosen"]:
            errors.append("Chagua mkeka wako kwenye orodha.")
        elif picked is None:
            errors.append("Chagua kampuni ya kubashiri ambayo odds zake umetumia.")
        if len(body) > 500:
            errors.append("Maelezo ya ziada yasizidi herufi 500.")
        if price is None or (price != 0 and not 5 <= price <= Config.TIP_MAX_PRICE):
            errors.append(f"Bei iwe 0 (bure) au kati ya coin 5 na {Config.TIP_MAX_PRICE}.")
        if not errors:
            times = models.recent_times("tips", g.user["id"], Config.MAX_TIPS_PER_DAY)
            if len(times) >= Config.MAX_TIPS_PER_DAY and times[-1] > now - timedelta(hours=24):
                errors.append(f"Umefikia kikomo cha mikeka {Config.MAX_TIPS_PER_DAY} kwa siku. Jaribu kesho.")
        if not errors and db.query(
                "SELECT 1 AS x FROM tips WHERE user_id = %s AND fixture_id = %s AND market = %s AND selection = %s",
                (g.user["id"], fid, market, selection), one=True):
            errors.append("Tayari umeshaweka mkeka huu kwa mechi hii.")
        if not errors:
            tip_id = models.create_tip(
                g.user["id"], title=f"{fx['home']} vs {fx['away']}", league=fx["league_name"][:40],
                pick=ctx["chosen"]["label"], body=body, odds=picked["odd"], price=price,
                starts_at=fx["kickoff"], fixture_id=fid, market=market, selection=selection,
                bookmaker=picked["name"])
            flash(f"Mkeka umewekwa kwa odds {picked['odd']:.2f} ({picked['name']}).", "ok")
            return _back(tip_id)
        return render_template("jamvi_weka.html", **ctx), 400
    return render_template("jamvi_weka.html", **ctx)


# ---------- Ukurasa wa mkeka ----------
@bp.route("/<int:tip_id>")
def detail(tip_id):
    football.maybe_settle()
    tip = _get_or_404(tip_id)
    is_admin = bool(g.user and g.user["is_admin"])
    auto = bool(tip["fixture_id"])  # mkeka wa mechi halisi unahukumiwa na mfumo
    return render_template(
        "mkeka.html", active="jamvi", t=tip, comments=models.list_comments(tip_id),
        fixture=football.get_fixture(tip["fixture_id"]) if auto else None, auto=auto,
        can_settle=is_admin or (not auto and tip["is_owner"] and tip["status"] == "open" and tip["started"]),
        can_delete=tip["is_owner"] and tip["buyers"] == 0,
        is_admin=is_admin, fee=Config.TIP_FEE_PCT,
    )


@bp.route("/<int:tip_id>/nunua", methods=["POST"])
@auth.login_required
def buy(tip_id):
    _get_or_404(tip_id)
    try:
        res = models.purchase_tip(tip_id, g.user["id"], Config.TIP_FEE_PCT)
    except models.TipError as e:
        flash(str(e), "error")
    except models.InsufficientFunds:
        flash("Salio lako halitoshi. Nunua coin kwenye Pochi.", "error")
    except db.IntegrityError:
        flash("Tayari umeshanunua mkeka huu.", "info")
    else:
        flash(f"Umenunua mkeka kwa coin {res['price']}. Salio jipya: {res['balance']}.", "ok")
    return _back(tip_id)


@bp.route("/<int:tip_id>/penda", methods=["POST"])
@auth.login_required
def like(tip_id):
    _get_or_404(tip_id)
    try:
        models.toggle_like(tip_id, g.user["id"])
    except db.IntegrityError:
        pass  # mibofyo miwili kwa wakati mmoja; hali ni ileile
    return _back(tip_id)


# ---------- Maoni ----------
@bp.route("/<int:tip_id>/maoni", methods=["POST"])
@auth.login_required
def comment(tip_id):
    _get_or_404(tip_id)
    body = request.form.get("body", "").strip()
    if not 1 <= len(body) <= 500:
        flash("Maoni yawe na herufi 1 hadi 500.", "error")
        return _back(tip_id)
    times = models.recent_times("comments", g.user["id"], 5)
    if len(times) >= 5 and times[-1] > datetime.now(timezone.utc) - timedelta(seconds=60):
        flash("Unatuma maoni haraka mno. Subiri kidogo.", "error")
        return _back(tip_id)
    tip = _get_or_404(tip_id)
    models.add_comment(tip_id, g.user["id"], body)
    if tip["user_id"] != g.user["id"]:
        models.notify_safe(tip["user_id"], "comment",
                           f"{g.user['display_name']} ametoa maoni kwenye mkeka wako: {tip['title']}",
                           f"/jamvi/{tip_id}")
    return _back(tip_id)


@bp.route("/<int:tip_id>/maoni/<int:comment_id>/futa", methods=["POST"])
@auth.login_required
def comment_delete(tip_id, comment_id):
    c = models.get_comment(comment_id)
    if not c or c["tip_id"] != tip_id:
        abort(404)
    if c["user_id"] != g.user["id"] and not g.user["is_admin"]:
        abort(403)
    models.delete_comment(comment_id)
    return _back(tip_id)


# ---------- Matokeo na kufuta ----------
@bp.route("/<int:tip_id>/matokeo", methods=["POST"])
@auth.login_required
def settle(tip_id):
    tip = _get_or_404(tip_id)
    result = request.form.get("result")
    if result not in ("won", "lost"):
        flash("Chagua matokeo: umeshinda au umepoteza.", "error")
        return _back(tip_id)
    if g.user["is_admin"]:
        pass  # msimamizi anaweza kuweka au kurekebisha wakati wowote
    elif tip["fixture_id"]:
        flash("Matokeo ya mechi halisi yanawekwa na mfumo kiotomatiki.", "info")
        return _back(tip_id)
    elif tip["is_owner"]:
        if tip["status"] != "open":
            flash("Matokeo yameshawekwa. Wasiliana na msimamizi kuyarekebisha.", "error")
            return _back(tip_id)
        if not tip["started"]:
            flash("Subiri mchezo uanze kabla ya kuweka matokeo.", "error")
            return _back(tip_id)
    else:
        abort(403)
    models.set_tip_status(tip_id, result)
    if g.user["is_admin"] and not tip["is_owner"]:
        models.log_order_action(g.user["id"], f"set_tip_{result}", tip_id)
    flash("Matokeo yamewekwa.", "ok")
    return _back(tip_id)


@bp.route("/<int:tip_id>/futa", methods=["POST"])
@auth.login_required
def delete(tip_id):
    tip = _get_or_404(tip_id)
    if not tip["is_owner"]:
        abort(403)
    if models.delete_tip(tip_id, g.user["id"]):
        flash("Mkeka umefutwa.", "info")
        return redirect(url_for("tips.index"))
    flash("Huwezi kufuta mkeka uliokwisha nunuliwa.", "error")
    return _back(tip_id)
