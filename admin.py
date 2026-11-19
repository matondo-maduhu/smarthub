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
    return render_template("admin_users.html", active="admin", rows=models.admin_users(q or None), q=q)


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
    return render_template("admin_tips.html", active="admin", rows=models.admin_tips(), fee=Config.TIP_FEE_PCT)


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
    return render_template("admin_products.html", active="admin", rows=models.admin_products())


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
    return render_template("admin_orders.html", active="admin", rows=models.admin_orders(None if hali == "zote" else hali),
                           hali=hali)


@bp.route("/ripoti")
@admin_required
def reports():
    hali = request.args.get("hali", "open")
    if hali not in ("open", "resolved", "dismissed"):
        hali = "open"
    return render_template("admin_reports.html", active="admin", rows=models.admin_reports(hali), hali=hali)


@bp.route("/ripoti/<int:rid>/<action>", methods=["POST"])
@admin_required
def report_action(rid, action):
    if action not in ("imeshughulikiwa", "puuza"):
        abort(404)
    _do(models.admin_resolve_report, "Ripoti imefungwa.", g.user["id"], rid,
        "resolved" if action == "imeshughulikiwa" else "dismissed")
    return redirect(url_for("admin.reports"))


@bp.route("/kumbukumbu")
@admin_required
def log():
    return render_template("admin_log.html", active="admin", rows=models.admin_log_list())


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
