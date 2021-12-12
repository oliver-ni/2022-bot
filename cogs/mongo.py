# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Copyright (c) 2021 Oliver Ni

from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorClient


class Mongo(commands.Cog):
    """For database operations."""

    def __init__(self, bot):
        self.bot = bot
        self.client = AsyncIOMotorClient(bot.config.DATABASE_URI, io_loop=bot.loop)
        self.db = self.client[bot.config.DATABASE_NAME]

    async def reserve_id(self, name, reserve=1):
        result = await self.db.counter.find_one_and_update(
            {"_id": name}, {"$inc": {"next": reserve}}, upsert=True
        )
        if result is None:
            return 0
        return result["next"]


def setup(bot):
    bot.add_cog(Mongo(bot))
