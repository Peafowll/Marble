import discord
from discord.ext import commands, tasks
import datetime
from zoneinfo import ZoneInfo
import logging
from config import FABI_DISCORD_ID
logger = logging.getLogger('discord.bouncyfriday')


class BouncyFriday(commands.Cog):
    """
    Discord cog dedicated to Fabi Painite.
    
    This cog runs a scheduled task every Friday at 00:01 AM (Europe/Bucharest).
    """
    
    def __init__(self, bot):
        self.bot = bot
        if not self.friday_event.is_running():
            self.friday_event.start()

    def cog_unload(self):
        if self.friday_event.is_running():
            self.friday_event.cancel()

    @tasks.loop(time=datetime.time(hour=0, minute=1, tzinfo=ZoneInfo("Europe/Bucharest")))
    async def friday_event(self):

        now = datetime.datetime.now(ZoneInfo("Europe/Bucharest"))
        
        if now.weekday() != 4:
            return
        
        logger.info("Bouncy Friday event triggered!")

        fabi_id = FABI_DISCORD_ID
        try:
            user = await self.bot.fetch_user(fabi_id)

            await user.send("https://media.discordapp.net/attachments/770707454027104269/1176860738992734258/591236411127234571.gif?ex=69d102f9&is=69cfb179&hm=3c637d81c19e3920cfaac7366f7845d6cc1b6fc3858f663ffa7e57434f868fc2&")
        except discord.NotFound:
            logger.error("Fabi wasn't found.")
        except discord.Forbidden:
            logger.error("Fabi forbidded messages.")
        except Exception as e:
            logger.error(f"Error in bouncy friday gif sending : {e}")

    @friday_event.before_loop
    async def before_friday_event(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    try:
        await bot.add_cog(BouncyFriday(bot))
        logger.info("BouncyFriday cog successfully loaded.")
    except Exception as e:
        logger.error(f"Failed to load BouncyFriday cog: {e}")
        raise e