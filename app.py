from flask import Flask, jsonify, render_template

from config import Config

# Data ya mfano ya kuonyesha muonekano. Hatua zijazo zitaisoma kutoka Neon.
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

TRANSACTIONS = [
    {"kind": "bonus", "label": "Zawadi ya kujiunga", "amount": 100, "time": "Leo"},
    {"kind": "tip_purchase", "label": "Mkeka wa Asha M.", "amount": -15, "time": "Jana"},
    {"kind": "buy", "label": "Kununua coin (majaribio)", "amount": 500, "time": "Jana"},
]

STATUS_LABELS = {
    "open": ("Unasubiri", "warn"),
    "won": ("Umeshinda", "ok"),
    "lost": ("Umepoteza", "bad"),
    "void": ("Umefutwa", "mute"),
}


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    @app.context_processor
    def inject_globals():
        return {
            "app_name": Config.APP_NAME,
            "coin_mode": Config.COIN_MODE,
            "coin_balance": 0,  # itasomwa kutoka Neon baada ya usajili (hatua ya 2)
            "status_labels": STATUS_LABELS,
        }

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
    def pochi():
        return render_template("pochi.html", active="pochi", txns=TRANSACTIONS)

    @app.route("/wasifu")
    def wasifu():
        return render_template("wasifu.html", active="wasifu")

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

    @app.errorhandler(404)
    def not_found(_):
        return render_template("404.html", active=""), 404

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
