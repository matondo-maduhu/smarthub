"""Jamvi la mikeka: kuweka, kuorodhesha, kununua, kupenda, maoni, matokeo na viwango."""
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from flask import (Blueprint, abort, current_app, flash, g, redirect, render_template,
                   request, session, url_for)

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
                           stats=models.tipster_stats(person["id"]),
                           following=models.is_following(g.user["id"] if g.user else None, person["id"]),
                           followers=models.follower_count(person["id"]))


@bp.route("/mtabiri/<username>/<action>", methods=["POST"])
@auth.login_required
def follow_action(username, action):
    if action not in ("fuata", "acha"):
        abort(404)
    person = models.get_user_by_username(username.lower())
    if not person:
        abort(404)
    try:
        if action == "fuata":
            models.follow(g.user["id"], person["id"])
            flash(f"Unamfuata {person['display_name']}. Utapata arifa akiweka mkeka mpya.", "ok")
        else:
            models.unfollow(g.user["id"], person["id"])
            flash(f"Umeacha kumfuata {person['display_name']}.", "ok")
    except models.FollowError as e:
        flash(str(e), "error")
    return redirect(auth.safe_next(request.form.get("next")) or url_for("tips.tipster", username=person["username"]))


@bp.route("/ninaowafuata")
@auth.login_required
def following():
    return render_template("ninaowafuata.html", active="jamvi", people=models.following_list(g.user["id"]),
                           tips=models.following_tips(g.user["id"]))


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
        elif starts <= now + timedelta(minutes=Config.LOCK_MINUTES_BEFORE + 5):
            errors.append(f"Mchezo lazima uanze angalau dakika {Config.LOCK_MINUTES_BEFORE + 5} kutoka sasa (mkeka unafungwa dakika {Config.LOCK_MINUTES_BEFORE} kabla).")
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


# ---------- Mkeka wa mechi nyingi (kapu la mechi) ----------
def _slip():
    """Mechi zilizochaguliwa kwenye kikao cha mtumiaji: [{f: fixture_id, c: 'soko:chaguo', t, l, o}]."""
    out, seen = [], set()
    for x in session.get("slip") or []:
        if (isinstance(x, dict) and isinstance(x.get("f"), int) and isinstance(x.get("c"), str)
                and x["f"] not in seen):
            seen.add(x["f"])
            out.append({"f": x["f"], "c": x["c"][:40], "t": str(x.get("t", ""))[:80],
                        "l": str(x.get("l", ""))[:80], "o": float(x.get("o") or 0)})
    return out[:Config.MAX_SLIP_LEGS]


def _save_slip(items):
    session["slip"] = items
    session.modified = True


def _fixture_ok(fx, now):
    return bool(fx and fx["status"] == "NS"
                and fx["kickoff"] > now + timedelta(minutes=Config.LOCK_MINUTES_BEFORE + 5))


@bp.route("/weka/ongeza", methods=["POST"])
@auth.login_required
def slip_add():
    now = datetime.now(timezone.utc)
    fid, key = _int(request.form.get("mechi")), request.form.get("chaguo", "")
    fx = football.get_fixture(fid) if fid else None
    if not _fixture_ok(fx, now):
        flash("Mechi hii haipatikani tena kwa mikeka. Chagua nyingine.", "error")
        return redirect(url_for("tips.new"))
    try:
        rows = football.get_odds(fid)
    except football.FootballError as e:
        flash(str(e), "error")
        return redirect(url_for("tips.new", mechi=fid))
    valid = {o["key"]: o for mk in football.options(rows, fx["home"], fx["away"]) for o in mk["options"]}
    if key not in valid:
        flash("Chagua mkeka kwenye orodha.", "error")
        return redirect(url_for("tips.new", mechi=fid))
    slip = [x for x in _slip() if x["f"] != fid]  # chaguo jipya la mechi ileile linabadilisha la zamani
    if len(slip) >= Config.MAX_SLIP_LEGS:
        flash(f"Mkeka mmoja una mechi {Config.MAX_SLIP_LEGS} kwa kiwango cha juu.", "error")
        return redirect(url_for("tips.new"))
    slip.append({"f": fid, "c": key, "t": f"{fx['home']} vs {fx['away']}", "l": valid[key]["label"],
                 "o": float(valid[key]["best"])})
    _save_slip(slip)
    flash("Mechi imeongezwa kwenye mkeka wako. Ongeza nyingine au bonyeza \"Kamilisha mkeka\".", "ok")
    return redirect(url_for("tips.new"))


