from discord.ext import commands
import discord
import logging
from dotenv import load_dotenv
import requests
import os
import json
logger = logging.getLogger('discord.ranked')

load_dotenv()
riot_token = os.getenv("RIOT_KEY")

def get_puuid(name, tag):
    """Fetch the PUUID for a given summoner."""
    url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}"
    headers = {"X-Riot-Token": riot_token}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json().get("puuid")

def get_ranked_data(puuid, region="EUN1"):
    """Fetch ranked data for a given PUUID."""
    url = f"https://eun1.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
    headers = {"X-Riot-Token": riot_token}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def parse_ranked_data(data, gamemode = None):
    """Parse ranked data into a readable format."""
    if not data:
        return "No ranked data found."
    
    results = {}
    print(json.dumps(data, indent=4))
    for entry in data:
        current_results = {}
        current_results["queue_type"] = entry.get("queueType", "Unknown Queue")
        current_results["tier"] = entry.get("tier", "Unranked")
        current_results["rank"] = entry.get("rank", "")
        current_results["lp"] = entry.get("leaguePoints", 0)
        wins = entry.get("wins", 0)
        losses = entry.get("losses", 0)
        current_results["wins"] = wins
        current_results["losses"] = losses
        winrate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0
        current_results["winrate"] = round(winrate, 2)
        results[entry.get("queueType", "Unknown Queue")] = current_results
    
    if gamemode:
        return results.get(gamemode, "No data for specified gamemode.")
    return (results)



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
        await ctx.send(parse_ranked_data(ranked_data, gamemode="RANKED_SOLO_5x5"))

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

