"""Market: bidhaa, picha (R2), utafutaji na maagizo ya coin yenye escrow."""
import re
from datetime import datetime, timedelta, timezone

from flask import (Blueprint, abort, flash, g, redirect, render_template,
                   request, url_for)

import auth
import db
import models
from config import Config

bp = Blueprint("market", __name__, url_prefix="/market")

CATEGORIES = [
    ("simu", "Simu na umeme"),
    ("nguo", "Nguo na viatu"),
    ("nyumbani", "Nyumbani"),
    ("magari", "Magari na pikipiki"),
    ("chakula", "Chakula"),
    ("huduma", "Huduma"),
    ("mengineyo", "Mengineyo"),
]
CATEGORY_META = {
    "simu": {"label": "Simu na umeme", "icon": "phone", "hue": 210},
    "nguo": {"label": "Nguo na viatu", "icon": "tag", "hue": 140},
    "nyumbani": {"label": "Nyumbani", "icon": "home", "hue": 30},
    "magari": {"label": "Magari na pikipiki", "icon": "trend", "hue": 0},
    "chakula": {"label": "Chakula", "icon": "store", "hue": 50},
    "huduma": {"label": "Huduma", "icon": "fire", "hue": 280},
    "mengineyo": {"label": "Mengineyo", "icon": "tag", "hue": 180},
}
PRODUCT_STATUS = {
    "reserved": ("Imeagizwa", "warn"),
    "sold": ("Imeuzwa", "mute"),
    "hidden": ("Imefichwa", "mute"),
}
ORDER_STATUS = {
    "paid": ("Imelipwa, inasubiri muuzaji", "warn"),
    "delivered": ("Imekabidhiwa, inasubiri uthibitisho", "warn"),
    "completed": ("Imekamilika", "ok"),
    "cancelled": ("Imeghairiwa, coin zimerudishwa", "mute"),
    "disputed": ("Kuna pingamizi", "bad"),
}
MAX_IMAGES = 4


def _int(raw):
    return int(raw) if re.fullmatch(r"[0-9]{1,9}", raw or "") else None


def _delete_images(urls):
    """Hufuta picha kutoka R2 (jitihada bora; kushindwa hakuvunji chochote)."""
    try:
        import storage
        for url in urls:
            key = storage.key_from_url(url)
            if key:
                storage.delete_key(key)
    except Exception as e:
        print(f"ONYO: imeshindwa kufuta picha: {e}")


# ---------- Orodha na utafutaji ----------
@bp.route("")
def index():
    q = " ".join(request.args.get("q", "").split())[:60]
    aina = request.args.get("aina", "zote")
    if aina not in CATEGORY_META:
        aina = "zote"
    page = max(1, _int(request.args.get("ukurasa")) or 1)
    per = Config.PRODUCTS_PER_PAGE
    rows = models.list_products(q=q or None, category=None if aina == "zote" else aina,
                                limit=per + 1, offset=(page - 1) * per)
    return render_template("market.html", active="market", products=rows[:per], q=q, aina=aina,
                           categories=CATEGORIES, page=page, has_next=len(rows) > per)


