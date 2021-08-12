from pathlib import Path

import discord
from discord.ext import commands, events, ipc
from discord.ext.events import member_kick

import config

DEFAULT_COGS = [
    "bot",
    "help",
    "info",
    "mongo",
    "redis",
    "verification",
]


class Bot(commands.Bot, events.EventsMixin):
    def __init__(self, **kwargs):
        super().__init__(
            **kwargs,
            command_prefix=config.PREFIX,
            intents=discord.Intents.all(),
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False),
            case_insensitive=True,
        )

        self.config = config
        self.ipc = ipc.Server(self, secret_key=config.SECRET_KEY)

        self.load_extension("jishaku")
        for i in DEFAULT_COGS:
            self.load_extension(f"cogs.{i}")

        for i in getattr(config, "EXTRA_COGS", []):
            self.load_extension(f"cogs.{i}")

    @property
    def mongo(self):
        return self.get_cog("Mongo")

    @property
    def redis(self):
        return self.get_cog("Redis").pool

    @property
    def log(self):
        return self.get_cog("Logging").log

    async def on_ready(self):
        print(f"Ready called.")

    async def on_ipc_ready(self):
        print("IPC is ready.")

    async def on_ipc_error(self, endpoint, error):
        print(endpoint, "raised", error)

    async def close(self):
        print("Shutting down")
        await super().close()


if __name__ == "__main__":
    Path("logs").mkdir(exist_ok=True)
    Path("attachments").mkdir(exist_ok=True)
    bot = Bot()
    bot.ipc.start()
    bot.run(config.BOT_TOKEN)
