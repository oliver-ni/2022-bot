from datetime import datetime
from datetime import timedelta
from helpers.time import strfdelta
from typing import Union
from dateutil.parser import parse

import discord
import json
from discord.ext import commands
from helpers.utils import FetchUserConverter
from aiogoogle import Aiogoogle
from aiogoogle.auth.creds import ServiceAccountCreds


class Events(commands.Cog):
    """Get info about upcoming events."""

    def __init__(self, bot):
        self.bot = bot
        with open(f"./{self.bot.config.GOOGLE_CREDS_FILE}") as f:
            self.service_account_key = json.load(f)

    @commands.command()
    async def events(self, ctx):
        """Displays information about upcoming events."""

        creds = ServiceAccountCreds(
            scopes=[
                "https://www.googleapis.com/auth/calendar.events.readonly",
            ],
            **self.service_account_key
        )
        # await ctx.send(arg)

        async with Aiogoogle(service_account_creds=creds) as aiogoogle:
            calendar_v3 = await aiogoogle.discover('calendar', 'v3')

            class_events = await aiogoogle.as_service_account(
                calendar_v3.events.list(calendarId='465gi7ilseitglkbohd2dgrd6o@group.calendar.google.com', timeMin=datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"), timeMax=(datetime.now() + timedelta(weeks=4)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
            )
            asb_events = await aiogoogle.as_service_account(
                calendar_v3.events.list(calendarId='qd1epm3o57ns1e5umjq6hfnric@group.calendar.google.com', timeMin=datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"), timeMax=(datetime.now() + timedelta(weeks=4)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
            )

            embed = discord.Embed()
            for e in class_events['items']:
                start = parse(e['start']['date'])
                end = parse(e['end']['date'])
                date = f"{start.strftime('%B %-d, %Y')}" if start + timedelta(days=1) >= end else f"{start.strftime('%B %-d, %Y')} to {end.strftime('%B %-d, %Y')}"
                embed.add_field(
                    name=e['summary'],
                    value=date,
                    inline=False
                )

            await ctx.send(embed=embed)
    


def setup(bot):
    bot.add_cog(Events(bot))
