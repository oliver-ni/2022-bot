from datetime import datetime
from datetime import timedelta
from dateutil.parser import parse

import discord
import json
from discord.ext import commands, tasks
from aiogoogle import Aiogoogle
from aiogoogle.auth.creds import ServiceAccountCreds

CLASS_EVENTS_CALENDAR = "465gi7ilseitglkbohd2dgrd6o@group.calendar.google.com"
ASB_EVENTS_CALENDAR = "qd1epm3o57ns1e5umjq6hfnric@group.calendar.google.com"


async def list_calendar(aiogoogle, calendar_id):
    calendar_v3 = await aiogoogle.discover("calendar", "v3")
    return await aiogoogle.as_service_account(
        calendar_v3.events.list(
            calendarId=calendar_id,
            timeMin=datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            timeMax=(datetime.now() + timedelta(weeks=4)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
    )


class Events(commands.Cog):
    """Get info about upcoming events."""

    def __init__(self, bot):
        self.bot = bot
        self.class_events = None
        self.refresh_calendar.start()

    @tasks.loop(minutes=15)
    async def refresh_calendar(self):
        async with Aiogoogle(service_account_creds=self.creds) as aiogoogle:
            self.class_events = await list_calendar(aiogoogle, CLASS_EVENTS_CALENDAR)
            self.asb_events = await list_calendar(aiogoogle, ASB_EVENTS_CALENDAR)

    @refresh_calendar.before_loop
    async def before_refresh_calendar(self):
        with open(self.bot.config.GOOGLE_CREDS_FILE) as f:
            self.creds = ServiceAccountCreds(
                scopes=["https://www.googleapis.com/auth/calendar.events.readonly"],
                **json.load(f),
            )

    @commands.command()
    async def events(self, ctx):
        """Displays information about upcoming events."""

        embed = discord.Embed(color=discord.Color.blurple())
        embed.title = "All Events"

        for event in self.class_events["items"] + self.asb_events["items"]:
            start = parse(event["start"]["date"])
            end = parse(event["end"]["date"])
            date = (
                f"{start:%B %-d, %Y}"
                if start + timedelta(days=1) >= end
                else f"{start:%B %-d, %Y} – {end:%B %-d, %Y}"
            )
            embed.add_field(name=event["summary"], value=date, inline=False)

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Events(bot))