@bp.route("/weka/ondoa", methods=["POST"])
@auth.login_required
def slip_remove():
    fid = _int(request.form.get("mechi"))
    _save_slip([x for x in _slip() if x["f"] != fid] if request.form.get("yote") != "1" else [])
    return redirect(url_for("tips.new", kamilisha=request.form.get("rudi") or None))


def _slip_view(now):
    """Kila mechi kwenye kapu na odds za sasa za kampuni. Inarudisha (mechi, tatizo). Mechi
    zisizopatikana tena zinaondolewa kwenye kapu na kuripotiwa."""
    view, keep, dropped, problem = [], [], [], None
    for x in _slip():
        fx = football.get_fixture(x["f"])
        if not _fixture_ok(fx, now):
            dropped.append(x["t"] or str(x["f"]))
            continue
        try:
            rows = football.get_odds(x["f"])
        except football.FootballError as e:
            problem = str(e)
            keep.append(x)
            continue
        market, selection = x["c"].split(":", 1) if ":" in x["c"] else ("", "")
        opts = {o["key"]: o for mk in football.options(rows, fx["home"], fx["away"]) for o in mk["options"]}
        if x["c"] not in opts:
            dropped.append(x["t"])
            continue
        keep.append(x)
        view.append({"fx": fx, "key": x["c"], "market": market, "selection": selection, "opt": opts[x["c"]],
                     "books": football.bookmakers_for(rows, market, selection)})
    if len(keep) != len(_slip()):
        _save_slip(keep)
    return view, dropped, problem


def _combos(view):
    """Kampuni zenye mechi ZOTE za kapu, na odds jumla (zinazidishwa) za kila moja."""
    if not view:
        return []
    ids = set.intersection(*[{b["id"] for b in v["books"]} for v in view])
    out = []
    for b in view[0]["books"]:  # mpangilio wa kampuni zilizopendelezwa unabaki
        if b["id"] in ids:
            per = [next(x["odd"] for x in v["books"] if x["id"] == b["id"]) for v in view]
            total = 1.0
            for o in per:
                total *= o
            out.append({"id": b["id"], "name": b["name"], "per": per, "total": round(total, 2)})
    return out


def _browse(ctx, q, now):
    """Mechi zimepangwa kwa siku na ligi: chagua siku, chuja ligi, kisha mechi zimekundikwa kwa ligi."""
    EAT = timezone(timedelta(hours=3))
    order = {lid: i for i, lid in enumerate(Config.FOOTBALL_LEAGUES)}
    rows = football.list_fixtures(q, limit=400)
    for f in rows:
        f["day"] = f["kickoff"].astimezone(EAT).date().isoformat()
    days = []
    for f in rows:
        if not days or days[-1]["key"] != f["day"]:
            days.append({"key": f["day"], "kickoff": f["kickoff"], "n": 0})
        days[-1]["n"] += 1
    siku = request.args.get("siku", "")
    if q or siku == "yote":  # kutafuta kunatafuta siku zote
        siku = "yote"
    elif siku not in {d["key"] for d in days}:
        siku = days[0]["key"] if days else "yote"
    day_rows = [f for f in rows if siku == "yote" or f["day"] == siku]
    leagues = {}
    for f in day_rows:
        l = leagues.setdefault(f["league_id"], {"id": f["league_id"], "name": f["league_name"],
                                                "country": f["country"], "n": 0})
        l["n"] += 1
    league_list = sorted(leagues.values(), key=lambda l: (order.get(l["id"], 999), l["name"]))
    ligi = _int(request.args.get("ligi"))
    if ligi not in leagues:
        ligi = None
    shown = [f for f in day_rows if ligi is None or f["league_id"] == ligi]
    groups = []
    for l in league_list:
        items = [f for f in shown if f["league_id"] == l["id"]]
        if items:
            items.sort(key=lambda f: f["kickoff"])
            groups.append({"league": l, "items": items})
    ctx.update(days=days, siku=siku, league_list=league_list, ligi=ligi, groups=groups, total=len(shown),
               slip_ids={x["f"] for x in ctx["slip"]})


