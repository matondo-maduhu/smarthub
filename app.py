import os
import sys
from datetime import datetime, timedelta, timezone

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
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
                stamp, have = auth.password_stamp(user), session.get("pv")
                if have is None:
                    session["pv"] = stamp
                elif have != stamp:  # nenosiri limebadilishwa kwenye kifaa kingine
                    session.clear()
                    return
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

    @app.template_filter("closes")
    def closes(seconds):
        """Sekunde -> 'siku 2', 'saa 3', 'dakika 20'."""
        if seconds is None:
            return ""
        if seconds >= 86400:
            return f"siku {seconds // 86400}"
        if seconds >= 3600:
            return f"saa {seconds // 3600}"
        if seconds >= 60:
            return f"dakika {seconds // 60}"
        return "chini ya dakika 1"

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

    @app.template_filter("eat_time")
    def eat_time(value):
        return value.astimezone(EAT).strftime("%H:%M") if value else ""

    @app.template_filter("eat_date")
    def eat_date(value):
        if not value:
            return ""
        d = value.astimezone(EAT)
        days = ["Jumatatu", "Jumanne", "Jumatano", "Alhamisi", "Ijumaa", "Jumamosi", "Jumapili"]
        today = datetime.now(timezone.utc).astimezone(EAT).date()
        tag = "Leo" if d.date() == today else ("Kesho" if (d.date() - today).days == 1 else days[d.weekday()])
        return f"{tag}, {d.strftime('%d/%m/%Y')}"

    # ----- Kurasa -----
    @app.route("/")
    def home():
        viewer = g.user["id"] if g.user else None
        try:  # ukurasa wa nyumbani ufunguke hata database ikikosekana
            banners = models.banners_active()
            latest = models.list_tips(viewer, limit=3)
            products = models.list_products(limit=4)
        except Exception as e:
            print(f"ONYO: imeshindwa kusoma nyumbani: {e}", file=sys.stderr)
            latest, products, banners = [], [], []
        return render_template("index.html", active="home", tips=latest, products=products, banners=banners)

    @app.route("/tangazo/<int:bid>")
    def banner_go(bid):
        """Huhesabu mbofyo kisha humpeleka mtumiaji kwenye kiungo cha tangazo."""
        try:
            link = models.banner_click(bid)
        except Exception:
            link = None
        return redirect(link or url_for("home"))

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

    @app.route("/masharti")
    def masharti():
        return render_template("masharti.html", active="", order_release_days=Config.ORDER_AUTO_RELEASE_DAYS)

    @app.route("/faragha")
    def faragha():
        return render_template("faragha.html", active="")

    @app.route("/msaada", methods=["GET", "POST"])
    def msaada():
        import hashlib
        form, err = {}, None
        if request.method == "POST":
            form = {k: request.form.get(k, "") for k in ("category", "subject", "body", "name", "contact")}
            iph = hashlib.sha256((request.remote_addr or "-").encode()).hexdigest()[:24]
            try:
                tid = models.support_create(g.user["id"] if g.user else None, form["name"] or (g.user["display_name"] if g.user else ""),
                                            form["contact"], form["category"], form["subject"], form["body"], iph)
            except models.SupportError as e:
                err = str(e)
            else:
                flash("Ombi lako limetumwa. Tutakujibu hivi karibuni.", "ok")
                return redirect(url_for("msaada_moja", tid=tid) if g.user else url_for("msaada"))
        mine = models.support_for_user(g.user["id"]) if g.user else []
        return render_template("msaada.html", active="wasifu", form=form, err=err, mine=mine,
                               cats=models.SUPPORT_CATEGORIES), (400 if err else 200)

    @app.route("/msaada/<int:tid>")
    @auth.login_required
    def msaada_moja(tid):
        t = models.support_get(tid)
        if not t or t["user_id"] != g.user["id"]:
            abort(404)
        return render_template("msaada_moja.html", active="wasifu", t=t, cats=dict(models.SUPPORT_CATEGORIES))

    @app.route("/cron/release")
    def cron_release():
        """Huachilia coin za maagizo yaliyokabidhiwa na yaliyozidi siku. Inaitwa na Vercel Cron kila siku.
        Inahitaji CRON_SECRET (Vercel inautuma kama 'Authorization: Bearer ...'); bila hiyo ni 404."""
        import hmac

        secret = os.getenv("CRON_SECRET", "")
        sent = request.headers.get("Authorization", "")
        if not secret or not hmac.compare_digest(sent, f"Bearer {secret}"):
            abort(404)
        n = models.release_overdue(Config.ORDER_AUTO_RELEASE_DAYS)
        out = {"released": n}
        try:
            models.void_stale_manual_tips()
        except Exception as e:
            print(f"ONYO: kubatilisha mikeka ya mkono kumeshindwa: {e}", file=sys.stderr)
        try:
            import football
            if football.configured():
                out.update(football.run_cron())
        except Exception as e:  # hitilafu ya huduma ya mechi isizuie kuachilia coin
            print(f"ONYO: cron ya mechi imeshindwa: {e}", file=sys.stderr)
        return out

    @app.route("/wasifu")
    def wasifu():
        stats = models.tipster_stats(g.user["id"]) if g.user else None
        return render_template("wasifu.html", active="wasifu", stats=stats)

    @app.route("/wasifu/hariri", methods=["GET", "POST"])
    @auth.login_required
    def wasifu_hariri():
        if request.method == "POST":
            f = request.files.get("avatar")
            url, drop = None, bool(request.form.get("drop_avatar"))
            try:
                if f and f.filename:
                    import storage
                    if not Config.R2_READY:
                        raise models.ProfileError("Upakiaji wa picha haujawashwa bado (R2 haijawekwa).")
                    try:
                        url = storage.upload_image(f, folder="avatars")
                    except ValueError as e:
                        raise models.ProfileError(str(e))
                    except Exception:
                        raise models.ProfileError("Hatukuweza kupakia picha sasa. Jaribu tena baadaye.")
                models.update_profile(g.user["id"], request.form.get("display_name"), request.form.get("bio"),
                                      request.form.get("location"), avatar_url=url, drop_avatar=drop)
            except models.ProfileError as e:
                flash(str(e), "error")
                return render_template("wasifu_hariri.html", active="wasifu", r2_ready=Config.R2_READY,
                                       form=request.form), 400
            flash("Wasifu umehifadhiwa.", "ok")
            return redirect(url_for("wasifu"))
        return render_template("wasifu_hariri.html", active="wasifu", r2_ready=Config.R2_READY, form=None)

    @app.route("/wasifu/mipangilio")
    def mipangilio():
        blocked = models.list_blocked(g.user["id"]) if g.user else []
        return render_template("mipangilio.html", active="wasifu", blocked=blocked)

    @app.route("/wasifu/mipangilio/faragha", methods=["POST"])
    @auth.login_required
    def mipangilio_faragha():
        models.set_allow_messages(g.user["id"], bool(request.form.get("allow_messages")))
        flash("Mipangilio ya faragha imehifadhiwa.", "ok")
        return redirect(url_for("mipangilio"))

    @app.route("/wasifu/mipangilio/ruhusu", methods=["POST"])
    @auth.login_required
    def mipangilio_ruhusu():
        try:
            models.unblock_user(g.user["id"], int(request.form.get("user_id", "")))
            flash("Kizuizi kimeondolewa.", "ok")
        except ValueError:
            pass
        return redirect(url_for("mipangilio"))

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
        if not Config.R2_READY:
            flash("Upakiaji wa picha haujawashwa bado (R2 haijawekwa).", "error")
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
