import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio
load_dotenv()
token = os.getenv("BOT_TOKEN")
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!',intents=intents)

async def load_cogs():
    for filename in os.listdir('./cogs'):
                if filename.endswith('.py') and filename != '__init__.py':
                    await bot.load_extension(f'cogs.{filename[:-3]}')
                    print(f"Loaded {filename}")

@bot.event
async def on_ready():
    print(f"MARBLE is online!")

@bot.command()
async def hi(ctx):
    await ctx.send("HELLO!")

asyncio.run(load_cogs())
bot.run(token=token)