"""Ujumbe wa moja kwa moja kati ya watumiaji wawili, na kuzuia."""
from datetime import datetime, timedelta, timezone

from flask import (Blueprint, abort, flash, g, jsonify, redirect,
                   render_template, request, url_for)

import auth
import models
from config import Config

bp = Blueprint("chat", __name__, url_prefix="/ujumbe")


def _other(username):
    """Mwenzi wa mazungumzo; 404 kama hayupo au amefungiwa akaunti."""
    u = models.get_user_by_username(username)
    if not u or u["is_banned"]:
        abort(404)
    return u


@bp.route("")
@auth.login_required
def inbox():
    q = request.args.get("q", "").strip()[:40]
    convs = models.inbox(g.user["id"])
    people = []
    if q:
        ql = q.lstrip("@").lower()
        convs = [c for c in convs if ql in c["user"]["username"].lower() or ql in c["user"]["display_name"].lower()
                 or ql in c["last"]["body"].lower()]
        have = {c["user"]["username"] for c in models.inbox(g.user["id"])}
        people = [p for p in models.search_chat_users(q, g.user["id"]) if p["username"] not in have]
    return render_template("mazungumzo.html", active="ujumbe", convs=convs, q=q, people=people)


@bp.route("/<username>", methods=["GET", "POST"])
@auth.login_required
def conversation(username):
    other = _other(username)
    me = g.user["id"]
    if other["id"] == me:
        return redirect(url_for("chat.inbox"))

    if request.method == "POST":
        body = request.form.get("body", "").strip()
        times = models.recent_times("messages", me, Config.MESSAGES_PER_MINUTE)
        if not 1 <= len(body) <= Config.MAX_MESSAGE_LEN:
            flash(f"Ujumbe uwe na herufi 1 hadi {Config.MAX_MESSAGE_LEN}.", "error")
        elif len(times) >= Config.MESSAGES_PER_MINUTE and \
                times[-1] > datetime.now(timezone.utc) - timedelta(seconds=60):
            flash("Unatuma ujumbe haraka mno. Subiri kidogo.", "error")
        else:
            try:
                models.send_message(me, other["id"], body)
            except models.ChatError as e:
                flash(str(e), "error")
        return redirect(url_for("chat.conversation", username=username))

    models.mark_thread_read(me, other["id"])
    msgs = models.thread(me, other["id"])
    return render_template("ujumbe.html", active="ujumbe", other=other, msgs=msgs,
                           state=models.block_state(me, other["id"]),
                           last_id=msgs[-1]["id"] if msgs else 0,
                           max_len=Config.MAX_MESSAGE_LEN)


@bp.route("/<username>/mpya")
@auth.login_required
def poll(username):
    """Ujumbe mpya tu (JSON) kwa ajili ya kuonyesha bila kupakia ukurasa upya."""
    other = _other(username)
    me = g.user["id"]
    if other["id"] == me:
        abort(404)
    try:
        after = int(request.args.get("baada", "0"))
    except ValueError:
        after = 0
    rows = models.thread(me, other["id"], after_id=after)
    models.mark_thread_read(me, other["id"])
    resp = jsonify([
        {"id": m["id"], "mine": m["sender_id"] == me, "body": m["body"],
         "time": models.to_dt(m["created_at"]).astimezone(models.EAT).strftime("%H:%M")}
        for m in rows
    ])
    resp.headers["Cache-Control"] = "no-store"
    return resp


@bp.route("/<username>/ficha", methods=["POST"])
@auth.login_required
def hide(username):
    other = models.get_user_by_username(username)
    if not other:
        abort(404)
    models.hide_conversation(g.user["id"], other["id"])
    flash("Mazungumzo yameondolewa kwenye orodha yako. Mwenzako anabaki nayo.", "ok")
    return redirect(url_for("chat.inbox"))


@bp.route("/<username>/zuia", methods=["POST"])
@auth.login_required
def block(username):
    other = _other(username)
    if other["id"] != g.user["id"]:
        models.block_user(g.user["id"], other["id"])
        flash("Mtumiaji amezuiwa. Hataweza kukutumia ujumbe.", "info")
    return redirect(url_for("chat.conversation", username=username))


@bp.route("/<username>/ondoa", methods=["POST"])
@auth.login_required
def unblock(username):
    other = _other(username)
    models.unblock_user(g.user["id"], other["id"])
    flash("Kizuizi kimeondolewa.", "info")
    return redirect(url_for("chat.conversation", username=username))