# ---------- Kuweka bidhaa ----------
@bp.route("/weka", methods=["GET", "POST"])
@auth.login_required
def new():
    form, errors = {"category": "simu"}, []
    if request.method == "POST":
        import storage  # inaletwa fomu ikitumwa tu, ili ukurasa wa kuweka ufunguke bila R2

        form = {k: request.form.get(k, "").strip()
                for k in ("title", "description", "category", "price", "location", "contact")}
        title = " ".join(form["title"].split())
        price = _int(form["price"])
        files = [f for f in request.files.getlist("images") if f and f.filename]

        if not 3 <= len(title) <= 80:
            errors.append("Jina la bidhaa liwe na herufi 3 hadi 80.")
        if len(form["description"]) > 1000:
            errors.append("Maelezo yasizidi herufi 1000.")
        if form["category"] not in CATEGORY_META:
            errors.append("Chagua kundi la bidhaa.")
        if price is None or not 1 <= price <= Config.MARKET_MAX_PRICE:
            errors.append(f"Bei iwe coin 1 hadi {Config.MARKET_MAX_PRICE:,}.")
        if len(form["location"]) > 60:
            errors.append("Mahali pasizidi herufi 60.")
        if len(form["contact"]) > 40:
            errors.append("Namba ya kuwasiliana isizidi herufi 40.")
        if len(files) > MAX_IMAGES:
            errors.append(f"Picha zisizidi {MAX_IMAGES}.")
        else:
            for f in files:
                try:
                    storage.validate_image(f)
                except ValueError as e:
                    errors.append(f"{f.filename}: {e}")

        if not errors:
            times = models.recent_times("products", g.user["id"], Config.MAX_PRODUCTS_PER_DAY)
            if (len(times) >= Config.MAX_PRODUCTS_PER_DAY
                    and times[-1] > datetime.now(timezone.utc) - timedelta(hours=24)):
                errors.append(f"Umefikia kikomo cha bidhaa {Config.MAX_PRODUCTS_PER_DAY} kwa siku. Jaribu kesho.")

        if not errors:
            urls = []
            try:
                for f in files:
                    urls.append(storage.upload_image(f, folder="products"))
            except Exception:
                _delete_images(urls)
                errors.append("Hatukuweza kupakia picha sasa. Jaribu tena, au weka bidhaa bila picha.")
            else:
                try:
                    pid = models.create_product(
                        g.user["id"], title=title, description=form["description"], category=form["category"],
                        price=price, location=form["location"], contact=form["contact"], image_urls=urls)
                except Exception:
                    _delete_images(urls)
                    raise
                flash("Bidhaa yako imewekwa.", "ok")
                return redirect(url_for("market.detail", product_id=pid))
    return render_template("bidhaa_weka.html", active="market", form=form, errors=errors,
                           categories=CATEGORIES, max_images=MAX_IMAGES, max_price=Config.MARKET_MAX_PRICE,
                           fee=Config.MARKET_FEE_PCT), (400 if errors else 200)


# ---------- Ukurasa wa bidhaa ----------
@bp.route("/<int:product_id>")
def detail(product_id):
    p = models.get_product(product_id)
    if not p:
        abort(404)
    uid = g.user["id"] if g.user else None
    is_owner = bool(uid) and uid == p["seller_id"]
    is_admin = bool(g.user and g.user["is_admin"])
    if p["status"] == "hidden" and not (is_owner or is_admin):
        abort(404)
    order = models.open_order_for_product(product_id)
    my_order_id = order["id"] if order and uid in (order["buyer_id"], order["seller_id"]) else None
    return render_template("bidhaa.html", active="market", p=p, is_owner=is_owner, my_order_id=my_order_id,
                           fee=Config.MARKET_FEE_PCT, days=Config.ORDER_AUTO_RELEASE_DAYS)


@bp.route("/<int:product_id>/ficha", methods=["POST"])
@auth.login_required
def toggle_hidden(product_id):
    p = models.get_product(product_id)
    if not p:
        abort(404)
    if p["seller_id"] != g.user["id"]:
        abort(403)
    if models.set_product_hidden(product_id, g.user["id"], hide=(p["status"] == "active")):
        flash("Bidhaa imefichwa." if p["status"] == "active" else "Bidhaa inaonekana tena.", "ok")
    else:
        flash("Bidhaa iliyoagizwa au kuuzwa haiwezi kufichwa.", "error")
    return redirect(url_for("market.detail", product_id=product_id))


@bp.route("/<int:product_id>/futa", methods=["POST"])
@auth.login_required
def delete(product_id):
    p = models.get_product(product_id)
    if not p:
        abort(404)
    if p["seller_id"] != g.user["id"]:
        abort(403)
    urls = models.delete_product(product_id, g.user["id"])
    if urls is None:
        flash("Bidhaa yenye historia ya maagizo haiwezi kufutwa. Unaweza kuificha.", "error")
        return redirect(url_for("market.detail", product_id=product_id))
    _delete_images(urls)
    flash("Bidhaa imefutwa.", "info")
    return redirect(url_for("market.index"))


