# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Copyright (c) 2021 Oliver Ni

import random

import discord
from discord.ext import commands, menus
from helpers.pagination import AsyncFieldsPageSource


class Levels(commands.Cog):
    """For XP and levels."""

    def __init__(self, bot):
        self.bot = bot

    def min_xp_at(cls, level):
        return (2 * level * level + 27 * level + 91) * level * 5 // 6

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None or message.author.bot:
            return

        # Set 60s timeout between messages
        if await self.bot.redis.get(f"xp:{message.author.id}") is not None:
            return
        await self.bot.redis.set(f"xp:{message.author.id}", 1, expire=60)

        xp = random.randint(15, 25)
        user = await self.bot.mongo.db.member.find_one_and_update(
            {"_id": message.author.id}, {"$inc": {"messages": 1, "xp": xp}}
        )

        if user.get("xp", 0) + xp > self.min_xp_at(user.get("level", 0) + 1):
            await self.bot.mongo.db.member.update_one({"_id": message.author.id}, {"$inc": {"level": 1}})
            msg = (
                f"Congratulations {message.author.mention}, you are now level **{user.get('level', 0) + 1}**!"
            )
            await message.channel.send(msg)

    @commands.command(aliases=("rank", "level"))
    async def xp(self, ctx):
        """Shows your server XP and level."""

        user = await self.bot.mongo.db.member.find_one({"_id": ctx.author.id})
        rank = await self.bot.mongo.db.member.count_documents(
            {"xp": {"$gt": user.get("xp", 0)}, "_id": {"$ne": ctx.author.id}}
        )
        xp, level = user.get("xp", 0), user.get("level", 0)
        progress = xp - self.min_xp_at(level)
        required = self.min_xp_at(level + 1) - self.min_xp_at(level)

        embed = discord.Embed(color=discord.Color.blurple())
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        embed.title = f"Level {level}"
        embed.add_field(name="XP", value=str(xp))
        embed.add_field(name="Progress", value=f"{progress}/{required}")
        embed.add_field(name="Rank", value=str(rank + 1))
        await ctx.send(embed=embed)

    @commands.command(aliases=("top", "lb", "levels"))
    async def leaderboard(self, ctx):
        """Displays the server XP leaderboard."""

        users = self.bot.mongo.db.member.find().sort("xp", -1)
        count = await self.bot.mongo.db.member.count_documents({})

        def format_embed(embed):
            embed.set_thumbnail(url=ctx.guild.icon_url)

        def format_item(i, x):
            name = f"{i + 1}. {x['name']}#{x['discriminator']}"
            if x.get("nick") is not None:
                name = f"{name} ({x['nick']})"
            return {
                "name": name,
                "value": f"{x.get('xp', 0)} (Level {x.get('level', 0)})",
                "inline": False,
            }

        pages = menus.MenuPages(
            source=AsyncFieldsPageSource(
                users,
                title=f"XP Leaderboard",
                format_embed=format_embed,
                format_item=format_item,
                count=count,
            )
        )
        await pages.start(ctx)


def setup(bot):
    bot.add_cog(Levels(bot))