def _new_api():
    """Kuweka mkeka kwa mechi halisi (moja au nyingi): chagua mechi -> chaguo -> ongeza kwenye kapu
    -> kamilisha (kampuni na bei). Odds zinatoka kwenye huduma, si kwa mtumiaji."""
    now = datetime.now(timezone.utc)
    q = request.values.get("q", "").strip()[:40]
    fid = _int(request.values.get("mechi"))
    finish = request.values.get("kamilisha") == "1" or request.form.get("kamilisha") == "1"
    ctx = dict(active="jamvi", api_mode=True, q=q, fixtures=[], fixture=None, markets=[], chosen=None,
               svc_error=None, errors=[], form={"price": "0", "body": ""}, slip=_slip(), finish=False,
               view=[], combos=[], max_price=Config.TIP_MAX_PRICE, fee=Config.TIP_FEE_PCT, leagues=[],
               max_legs=Config.MAX_SLIP_LEGS)

    if finish:
        return _finish(ctx, now)

    if fid is None:
        ctx["svc_error"] = football.ensure_fixtures()
        _browse(ctx, q, now)
        return render_template("jamvi_weka.html", **ctx)

    fx = football.get_fixture(fid)
    if not _fixture_ok(fx, now):
        flash("Mechi hii haipatikani tena kwa mikeka (imeanza au imeondolewa). Chagua nyingine.", "error")
        return redirect(url_for("tips.new"))
    ctx["fixture"] = fx
    rows = []
    try:
        rows = football.get_odds(fid)
    except football.FootballError as e:
        ctx["svc_error"] = str(e)
    except Exception:
        current_app.logger.exception("odds za mechi %s zimeshindwa kusomwa", fid)
        ctx["svc_error"] = "Odds za mechi hii hazikuweza kusomwa sasa. Jaribu mechi nyingine au baadaye."
    ctx["markets"] = football.options(rows, fx["home"], fx["away"])
    valid = {o["key"]: o for mk in ctx["markets"] for o in mk["options"]}
    chosen = request.values.get("chaguo", "")
    if chosen in valid:
        ctx["chosen"] = valid[chosen]
    ctx["in_slip"] = next((x["c"] for x in ctx["slip"] if x["f"] == fid), None)
    return render_template("jamvi_weka.html", **ctx)


