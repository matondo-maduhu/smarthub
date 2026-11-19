import sys
from datetime import datetime, timedelta, timezone

from flask import (Flask, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.middleware.proxy_fix import ProxyFix

import admin
import auth
import chat
import db
import market
import models
import notifications
import tips
import wallet
from config import Config

STATUS_LABELS = {
    "open": ("Unasubiri", "warn"),
    "won": ("Umeshinda", "ok"),
    "lost": ("Umepoteza", "bad"),
    "void": ("Umefutwa", "mute"),
}

KIND_LABELS = {
    "bonus": "Zawadi ya kujiunga",
    "buy": "Kununua coin",
    "withdraw": "Kutoa pesa",
    "tip_purchase": "Kununua mkeka",
    "tip_sale": "Mauzo ya mkeka",
    "market": "Market",
}

EAT = timezone(timedelta(hours=3))  # saa za Afrika Mashariki


def _env_admin(user):
    """Je, mtumiaji huyu yumo kwenye ADMIN_USERNAMES / ADMIN_EMAILS / ADMIN_PHONES?"""
    if (user["username"] or "").lower() in Config.ADMIN_USERNAMES:
        return True
    if user["email"] and user["email"].lower() in Config.ADMIN_EMAILS:
        return True
    phones = {auth.normalize_phone(p) for p in Config.ADMIN_PHONES}
    return bool(user["phone"] and user["phone"] in phones)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    if Config.TRUST_PROXY:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    if Config.SECRET_KEY == "dev-only-change-me":
        print("ONYO: SECRET_KEY haijabadilishwa. Weka thamani ndefu ya siri kwenye .env", file=sys.stderr)

    app.register_blueprint(auth.bp)
    app.register_blueprint(wallet.bp)
    app.register_blueprint(tips.bp)
    app.register_blueprint(market.bp)
    app.register_blueprint(chat.bp)
    app.register_blueprint(notifications.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(admin.report_bp)

    @app.before_request
    def load_user():
        g.user = None
        if Config.DATABASE_URL:
            try:
                db.ensure_schema()
            except Exception as e:  # kurasa zisizotumia database bado zifunguke
                print(f"ONYO: imeshindwa kutengeneza majedwali: {e}", file=sys.stderr)
        uid = session.get("uid")
        if uid:
            user = models.get_user(uid)
            if user and not user["is_banned"]:
                if not user["is_admin"] and _env_admin(user):
                    try:
                        models.make_admin(user["id"])
                        user = models.get_user(uid)
                    except Exception as e:
                        print(f"ONYO: imeshindwa kumfanya msimamizi: {e}", file=sys.stderr)
                g.user = user
            else:
                session.clear()

    @app.context_processor
    def inject_globals():
        unread_msgs = unread_notes = 0
        if g.get("user"):
            try:
                unread_msgs, unread_notes = models.unread_counts(g.user["id"])
            except Exception:
                pass
        return {
            "unread_messages": unread_msgs,
            "unread_notifications": unread_notes,
            "app_name": Config.APP_NAME,
            "coin_mode": Config.COIN_MODE,
            "user": g.get("user"),
            "coin_balance": g.user["balance"] if g.get("user") else 0,
            "coin_rate": Config.COIN_RATE_TZS,
            "min_withdraw": Config.MIN_WITHDRAW,
            "status_labels": STATUS_LABELS,
            "category_meta": market.CATEGORY_META,
            "product_status": market.PRODUCT_STATUS,
            "csrf_token": auth.csrf_token,
            "google_enabled": auth.google_enabled(),
        }

    @app.template_filter("num")
    def num(value):
        return f"{int(value):,}"

    @app.template_filter("eat")
    def eat(value):
        if value is None:
            return ""
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                return value
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(EAT).strftime("%d/%m/%Y %H:%M")

    # ----- Kurasa -----
    @app.route("/")
    def home():
        viewer = g.user["id"] if g.user else None
        try:  # ukurasa wa nyumbani ufunguke hata database ikikosekana
            latest = models.list_tips(viewer, limit=3)
            products = models.list_products(limit=4)
        except Exception as e:
            print(f"ONYO: imeshindwa kusoma nyumbani: {e}", file=sys.stderr)
            latest, products = [], []
        return render_template("index.html", active="home", tips=latest, products=products)

    @app.route("/pochi")
    @auth.login_required
    def pochi():
        txns = [
            {
                "label": t["note"] or KIND_LABELS.get(t["kind"], t["kind"]),
                "amount": t["amount"],
                "time": t["created_at"],
                "status": t["status"],
            }
            for t in models.get_transactions(g.user["id"])
        ]
        return render_template("pochi.html", active="pochi", txns=txns)

    @app.route("/wasifu")
    def wasifu():
        return render_template("wasifu.html", active="wasifu")

    @app.route("/wasifu/jina", methods=["POST"])
    @auth.login_required
    def wasifu_jina():
        name = " ".join(request.form.get("display_name", "").split())
        if 2 <= len(name) <= 40:
            models.update_display_name(g.user["id"], name)
            flash("Jina limebadilishwa.", "ok")
        else:
            flash("Jina liwe na herufi 2 hadi 40.", "error")
        return redirect(url_for("wasifu"))

    @app.route("/wasifu/picha", methods=["POST"])
    @auth.login_required
    def wasifu_picha():
        import storage

        f = request.files.get("avatar")
        if not f or not f.filename:
            flash("Chagua picha kwanza.", "error")
            return redirect(url_for("wasifu"))
        try:
            url = storage.upload_image(f, folder="avatars")
        except ValueError as e:
            flash(str(e), "error")
        except Exception:
            flash("Hatukuweza kupakia picha sasa. Hakikisha R2 imewekwa vizuri.", "error")
        else:
            models.update_avatar(g.user["id"], url)
            flash("Picha imebadilishwa.", "ok")
        return redirect(url_for("wasifu"))

    @app.route("/afya")
    def afya():
        """Hukagua kama Neon na R2 zimeunganishwa vizuri."""
        import db
        import storage

        result = {"neon": "haijajaribiwa", "r2": "haijajaribiwa"}
        try:
            result["neon"] = "sawa" if db.ping() else "imeshindwa"
        except Exception as e:
            result["neon"] = f"kosa: {e}"
        try:
            result["r2"] = "sawa" if storage.ping() else "imeshindwa"
        except Exception as e:
            result["r2"] = f"kosa: {e}"
        return jsonify(result)

    # ----- Makosa -----
    @app.errorhandler(400)
    def bad_request(_):
        return render_template("error.html", active="", title="Ombi halikukubalika",
                               message="Fomu imepitwa na wakati. Rudi nyuma, onyesha ukurasa upya kisha ujaribu tena."), 400

    @app.errorhandler(404)
    def not_found(_):
        return render_template("404.html", active=""), 404

    @app.errorhandler(413)
    def too_large(_):
        return render_template("error.html", active="", title="Faili ni kubwa mno",
                               message="Ukubwa wa juu ni MB 20 kwa ombi lote, na MB 5 kwa kila picha."), 413

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
