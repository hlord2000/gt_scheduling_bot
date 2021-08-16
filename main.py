from discord.ext import tasks, commands
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_commands import create_option
import os
import schedule

import collector
from collector import update_database
from course import *
import asyncio
from dotenv import load_dotenv
import threading
import aiocron


def run():
    description = '''A bot intended to make Georgia Tech's class search
    LESS TERRIBLE'''

    bot = commands.Bot(command_prefix="`", description=description)

    slash = SlashCommand(bot, sync_commands=True)
    guild_ids = [797968601575325707, 575726573852819508, 760550078448140346, 823735719708590110]

    @bot.event
    async def on_ready():
        print("ready, sama")

    @slash.slash(name="search",
                 description="Input your department, course number, season, and year to search.",
                 options=[
                     create_option(
                         name="department",
                         description="Input department code, e.g. ECE",
                         option_type=3,
                         required=True
                     ),
                     create_option(
                         name="coursenum",
                         description="Input course number, e.g. 2031",
                         option_type=3,
                         required=True
                     ),
                     create_option(
                         name="season",
                         description="Input season, e.g. Fall",
                         option_type=3,
                         required=False
                     ),
                     create_option(
                         name="year",
                         description="Input year, e.g. 1969",
                         option_type=3,
                         required=False
                     ),
                 ],
                 guild_ids=guild_ids)
    async def _search(ctx: SlashContext, department: str, coursenum: str, season=None, year=None):
        msg = await ctx.send(f"Working on {department.upper()} {coursenum}!")

        try:
            if type(season) is not str or type(year) is not str:
                report = DataReporting(department, coursenum, 0)
            else:
                report = DataReporting(department, coursenum, str(season + " " + year))
            report.collect_class_data()

            if len(report.courses) > 0:
                await msg.edit(embed=report.format_class_data())
            else:
                await msg.edit(content="Course could not be found.")
        except KeyError:
            await msg.edit(content="Course could not be found.")

    @commands.cooldown(1, 360, commands.BucketType.guild)
    @slash.slash(name="kevin",
                 description="KeyError: UNKNOWN",
                 guild_ids=guild_ids)
    async def _kevin(ctx: SlashContext):
        await ctx.send("ECE2031 has been the most impactful, practical class in my time at Tech; it truly "
                       "establishes useful skills of the trade that any electrical or computer engineer needs "
                       "from using scopes to blinking LEDs. If I could, I would retake this class as an "
                       "elective to gain more understanding of the plethora of features the DE2 offers as a "
                       "state of the art FPGA. I currently make SRAM on the side as a personal hobby. ECE2031 "
                       "taught me if I don't have enough storage for all the important things in life, "
                       "I can just make more.", delete_after=60)

    @aiocron.crontab('0 3 * * MON')
    async def database():
        collector.update_database()

    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')
    bot.run(TOKEN)


if __name__ == "__main__":
    run()
