"""Orodha ya arifa za mtumiaji."""
from flask import Blueprint, g, render_template

import auth
import models

bp = Blueprint("notifications", __name__, url_prefix="/arifa")


@bp.route("")
@auth.login_required
def index():
    rows = models.list_notifications(g.user["id"])
    models.mark_notifications_read(g.user["id"])  # zinaangaziwa kwenye ukurasa huu kisha zinawekwa zimesomwa
    return render_template("arifa.html", active="arifa", items=rows)
