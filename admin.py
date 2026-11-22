"""Usimamizi: dashibodi, watumiaji, mikeka, bidhaa, maagizo, ripoti na kumbukumbu."""
from functools import wraps

from flask import (Blueprint, abort, flash, g, redirect, render_template,
                   request, url_for)

import auth
import models
from config import Config

bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    @wraps(view)
    @auth.login_required
    def wrapped(*args, **kwargs):
        if not g.user["is_admin"]:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


PER_PAGE = 50
LOG_LABELS = {
    "ban": "Alisimamisha akaunti", "unban": "Aliwasha akaunti", "verify": "Alithibitisha akaunti", "unverify": "Aliondoa uthibitisho",
    "delete_tip": "Alifuta mkeka", "void_tip": "Alibatilisha mkeka", "hide_product": "Alificha bidhaa", "show_product": "Alionyesha bidhaa",
    "banner_add": "Aliongeza tangazo", "banner_edit": "Alihariri tangazo", "banner_delete": "Alifuta tangazo",
    "banner_on": "Aliwasha tangazo", "banner_off": "Alizima tangazo", "env_admin": "Msimamizi (environment)",
    "support_reply": "Alijibu ombi la msaada", "support_close": "Alifunga ombi la msaada", "reset_link": "Alitengeneza kiungo cha nenosiri",
    "report_resolved": "Alishughulikia ripoti", "report_dismissed": "Alipuuza ripoti",
}


def _paging():
    """(ukurasa, kiasi, offset) kutoka ?ukurasa=; tunaomba kimoja zaidi ili kujua kama kuna kurasa inayofuata."""
    try:
        page = max(1, min(int(request.args.get("ukurasa", "1")), 10000))
    except ValueError:
        page = 1
    return page, PER_PAGE, (page - 1) * PER_PAGE


def _cut(rows, per):
    return rows[:per], len(rows) > per


def _do(fn, ok_msg, *args):
    try:
        fn(*args)
    except models.AdminError as e:
        flash(str(e), "error")
    else:
        flash(ok_msg, "ok")


@bp.route("")
@admin_required
def dashboard():
    return render_template("admin_dash.html", active="admin", s=models.admin_stats(),
                           disputed=models.admin_orders("disputed", 10))


@bp.route("/watumiaji")
@admin_required
def users():
    q = request.args.get("q", "").strip()[:60]
    page, per, off = _paging()
    rows, more = _cut(models.admin_users(q or None, per + 1, off), per)
    return render_template("admin_users.html", active="admin", rows=rows, q=q, page=page, has_next=more)


@bp.route("/watumiaji/<int:uid>/kiungo-nenosiri", methods=["POST"])
@admin_required
def user_reset_link(uid):
    try:
        token, uname = models.admin_make_reset_link(g.user["id"], uid)
    except models.AdminError as e:
        flash(str(e), "error")
        return redirect(url_for("admin.users"))
    link = url_for("auth.reset_password", token=token, _external=True)
    return render_template("admin_kiungo.html", active="admin", link=link, uname=uname, hours=models.RESET_HOURS)


@bp.route("/watumiaji/<int:uid>/<action>", methods=["POST"])
@admin_required
def user_action(uid, action):
    me = g.user["id"]
    if action == "simamisha":
        _do(models.admin_set_banned, "Akaunti imesimamishwa.", me, uid, True)
    elif action == "washa":
        _do(models.admin_set_banned, "Akaunti imewashwa tena.", me, uid, False)
    elif action == "thibitisha":
        _do(models.admin_set_verified, "Mtumiaji amethibitishwa.", me, uid, True)
    elif action == "ondoa-uthibitisho":
        _do(models.admin_set_verified, "Uthibitisho umeondolewa.", me, uid, False)
    else:
        abort(404)
    return redirect(url_for("admin.users", q=request.form.get("q") or None))


@bp.route("/mikeka")
@admin_required
def tips():
    page, per, off = _paging()
    rows, more = _cut(models.admin_tips(per + 1, off), per)
    return render_template("admin_tips.html", active="admin", rows=rows, fee=Config.TIP_FEE_PCT, page=page, has_next=more)


@bp.route("/mikeka/<int:tip_id>/<action>", methods=["POST"])
@admin_required
def tip_action(tip_id, action):
    me = g.user["id"]
    if action == "batilisha":
        try:
            n = models.admin_void_tip(me, tip_id)
            flash(f"Mkeka umebatilishwa. Wanunuzi {n} wamerudishiwa coin.", "ok")
        except models.AdminError as e:
            flash(str(e), "error")
    elif action == "futa":
        _do(models.admin_delete_tip, "Mkeka umefutwa.", me, tip_id)
    else:
        abort(404)
    return redirect(url_for("admin.tips"))


@bp.route("/bidhaa")
@admin_required
def products():
    page, per, off = _paging()
    rows, more = _cut(models.admin_products(per + 1, off), per)
    return render_template("admin_products.html", active="admin", rows=rows, page=page, has_next=more)


