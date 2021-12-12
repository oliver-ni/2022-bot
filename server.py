# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Copyright (c) 2021 Oliver Ni

import config
from discord.ext import ipc
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse, Response
from starlette.templating import Jinja2Templates

ipc_client = ipc.Client(secret_key=config.SECRET_KEY)
app = Starlette(debug=True)

templates = Jinja2Templates(directory="templates")

msg_dict = {
    "unknown-error": (
        "alert-circle",
        "Error",
        "An unknown error has occurred. Please try again later.",
    ),
    "not-found": (
        "alert-circle",
        "Error",
        "The authorization request was not found. It may have expired. Please try again.",
    ),
    "approved": (
        "checkmark-circle",
        "Approved",
        "You have been approved! You can now close this tab and return to Discord.",
    ),
    "rejected": (
        "close-circle",
        "Rejected",
        "Unfortunately, your account has been rejected. Our server is only for members of the Lynbrook Class of 2022.",
    ),
}


@app.on_event("startup")
async def startup():
    print("Ready to go!")


@app.route("/")
async def homepage(request):
    return PlainTextResponse("Hello World!")


@app.route("/callback")
async def callback(request):
    if "oauth_token" not in request.query_params:
        return Response(status_code=400)

    resp = await ipc_client.request("callback", token=request.query_params["oauth_token"])
    icon, title, message = msg_dict[resp.get("error", resp.get("result", "unknown-error"))]

    return templates.TemplateResponse(
        "success.html", {"request": request, "icon": icon, "title": title, "message": message}
    )
