import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio
import logging
from datetime import datetime



logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'bot_{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('discord')

load_dotenv()
token = os.getenv("BOT_TOKEN")
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!',intents=intents)

async def load_cogs():
    try:
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py') and filename != '__init__.py':
                try:
                    await bot.load_extension(f'cogs.{filename[:-3]}')
                    logger.info(f"Loaded cog: {filename}")
                except Exception as e:
                    logger.error(f"Failed to load cog {filename}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Error loading cogs: {e}", exc_info=True)

@bot.event
async def on_ready():
    logger.info(f"MARBLE is online! Logged in as {bot.user.name} (ID: {bot.user.id})")
    print(f"MARBLE is online!") 

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for commands."""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: `{error.param.name}`")
        logger.warning(f"Missing argument in {ctx.command}: {error}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument provided.")
        logger.warning(f"Bad argument in {ctx.command}: {error}")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏱️ This command is on cooldown. Try again in {error.retry_after:.2f}s")
        logger.info(f"Command on cooldown: {ctx.command}")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send(f"❌ You don't have permission to use this command.")
        logger.warning(f"Permission denied for {ctx.author} in {ctx.command}")
    else:
        await ctx.send(f"❌ An error occurred while executing the command.")
        logger.error(f"Error in command {ctx.command}: {error}", exc_info=True)

@bot.command()
async def hi(ctx):
    """Says hello to you!"""
    try:
        await ctx.send("HELLO!")
        logger.info(f"Hi command used by {ctx.author}")
    except Exception as e:
        logger.error(f"Error in hi command: {e}", exc_info=True)
        await ctx.send("❌ An error occurred.")

@bot.command()
@commands.is_owner()
async def exportleaderboard(ctx):
    """Export the current leaderboard JSON (owner only)"""
    try:
        with open("loltriviaLeaderboards.json", "r", encoding="utf8") as file:
            await ctx.send(file=discord.File(file, "loltriviaLeaderboards.json"))
    except FileNotFoundError:
        await ctx.send("No leaderboard file found!")


try:
    asyncio.run(load_cogs())
    bot.run(token=token)
except KeyboardInterrupt:
    logger.info("Bot shutdown requested by user")
except Exception as e:
    logger.critical(f"Fatal error: {e}", exc_info=True)