# ---------- Kuagiza ----------
@bp.route("/<int:product_id>/agiza", methods=["POST"])
@auth.login_required
def place_order(product_id):
    back = redirect(url_for("market.detail", product_id=product_id))
    if not models.get_product(product_id):
        abort(404)
    note = request.form.get("note", "").strip()
    if len(note) > 300:
        flash("Maelezo yasizidi herufi 300.", "error")
        return back
    try:
        res = models.create_order(product_id, g.user["id"], note, Config.MARKET_FEE_PCT)
    except models.MarketError as e:
        flash(str(e), "error")
        return back
    except models.InsufficientFunds:
        flash("Salio lako halitoshi. Nunua coin kwenye Pochi.", "error")
        return back
    except db.IntegrityError:
        flash("Bidhaa hii imeshaagizwa.", "error")
        return back
    flash(f"Agizo limewekwa. Coin {res['price']} zinashikiliwa hadi upokee bidhaa.", "ok")
    return redirect(url_for("market.order_detail", order_id=res["id"]))


# ---------- Maagizo ----------
def _order_for_viewer(order_id):
    o = models.get_order(order_id)
    uid = g.user["id"]
    if not o or not (uid in (o["buyer_id"], o["seller_id"]) or g.user["is_admin"]):
        abort(404)  # hatufichui kuwepo kwa agizo la watu wengine
    return o


@bp.route("/maagizo")
@auth.login_required
def orders():
    models.release_overdue(Config.ORDER_AUTO_RELEASE_DAYS, g.user["id"])
    kama = "muuzaji" if request.args.get("kama") == "muuzaji" else "mnunuzi"
    rows = models.list_orders(g.user["id"], "seller" if kama == "muuzaji" else "buyer")
    return render_template("maagizo.html", active="market", orders=rows, kama=kama, order_status=ORDER_STATUS)


@bp.route("/maagizo/<int:order_id>")
@auth.login_required
def order_detail(order_id):
    models.release_overdue(Config.ORDER_AUTO_RELEASE_DAYS, g.user["id"])
    o = _order_for_viewer(order_id)
    uid = g.user["id"]
    release_at = None
    if o["status"] == "delivered":
        release_at = models.to_dt(o["delivered_at"]) + timedelta(days=Config.ORDER_AUTO_RELEASE_DAYS)
    return render_template(
        "agizo.html", active="market", o=o, order_status=ORDER_STATUS, release_at=release_at,
        is_buyer=uid == o["buyer_id"], is_seller=uid == o["seller_id"], is_admin=bool(g.user["is_admin"]),
        is_open=o["status"] in ("paid", "delivered", "disputed"), net=o["price"] - o["fee"],
    )


@bp.route("/maagizo/<int:order_id>/<action>", methods=["POST"])
@auth.login_required
def order_action(order_id, action):
    o = _order_for_viewer(order_id)
    uid = g.user["id"]
    is_buyer, is_seller, is_admin = uid == o["buyer_id"], uid == o["seller_id"], bool(g.user["is_admin"])
    done = {
        "kabidhi": "Umeweka kuwa umekabidhi bidhaa. Mnunuzi akithibitisha, coin zako zitaachiliwa.",
        "pokea": "Asante! Umethibitisha kupokea. Muuzaji amelipwa.",
        "ghairi": "Agizo limeghairiwa na coin zimerudishwa.",
        "pingamizi": "Pingamizi limewekwa. Coin zinabaki zimeshikiliwa hadi msimamizi aamue.",
        "achilia": "Coin zimeachiliwa kwa muuzaji.",
        "rudisha": "Coin zimerudishwa kwa mnunuzi.",
    }
    if action not in done:
        abort(404)
    try:
        if action == "kabidhi" and is_seller:
            models.mark_delivered(order_id, uid)
        elif action == "pokea" and is_buyer:
            models.confirm_received(order_id, uid)
        elif action == "ghairi" and is_seller:
            models.cancel_by_seller(order_id, uid)
        elif action == "ghairi" and is_buyer:
            models.cancel_by_buyer(order_id, uid)
        elif action == "pingamizi" and is_buyer:
            models.open_dispute(order_id, uid)
        elif action == "achilia" and is_admin:
            models.admin_release(order_id)
        elif action == "rudisha" and is_admin:
            models.admin_refund(order_id)
        else:
            abort(403)
    except models.MarketError as e:
        flash(str(e), "error")
    else:
        flash(done[action], "ok")
    return redirect(url_for("market.order_detail", order_id=order_id))
