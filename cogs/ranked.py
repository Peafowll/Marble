from discord.ext import commands
import discord
import logging
from dotenv import load_dotenv
import requests
import os
logger = logging.getLogger('discord.ranked')

load_dotenv()
riot_token = os.getenv("RIOT_KEY")

def get_puuid(summoner_name, tag):
    """Fetch the PUUID for a given summoner."""
    url = f"https://europe.api.riotgames.com/lol/summoner/v4/summoners/by-name/{summoner_name}"
    headers = {"X-Riot-Token": riot_token}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json().get("puuid")

def get_ranked_data(puuid, region="EUN1"):
    """Fetch ranked data for a given PUUID."""
    url = f"https://{region}.api.riotgames.com/lol/league/v4/entries/by-summoner/{puuid}"
    headers = {"X-Riot-Token": riot_token}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()



class Ranked(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("Ranked cog initialized")

    @commands.command()
    async def test_ranked(self, ctx):
        summoner_name = "Peafowl"
        tag = "EUNE" 
        puuid = get_puuid(summoner_name, tag)
        ranked_data = get_ranked_data(puuid)
        await ctx.send(ranked_data)

    @commands.Cog.listener()
    async def on_ready(self):
        """Event listener example"""
        logger.info("Ranked cog is ready")

# ============================================================================
# Setup Function
# ============================================================================

async def setup(bot):
    try:
        await bot.add_cog(Ranked(bot))
        logger.info("Ranked cog loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load Ranked cog: {e}")
        raise

