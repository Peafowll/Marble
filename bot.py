import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio
import logging
import json
from datetime import datetime

# TODO : rewrite changelog command and file by hand

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
        
        # Extract the latest version number
        for line in changelog_content.split('\n'):
            if line.startswith('## [') and 'Unreleased' not in line:
                # Extract version from line like "## [1.0.0] - 2025-11-16"
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

@bot.command()
@commands.is_owner()
async def exportleaderboard(ctx):
    """Export the current leaderboard JSON (owner only)"""
    try:
        with open("data/loltriviaLeaderboards.json", "r", encoding="utf8") as file:
            await ctx.send(file=discord.File(file, "loltriviaLeaderboards.json"))
    except FileNotFoundError:
        await ctx.send("No leaderboard file found!")

@bot.command()
@commands.is_owner()
async def importleaderboard(ctx):
    """Import a leaderboard JSON file to replace the current one (owner only)
    
    Usage: Upload a JSON file with the command !importleaderboard
    """
    try:
        if not ctx.message.attachments:
            await ctx.send("❌ Please attach a JSON file to import.")
            return
        
        attachment = ctx.message.attachments[0]
        
        if not attachment.filename.endswith('.json'):
            await ctx.send("❌ File must be a .json file!")
            return
        
        # Download and read the file
        file_content = await attachment.read()
        data = json.loads(file_content.decode('utf-8'))
        
        # Write to leaderboard file
        with open("data/loltriviaLeaderboards.json", "w", encoding="utf8") as file:
            json.dump(data, file, indent=4)
        
        await ctx.send(f"✅ Successfully imported leaderboard from `{attachment.filename}`!")
        logger.info(f"Leaderboard imported by {ctx.author} from {attachment.filename}")
        
    except json.JSONDecodeError:
        await ctx.send("❌ Invalid JSON file!")
        logger.error("Failed to parse imported JSON file")
    except Exception as e:
        await ctx.send("❌ An error occurred while importing the leaderboard.")
        logger.error(f"Error in importleaderboard command: {e}", exc_info=True)

@bot.command(aliases=['updates', 'changes', 'whatsnew'])
async def changelog(ctx, version: str = None):
    """View the changelog for Marble bot updates!
    
    Usage: !changelog [version]
    - If no version is specified, shows the latest changes
    - Use !changelog all to see the full changelog
    """
    try:
        with open("CHANGELOG.md", "r", encoding="utf8") as file:
            changelog_content = file.read()
        
        if version and version.lower() == "all":
            if len(changelog_content) > 1900:
                with open("CHANGELOG.md", "rb") as file:
                    await ctx.send("📜 **Full Changelog:**", file=discord.File(file, "CHANGELOG.md"))
            else:
                await ctx.send(f"📜 **Full Changelog:**\n```md\n{changelog_content}\n```")
        else:
            lines = changelog_content.split('\n')
            latest_section = []
            in_section = False
            section_count = 0
            
            for line in lines:
                if line.startswith('## ['):
                    section_count += 1
                    if section_count > 2:
                        break
                    in_section = True
                
                if in_section or line.startswith('# Marble Changelog'):
                    latest_section.append(line)
            
            latest_content = '\n'.join(latest_section)
            
            embed = discord.Embed(
                title="📜 Marble Changelog",
                description=latest_content[:4000],
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            embed.set_footer(text="Use !changelog all to see full history")
            
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