@bp.route("/bidhaa/<int:pid>/<action>", methods=["POST"])
@admin_required
def product_action(pid, action):
    if action == "ficha":
        _do(models.admin_hide_product, "Bidhaa imefichwa.", g.user["id"], pid, True)
    elif action == "onyesha":
        _do(models.admin_hide_product, "Bidhaa imeonyeshwa.", g.user["id"], pid, False)
    else:
        abort(404)
    return redirect(url_for("admin.products"))


@bp.route("/maagizo")
@admin_required
def orders():
    hali = request.args.get("hali", "disputed")
    if hali not in ("disputed", "paid", "delivered", "completed", "cancelled", "zote"):
        hali = "disputed"
    page, per, off = _paging()
    rows, more = _cut(models.admin_orders(None if hali == "zote" else hali, per + 1, off), per)
    return render_template("admin_orders.html", active="admin", rows=rows, hali=hali, page=page, has_next=more)


@bp.route("/ripoti")
@admin_required
def reports():
    hali = request.args.get("hali", "open")
    if hali not in ("open", "resolved", "dismissed"):
        hali = "open"
    page, per, off = _paging()
    rows, more = _cut(models.admin_reports(hali, per + 1, off), per)
    return render_template("admin_reports.html", active="admin", rows=rows, hali=hali, page=page, has_next=more)


@bp.route("/ripoti/<int:rid>/<action>", methods=["POST"])
@admin_required
def report_action(rid, action):
    if action not in ("imeshughulikiwa", "puuza"):
        abort(404)
    _do(models.admin_resolve_report, "Ripoti imefungwa.", g.user["id"], rid,
        "resolved" if action == "imeshughulikiwa" else "dismissed")
    return redirect(url_for("admin.reports"))


@bp.route("/msaada")
@admin_required
def support():
    hali = request.args.get("hali", "open")
    if hali not in ("open", "answered", "closed", "zote"):
        hali = "open"
    page, per, off = _paging()
    rows, more = _cut(models.admin_support(hali, per + 1, off), per)
    return render_template("admin_msaada.html", active="admin", rows=rows, hali=hali, page=page, has_next=more)


@bp.route("/msaada/<int:tid>")
@admin_required
def support_detail(tid):
    t = models.support_get(tid)
    if not t:
        abort(404)
    return render_template("admin_msaada_moja.html", active="admin", t=t, cats=dict(models.SUPPORT_CATEGORIES))


@bp.route("/msaada/<int:tid>/jibu", methods=["POST"])
@admin_required
def support_reply(tid):
    _do(models.admin_support_reply, "Jibu limetumwa.", g.user["id"], tid,
        request.form.get("jibu", ""), request.form.get("funga") == "1")
    return redirect(url_for("admin.support_detail", tid=tid))


@bp.route("/msaada/<int:tid>/funga", methods=["POST"])
@admin_required
def support_close(tid):
    _do(models.admin_support_close, "Ombi limefungwa.", g.user["id"], tid)
    return redirect(url_for("admin.support"))


@bp.route("/mechi")
@admin_required
def fixtures():
    import football

    q = request.args.get("q", "").strip()[:40]
    found, err = [], None
    if q and len(q) >= 3 and football.configured():
        try:
            found = football.search_leagues(q)
        except football.FootballError as e:
            err = str(e)
    return render_template(
        "admin_mechi.html", active="admin", configured=football.configured(), q=q, found=found, err=err,
        leagues=Config.FOOTBALL_LEAGUES, left=football.requests_left() if football.configured() else None,
        synced=football.kv_get("fixtures_synced") if football.configured() else None,
        sync_note=(lambda r: r["value"] if r and r["value"] != "-" else None)(football.kv_get("fixtures_note")) if football.configured() else None,
        upcoming=len(football.list_fixtures(limit=600)) if football.configured() else 0,
        waiting=models.admin_waiting_tips())


@bp.route("/mechi/<action>", methods=["POST"])
@admin_required
def fixtures_action(action):
    import football

    try:
        if action == "sasisha":
            n = football.sync_fixtures(force=True)
            models.log_order_action(g.user["id"], "sync_fixtures", n)
            flash(f"Mechi {n} zimesasishwa.", "ok")
        elif action == "hukumu":
            n = football.settle_due(force=True)
            models.log_order_action(g.user["id"], "settle_fixtures", n)
            flash(f"Mikeka {n} imehukumiwa.", "ok")
        else:
            abort(404)
    except football.FootballError as e:
        flash(str(e), "error")
    return redirect(url_for("admin.fixtures"))


@bp.route("/kumbukumbu")
@admin_required
def log():
    page, per, off = _paging()
    rows, more = _cut(models.admin_log_list(per + 1, off), per)
    return render_template("admin_log.html", active="admin", rows=rows, page=page, has_next=more, log_labels=LOG_LABELS)


