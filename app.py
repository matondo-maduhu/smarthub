import sys
from datetime import datetime, timedelta, timezone

from flask import (Flask, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.middleware.proxy_fix import ProxyFix

import auth
import models
from config import Config

# Data ya mfano ya mikeka na bidhaa. Hatua ya 4 na 5 zitaisoma kutoka Neon.
CATEGORIES = [
    ("zote", "Zote"),
    ("simu", "Simu na umeme"),
    ("nguo", "Nguo na viatu"),
    ("nyumbani", "Nyumbani"),
    ("magari", "Magari na pikipiki"),
    ("chakula", "Chakula"),
    ("huduma", "Huduma"),
]

PRODUCTS = [
    {"id": 1, "title": "Simu janja 128GB", "category": "simu", "price": 450, "location": "Dar es Salaam", "icon": "phone", "hue": 210},
    {"id": 2, "title": "Viatu vya michezo", "category": "nguo", "price": 60, "location": "Arusha", "icon": "tag", "hue": 140},
    {"id": 3, "title": "Kochi la watu watatu", "category": "nyumbani", "price": 380, "location": "Mwanza", "icon": "home", "hue": 30},
    {"id": 4, "title": "Pikipiki ya miezi 6", "category": "magari", "price": 2400, "location": "Dodoma", "icon": "trend", "hue": 0},
    {"id": 5, "title": "Mchele kilo 25", "category": "chakula", "price": 55, "location": "Mbeya", "icon": "store", "hue": 50},
    {"id": 6, "title": "Fundi wa umeme", "category": "huduma", "price": 25, "location": "Dar es Salaam", "icon": "fire", "hue": 280},
]

TIPS = [
    {"id": 1, "tipster": "Juma K.", "initials": "JK", "league": "Ligi Kuu", "match": "Simba vs Yanga", "pick": "Wote kufunga", "odds": 1.85, "price": 0, "status": "open", "time": "Leo 19:00", "likes": 42, "comments": 18, "win_rate": 72},
    {"id": 2, "tipster": "Asha M.", "initials": "AM", "league": "Premier League", "match": "Arsenal vs Chelsea", "pick": "Arsenal ashinde", "odds": 2.10, "price": 15, "status": "open", "time": "Kesho 17:30", "likes": 31, "comments": 9, "win_rate": 68},
    {"id": 3, "tipster": "Baraka T.", "initials": "BT", "league": "La Liga", "match": "Real Madrid vs Sevilla", "pick": "Magoli zaidi ya 2.5", "odds": 1.70, "price": 10, "status": "won", "time": "Jana 22:00", "likes": 88, "comments": 27, "win_rate": 81},
    {"id": 4, "tipster": "Neema S.", "initials": "NS", "league": "Serie A", "match": "Inter vs Napoli", "pick": "Sare au Inter", "odds": 1.55, "price": 0, "status": "lost", "time": "Jana 21:45", "likes": 12, "comments": 6, "win_rate": 59},
]

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


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    if Config.TRUST_PROXY:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    if Config.SECRET_KEY == "dev-only-change-me":
        print("ONYO: SECRET_KEY haijabadilishwa. Weka thamani ndefu ya siri kwenye .env", file=sys.stderr)

    app.register_blueprint(auth.bp)

    @app.before_request
    def load_user():
        g.user = None
        uid = session.get("uid")
        if uid:
            user = models.get_user(uid)
            if user and not user["is_banned"]:
                g.user = user
            else:
                session.clear()

    @app.context_processor
    def inject_globals():
        return {
            "app_name": Config.APP_NAME,
            "coin_mode": Config.COIN_MODE,
            "user": g.get("user"),
            "coin_balance": g.user["balance"] if g.get("user") else 0,
            "status_labels": STATUS_LABELS,
            "csrf_token": auth.csrf_token,
            "google_enabled": auth.google_enabled(),
        }

    @app.template_filter("eat")
    def eat(value):
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
        return render_template("index.html", active="home", tips=TIPS[:3], products=PRODUCTS[:4])

    @app.route("/jamvi")
    def jamvi():
        return render_template("jamvi.html", active="jamvi", tips=TIPS)

    @app.route("/market")
    def market():
        return render_template("market.html", active="market", products=PRODUCTS, categories=CATEGORIES)

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
                               message="Ukubwa wa juu ni MB 8."), 413

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
