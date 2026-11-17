"""Pochi ya coin: kununua na kutoa (hali ya majaribio tu hadi malipo halisi yawashwe)."""
import re
import uuid

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

import auth
import db
import models
from config import Config

bp = Blueprint("wallet", __name__, url_prefix="/pochi")

PACKAGES = [50, 100, 500, 1000]
NETWORKS = {"mpesa": "M-Pesa", "tigo": "Tigo Pesa", "airtel": "Airtel Money"}
TOKEN_RE = re.compile(r"^[0-9a-f]{32}$")


def _int(raw):
    return int(raw) if re.fullmatch(r"[0-9]{1,9}", raw or "") else None


def _blocked():
    """Coin hazitolewi wala hazinunuliwi kwa pesa halisi hadi hatua ya 8."""
    if Config.COIN_MODE != "demo":
        flash("Malipo halisi bado hayajawashwa.", "error")
        return redirect(url_for("pochi"))
    return None


@bp.route("/nunua", methods=["GET", "POST"])
@auth.login_required
def buy():
    blocked = _blocked()
    if blocked:
        return blocked
    errors = []
    if request.method == "POST":
        token = request.form.get("token", "")
        coins = _int(request.form.get("coins", ""))
        if not TOKEN_RE.match(token):
            errors.append("Fomu imepitwa na wakati. Jaribu tena.")
        elif coins not in PACKAGES:
            errors.append("Chagua kifurushi cha coin.")
        else:
            try:
                balance = models.wallet_change(
                    g.user["id"], coins, "buy", f"Kununua coin {coins} (majaribio)",
                    idem_key=f"{g.user['id']}:{token}",
                )
            except db.IntegrityError:
                flash("Ombi hili tayari limeshashughulikiwa.", "info")
                return redirect(url_for("pochi"))
            flash(f"Umeongeza coin {coins} (majaribio). Salio jipya: {balance}.", "ok")
            return redirect(url_for("pochi"))
    return render_template("pochi_nunua.html", packages=PACKAGES, token=uuid.uuid4().hex,
                           errors=errors, active="pochi"), (400 if errors else 200)


@bp.route("/toa", methods=["GET", "POST"])
@auth.login_required
def withdraw():
    blocked = _blocked()
    if blocked:
        return blocked
    phone_default = ("0" + g.user["phone"][4:]) if g.user["phone"] else ""
    form, errors = {"phone": phone_default, "network": "mpesa", "amount": ""}, []
    if request.method == "POST":
        form = {k: request.form.get(k, "").strip() for k in ("amount", "network", "phone")}
        token = request.form.get("token", "")
        amount = _int(form["amount"])
        phone = auth.normalize_phone(form["phone"])

        if not TOKEN_RE.match(token):
            errors.append("Fomu imepitwa na wakati. Jaribu tena.")
        if amount is None or amount <= 0:
            errors.append("Weka idadi sahihi ya coin (namba nzima).")
        elif amount < Config.MIN_WITHDRAW:
            errors.append(f"Kiwango cha chini cha kutoa ni coin {Config.MIN_WITHDRAW}.")
        elif amount > g.user["balance"]:
            errors.append("Salio lako halitoshi.")
        if form["network"] not in NETWORKS:
            errors.append("Chagua mtandao wa kupokelea pesa.")
        if not phone:
            errors.append("Weka namba sahihi ya simu ya Tanzania.")

        if not errors:
            note = f"Kutoa kwenda {NETWORKS[form['network']]} ***{phone[-3:]} (majaribio)"
            try:
                balance = models.wallet_change(
                    g.user["id"], -amount, "withdraw", note,
                    idem_key=f"{g.user['id']}:{token}",
                )
            except models.InsufficientFunds:
                errors.append("Salio lako halitoshi.")
            except db.IntegrityError:
                flash("Ombi hili tayari limeshashughulikiwa.", "info")
                return redirect(url_for("pochi"))
            else:
                flash(f"Ombi la kutoa coin {amount} limekamilika (majaribio, hakuna pesa halisi "
                      f"iliyotumwa). Salio jipya: {balance}.", "ok")
                return redirect(url_for("pochi"))
    return render_template("pochi_toa.html", form=form, networks=NETWORKS, token=uuid.uuid4().hex,
                           errors=errors, active="pochi"), (400 if errors else 200)