# ---------- Matangazo ----------
def _banner_form():
    """Husoma fomu ya tangazo. Kiungo: chaguo la haraka au maandishi ya mkono."""
    from datetime import datetime, timedelta, timezone
    f = request.form
    link = f.get("link_custom", "").strip() or f.get("link_pick", "").strip()
    ends = None
    raw = f.get("ends_on", "").strip()
    if raw:
        try:  # mwisho wa siku hiyo kwa saa za Tanzania (UTC+3)
            ends = datetime.strptime(raw, "%Y-%m-%d").replace(tzinfo=timezone(timedelta(hours=3))) + timedelta(days=1)
        except ValueError:
            raise models.AdminError("Tarehe ya mwisho si sahihi.")
    return dict(title=f.get("title"), subtitle=f.get("subtitle"), theme=f.get("theme"), link=link,
                cta=f.get("cta"), position=f.get("position"), ends_at=ends)


def _banner_image():
    """Inarudisha URL ya picha mpya (au None). Inahitaji R2."""
    file = request.files.get("image")
    if not file or not file.filename:
        return None
    if not Config.R2_READY:
        raise models.AdminError("Picha haziwezi kupakiwa: R2 haijawekwa. Tumia rangi bila picha au weka R2.")
    import storage
    try:
        return storage.upload_image(file, folder="banners")
    except ValueError as e:
        raise models.AdminError(str(e))
    except Exception:
        raise models.AdminError("Imeshindwa kupakia picha. Jaribu tena.")


def _banner_targets():
    """Bidhaa na mikeka ya hivi karibuni, ili admin achague badala ya kunakili kiungo."""
    prods = models.db.query("SELECT id, title FROM products WHERE status = 'active' ORDER BY id DESC LIMIT 40")
    tips = models.db.query("SELECT id, title FROM tips ORDER BY id DESC LIMIT 40")
    picked = [p for p, _ in models.BANNER_LINKS]
    picked += [f"/market?aina={c}" for c in ("simu", "nguo", "nyumbani", "magari", "chakula", "huduma", "mengineyo")]
    picked += [f"/market/{p['id']}" for p in prods] + [f"/jamvi/{t['id']}" for t in tips]
    return prods, tips, picked


@bp.route("/matangazo")
@admin_required
def banners():
    return render_template("admin_matangazo.html", active="admin", rows=models.admin_banners(),
                           links=models.BANNER_LINKS, themes=models.BANNER_THEMES, r2_ready=Config.R2_READY,
                           max_banners=models.MAX_BANNERS, edit=None, targets=_banner_targets())


@bp.route("/matangazo/<int:bid>/hariri")
@admin_required
def banner_edit(bid):
    b = models.get_banner(bid)
    if b is None:
        abort(404)
    return render_template("admin_matangazo.html", active="admin", rows=models.admin_banners(),
                           links=models.BANNER_LINKS, themes=models.BANNER_THEMES, r2_ready=Config.R2_READY,
                           max_banners=models.MAX_BANNERS, edit=b, targets=_banner_targets())


@bp.route("/matangazo/hifadhi", methods=["POST"])
@admin_required
def banner_save():
    raw = request.form.get("id", "")
    bid = int(raw) if raw.isdigit() else None
    try:
        data = _banner_form()
        img = _banner_image()
        models.banner_save(g.user["id"], bid, image_url=img, drop_image=bool(request.form.get("drop_image")), **data)
    except models.AdminError as e:
        flash(str(e), "error")
        return redirect(url_for("admin.banner_edit", bid=bid) if bid else url_for("admin.banners"))
    flash("Tangazo limehifadhiwa.", "ok")
    return redirect(url_for("admin.banners"))


@bp.route("/matangazo/<int:bid>/<action>", methods=["POST"])
@admin_required
def banner_action(bid, action):
    if action == "toggle":
        _do(models.banner_toggle, "Hali ya tangazo imebadilishwa.", g.user["id"], bid)
    elif action == "futa":
        try:
            img = models.banner_delete(g.user["id"], bid)
            if img:
                try:
                    import storage
                    key = storage.key_from_url(img)
                    if key:
                        storage.delete_key(key)
                except Exception:
                    pass
            flash("Tangazo limefutwa.", "ok")
        except models.AdminError as e:
            flash(str(e), "error")
    else:
        abort(404)
    return redirect(url_for("admin.banners"))


# ---------- Ripoti za watumiaji (si za msimamizi) ----------
report_bp = Blueprint("report", __name__)


@report_bp.route("/ripoti", methods=["POST"])
@auth.login_required
def submit():
    kind = request.form.get("aina", "")
    try:
        target = int(request.form.get("id", ""))
    except ValueError:
        abort(400)
    reason = request.form.get("sababu", "").strip()
    if not 5 <= len(reason) <= 300:
        flash("Eleza sababu kwa herufi 5 hadi 300.", "error")
    else:
        try:
            if models.create_report(g.user["id"], kind, target, reason):
                flash("Asante. Ripoti imetumwa kwa wasimamizi.", "ok")
            else:
                flash("Umesharipoti hili. Wasimamizi wanalishughulikia.", "info")
        except models.AdminError as e:
            flash(str(e), "error")
    nxt = auth.safe_next(request.form.get("next")) or url_for("home")
    return redirect(nxt)
