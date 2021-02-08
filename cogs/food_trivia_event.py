import asyncio
import json
import random
import string
from datetime import datetime, timedelta

import discord
from discord.ext import commands, menus, tasks
from helpers.constants import LETTER_REACTIONS
from helpers.pagination import AsyncFieldsPageSource


async def add_reactions(message, *reactions):
    for i in reactions:
        await message.add_reaction(i)


class FoodTriviaEvent(commands.Cog):
    """For the food trivia event."""

    def __init__(self, bot):
        self.bot = bot
        with open("trivia.json") as f:
            self.questions = json.load(f)
            self.questions = [x for x in self.questions if len(x["question"]) > 0]
            self.answers = {x["answer"] for x in self.questions}
        self.start_game.start()

    def get_question(self):
        question = random.choice(self.questions)
        question["choices"] = random.sample(self.answers - {question["answer"]}, 5)
        question["correct_choice"] = random.randrange(6)
        question["choices"].insert(question["correct_choice"], question["answer"])
        return question

    async def send_question(self, question, channel):
        embed = discord.Embed(color=discord.Color.blurple())
        embed.title = question["question"]
        for choice, letter in zip(question["choices"], string.ascii_uppercase):
            embed.add_field(name=letter, value=choice)
        embed.set_footer(text="Click the reactions below to answer!")

        message = await channel.send(embed=embed)
        self.bot.loop.create_task(add_reactions(message, *LETTER_REACTIONS[:6]))
        answers = {}

        def check(reaction, user):
            if (
                reaction.message != message
                or user.bot
                or reaction.emoji not in LETTER_REACTIONS[:6]
                or user.id in answers
            ):
                return False

            answers[user.id] = LETTER_REACTIONS.index(reaction.emoji)

            if answers[user.id] == question["correct_choice"]:
                delta = datetime.utcnow() - message.created_at
                msg = f"{user.mention} correctly answered **{question['answer']}** in **{delta.total_seconds():.02f}s**! + 1 point"
                self.bot.loop.create_task(channel.send(msg))
                return True
            else:
                msg = f"{user.mention}, **{question['choices'][answers[user.id]]}** is incorrect."
                self.bot.loop.create_task(channel.send(msg))
                return False

        try:
            reaction, user = await self.bot.wait_for("reaction_add", check=check, timeout=20)
        except asyncio.TimeoutError:
            await channel.send("No one answered the question correctly in time!")
            return None
        else:
            return user

    @tasks.loop(minutes=30)
    async def start_game(self):
        channel = self.bot.get_channel(self.bot.config.TRIVIA_CHANNEL_ID)
        embed = discord.Embed(color=discord.Color.blurple())
        embed.title = "A new Food Trivia round is starting!"
        embed.description = "Compete to answer the questions the fastest!"
        embed.set_footer(text="The round will start in 30 seconds.")
        await channel.send(embed=embed)

        await asyncio.sleep(30)

        for i in range(20):
            if i != 0:
                await channel.send("The next question will be sent in 15 seconds.")
                await asyncio.sleep(15)

            question = self.get_question()
            user = await self.send_question(question, channel)
            if user is not None:
                await self.bot.mongo.db.member.update_one(
                    {"_id": user.id}, {"$inc": {"food_trivia_points": 1}}, upsert=True
                )

    @start_game.before_loop
    async def before_start_game(self):
        dt = datetime.now()
        prev_half = dt.replace(minute=30 * (dt.minute // 30), second=0, microsecond=0)
        await discord.utils.sleep_until(prev_half + timedelta(minutes=30))
        await self.bot.wait_until_ready()

    @commands.command(aliases=("eventlb", "eventtop", "etop"))
    async def eventleaderboard(self, ctx):
        """Displays the leaderboard for the Food Trivia event."""

        users = self.bot.mongo.db.member.find().sort("food_trivia_points", -1)
        count = await self.bot.mongo.db.member.count_documents({})

        def format_embed(embed):
            embed.set_thumbnail(url=ctx.guild.icon_url)

        def format_item(i, x):
            name = f"{i + 1}. {x['name']}#{x['discriminator']}"
            if x.get("nick") is not None:
                name = f"{name} ({x['nick']})"
            return {
                "name": name,
                "value": str(x.get("food_trivia_points", 0)),
                "inline": False,
            }

        pages = menus.MenuPages(
            source=AsyncFieldsPageSource(
                users,
                title=f"Food Trivia Event Leaderboard",
                format_embed=format_embed,
                format_item=format_item,
                count=count,
            )
        )
        await pages.start(ctx)

    def cog_unload(self):
        self.start_game.cancel()


def setup(bot):
    bot.add_cog(FoodTriviaEvent(bot))
