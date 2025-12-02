import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio
import logging
import json
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
    try:
        with open("CHANGELOG.md", "r", encoding="utf8") as file:
            changelog_content = file.read()
        
        for line in changelog_content.split('\n'):
            if line.startswith('## [') and 'Unreleased' not in line:
                # Extract version from line like "## [1.0.0] - 2025-11-16"
                # This works by first splitting it intp "[" , "1.0.0] - 2025-11-16" and then "[" , "1.0.0" , "] - 2025-11-16"
                version = line.split('[')[1].split(']')[0]
                
                await bot.change_presence(
                    activity=discord.Game(name=f"v{version} | !changelog | \"!\" for commands!")
                )
                logger.info(f"Set bot status to version {version}")
                break
    except Exception as e:
        logger.warning(f"Could not set version status: {e}")
        await bot.change_presence(activity=discord.Game(name="!changelog for updates"))
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


@bot.command(aliases=['updates', 'changes', 'whatsnew'])
async def changelog(ctx, size: str = "minor"):
    """View the changelog for Marble bot updates!
    
    Usage: !changelog
    - Shows changes up to the last minor update
    - Use !changelog all to see the full changelog
    - Use !changelog major to see changes up to the last major update
    - Use !changelog minor to see changes up to the last minor update
    - Use !changelog patch/latest to see only the last patch
    """
    try:
        size = size.lower()
        if size == "latest":
            size = "patch"
        valid_responses = ["major","minor","patch","all"]
        if size not in valid_responses:
            raise commands.BadArgument
        with open("CHANGELOG.md", "r", encoding="utf8") as file:
            changelog_content = file.read()
            lines = changelog_content.split('\n')
            latest_section = []
            in_section = False
            section_count = 0
            first_minor = None
            first_major = None
            first_patch = None
            changed_patch = False
            changed_minor = False
            changed_major = False
            for line in lines:
                if line.startswith('## ['):
                    section_count += 1
                    in_section = True

                    current_version = line.split("[")[1].split("]")[0]

                    current_major = int(current_version.split(".")[0])
                    current_minor = int(current_version.split(".")[1])
                    current_patch = int(current_version.split(".")[2])

                    if first_minor == None:
                        first_minor = current_minor
                        first_major = current_major
                        first_patch = current_patch
                    else:
                        changed_minor = first_minor!=current_minor
                        changed_patch = first_patch!=current_patch
                        changed_major = first_major!=current_major
                   
                    if changed_major and size == "major":
                        break
                    if changed_minor and size == "minor":
                        break
                    if changed_patch and size == "patch":
                        break 
                
                if in_section:
                    latest_section.append(line)
            
            latest_content = '\n'.join(latest_section)
            
            embed = discord.Embed(
                title="📜 Marble Changelog",
                description=latest_content[:4000],
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            await ctx.send(embed=embed)
        
        logger.info(f"Changelog command used by {ctx.author}")
    except FileNotFoundError:
        await ctx.send("❌ Changelog file not found!")
        logger.error("CHANGELOG.md file not found")
    except Exception as e:
        logger.error(f"Error in changelog command: {e}", exc_info=True)
        await ctx.send("❌ An error occurred while reading the changelog.")

try:
    asyncio.run(load_cogs())
    bot.run(token=token)
except KeyboardInterrupt:
    logger.info("Bot shutdown requested by user")
except Exception as e:
    logger.critical(f"Fatal error: {e}", exc_info=True)