def _finish(ctx, now):
    ctx["finish"] = True
    view, dropped, problem = _slip_view(now)
    ctx["svc_error"] = problem
    if dropped:
        flash("Mechi hizi ziliondolewa kwa sababu zimeanza au hazina odds tena: " + ", ".join(dropped), "info")
    ctx["slip"] = _slip()
    if not ctx["slip"]:
        flash("Mkeka wako haujawa na mechi. Chagua mechi kwanza.", "error")
        return redirect(url_for("tips.new"))
    combos = _combos(view)
    ctx.update(view=view, combos=combos)

    if request.method == "POST":
        errors = ctx["errors"]
        price = _int(request.form.get("price", "0") or "0")
        body = request.form.get("body", "").strip()
        book = _int(request.form.get("bookmaker", ""))
        ctx["form"] = {"price": request.form.get("price", "0"), "body": body, "bookmaker": book}
        picked = next((b for b in combos if b["id"] == book), None)
        if problem or len(view) != len(ctx["slip"]):
            errors.append("Odds za baadhi ya mechi hazikupatikana sasa. Jaribu tena baadaye.")
        elif picked is None:
            errors.append("Chagua kampuni ya kubashiri ambayo odds zake umetumia.")
        elif picked["total"] > 1000:
            errors.append("Odds jumla zisizidi 1000. Ondoa mechi moja au zaidi.")
        if len(body) > 500:
            errors.append("Maelezo ya ziada yasizidi herufi 500.")
        if price is None or (price != 0 and not 5 <= price <= Config.TIP_MAX_PRICE):
            errors.append(f"Bei iwe 0 (bure) au kati ya coin 5 na {Config.TIP_MAX_PRICE}.")
        if not errors:
            times = models.recent_times("tips", g.user["id"], Config.MAX_TIPS_PER_DAY)
            if len(times) >= Config.MAX_TIPS_PER_DAY and times[-1] > now - timedelta(hours=24):
                errors.append(f"Umefikia kikomo cha mikeka {Config.MAX_TIPS_PER_DAY} kwa siku. Jaribu kesho.")
        if not errors and len(view) == 1 and db.query(
                "SELECT 1 AS x FROM tips WHERE user_id = %s AND fixture_id = %s AND market = %s AND selection = %s",
                (g.user["id"], view[0]["fx"]["id"], view[0]["market"], view[0]["selection"]), one=True):
            errors.append("Tayari umeshaweka mkeka huu kwa mechi hii.")
        if not errors:
            tip_id = _create_from_view(view, picked, body, price)
            _save_slip([])
            flash(f"Mkeka umewekwa kwa odds {picked['total']:.2f} ({picked['name']}).", "ok")
            return _back(tip_id)
        return render_template("jamvi_weka.html", **ctx), 400
    return render_template("jamvi_weka.html", **ctx)


def _create_from_view(view, picked, body, price):
    legs = []
    for v, odd in zip(view, picked["per"]):
        fx = v["fx"]
        legs.append(dict(fixture_id=fx["id"], title=f"{fx['home']} vs {fx['away']}", league=fx["league_name"],
                         market=v["market"], selection=v["selection"], pick=v["opt"]["label"], odds=odd,
                         kickoff=fx["kickoff"]))
    legs.sort(key=lambda l: l["kickoff"])
    if len(legs) == 1:
        l = legs[0]
        return models.create_tip(g.user["id"], title=l["title"], league=l["league"][:40], pick=l["pick"],
                                 body=body, odds=picked["total"], price=price, starts_at=l["kickoff"],
                                 fixture_id=l["fixture_id"], market=l["market"], selection=l["selection"],
                                 bookmaker=picked["name"])
    leagues = {l["league"] for l in legs}
    return models.create_tip(
        g.user["id"], title=f"{legs[0]['title']} +{len(legs) - 1} mechi",
        league=(next(iter(leagues)) if len(leagues) == 1 else "Ligi mbalimbali")[:40],
        pick=" + ".join(l["pick"] for l in legs)[:300], body=body, odds=picked["total"], price=price,
        starts_at=legs[0]["kickoff"], bookmaker=picked["name"], legs=legs)


# ---------- Ukurasa wa mkeka ----------
@bp.route("/<int:tip_id>")
def detail(tip_id):
    football.maybe_settle()
    tip = _get_or_404(tip_id)
    is_admin = bool(g.user and g.user["is_admin"])
    auto = bool(tip["fixture_id"]) or tip["legs"] > 1  # mkeka wa mechi halisi unahukumiwa na mfumo
    return render_template(
        "mkeka.html", active="jamvi", t=tip, comments=models.list_comments(tip_id),
        fixture=football.get_fixture(tip["fixture_id"]) if tip["fixture_id"] else None, auto=auto,
        legs=models.get_legs(tip_id) if tip["legs"] > 1 else [],
        can_settle=is_admin or (not auto and tip["is_owner"] and tip["status"] == "open" and tip["started"]),
        can_delete=tip["is_owner"] and tip["buyers"] == 0,
        is_admin=is_admin, fee=Config.TIP_FEE_PCT, lock_min=Config.LOCK_MINUTES_BEFORE,
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
    elif tip["fixture_id"] or tip["legs"] > 1:
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
