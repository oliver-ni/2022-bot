from discord.ext import ipc
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
import config
import aioredis


ipc_client = ipc.Client(secret_key=config.SECRET_KEY)
app = Starlette(debug=True)
conn = None


@app.on_event("startup")
async def startup():
    global conn
    conn = await aioredis.create_redis_pool(config.REDIS_URL)
    print("Ready to go!")


@app.route("/")
async def homepage(request):
    return PlainTextResponse("Hello, world!")


@app.route("/callback")
async def callback(request):
    await ipc_client.request("callback", token=request.query_params["oauth_token"])
    return PlainTextResponse("OK")
