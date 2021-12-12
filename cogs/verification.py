# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Copyright (c) 2021 Oliver Ni

import json

import discord
from discord.ext import commands, ipc
from helpers.oauth import AsyncSchoologyOAuth1Client

API_BASE_URL = "https://api.schoology.com/v1"
SCHOOLOGY_URL = "https://fuhsd.schoology.com"

REQUEST_URL = f"{API_BASE_URL}/oauth/request_token"
ACCESS_TOKEN_URL = f"{API_BASE_URL}/oauth/access_token"
AUTH_URL = f"{SCHOOLOGY_URL}/oauth/authorize"


class Verification(commands.Cog):
    """For verifying server members."""

    def __init__(self, bot):
        self.bot = bot

    def client(self, **kwargs):
        return AsyncSchoologyOAuth1Client(
            self.bot.config.SCHOOLOGY_API_KEY,
            self.bot.config.SCHOOLOGY_API_SECRET,
            redirect_uri=f"{self.bot.config.BASE_URL}/callback",
            **kwargs,
        )

    @ipc.server.route()
    async def callback(self, data):
        info = await self.bot.redis.get(f"oauth:{data.token}")
        await self.bot.redis.delete(f"oauth:{data.token}")
        if info is None:
            return {"status": "error", "error": "not-found"}

        info = json.loads(info)
        user = self.bot.get_user(info["user_id"])
        if user is None:
            return {"status": "error", "error": "user-not-found"}

        return await self.verify_user(user, info["token"]["oauth_token"], info["token"]["oauth_token_secret"])

    async def verify_user(self, user, token, secret):
        async with self.client(verifier=str(user.id), token=token, token_secret=secret) as client:
            await client.fetch_access_token(ACCESS_TOKEN_URL)
            r = await client.get(f"{API_BASE_URL}/users/me", allow_redirects=False)
            if r.status_code == 303:
                r = await client.get(r.headers["Location"])
            data = r.json()

        if (
            int(data["school_id"]) == self.bot.config.SCHOOLOGY_SCHOOL_ID
            and int(data["grad_year"]) == self.bot.config.SCHOOLOGY_GRAD_YEAR
        ):
            await self.approve_user(user, data)
            return {"status": "success", "result": "approved"}
        else:
            await self.reject_user(user, data)
            return {"status": "success", "result": "rejected"}

    async def approve_user(self, user, data):
        await self.bot.mongo.db.member.update_one(
            {"_id": user.id}, {"$set": {"schoology": data}}, upsert=True
        )

        guild = self.bot.get_guild(self.bot.config.GUILD_ID)
        role = discord.utils.get(guild.roles, name="Member")
        member = guild.get_member(user.id)
        await member.add_roles(role)
        try:
            await member.edit(nick=data["name_display"])
        except discord.Forbidden:
            pass

        embed = discord.Embed(color=discord.Color.blurple())
        embed.title = f"Welcome, {data['name_display']}!"
        embed.description = "Welcome to the Lynbrook Class of 2022 server! You now have full access to the server. Please make sure to follow the rules at all times!"
        await user.send(embed=embed)

    async def reject_user(self, user, data):
        msg = f"Hi {data['name_display']}, unfortunately only Lynbrook students from the Class of 2022 are allowed to join the server at this time."
        await user.send(msg)

    @commands.command()
    @commands.dm_only()
    async def verify(self, ctx):
        """Verify yourself to access the server."""

        guild = self.bot.get_guild(self.bot.config.GUILD_ID)
        member = guild.get_member(ctx.author.id)
        if discord.utils.get(member.roles, name="Member") is not None:
            return await ctx.send("You are already verified!")

        async with self.client(verifier=str(ctx.author.id)) as client:
            token = await client.fetch_request_token(REQUEST_URL)
            url = client.create_authorization_url(AUTH_URL)

        await self.bot.redis.set(
            f"oauth:{token['oauth_token']}",
            json.dumps({"user_id": ctx.author.id, "token": token}),
            expire=3600,
        )

        embed = discord.Embed(color=discord.Color.blurple())
        embed.title = "Sign in with Schoology"
        embed.description = (
            "Please verify that you are a member of the Lynbrook Class of 2022 by clicking the link above."
        )
        embed.url = url
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Verification(bot))
