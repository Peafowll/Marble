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

def get_recent_soloqueue_kda(puuid, count=25, region="EUN1"):
    queue = 420 # SOLOQUEUE
    url = f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count={count}&queue={queue}"
    headers = {"X-Riot-Token": riot_token}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    match_ids = response.json()

    kda_data = []
    for match_id in match_ids:
        match_url = f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}"
        match_response = requests.get(match_url, headers=headers)
        match_response.raise_for_status()
        match_data = match_response.json()

        for participant in match_data['info']['participants']:
            if participant['puuid'] == puuid:
                kills = participant['kills']
                deaths = participant['deaths']
                assists = participant['assists']
                kda_score = (kills + assists) / deaths if deaths > 0 else (kills + assists)
                kda_data.append({
                    'kills': kills,
                    'deaths': deaths,
                    'assists': assists,
                    'kda_score': kda_score
                })
                break
    return kda_data

def get_soloque_performance_data(puuid, count=25, region="EUN1"):
    kda = get_recent_soloqueue_kda(puuid, count, region)
    avg_kills = sum(match['kills'] for match in kda) / len(kda) if kda else 0
    avg_deaths = sum(match['deaths'] for match in kda) / len(kda) if kda else 0
    avg_assists = sum(match['assists'] for match in kda) / len(kda) if kda else 0
    avg_kda_score = sum(match['kda_score'] for match in kda) / len(kda) if kda else 0
    ranked_data = get_ranked_data(puuid, region)
    ranked_data_parsed = parse_ranked_data(ranked_data)
    soloqueue_data = ranked_data_parsed.get("RANKED_SOLO_5x5", {})
    data = {
        "kda_stats":{
            "average_kills": round(avg_kills, 2),
            "average_deaths": round(avg_deaths, 2),
            "average_assists": round(avg_assists, 2),
            "average_kda_score": round(avg_kda_score, 2)
        },
        "ranked_stats": soloqueue_data
    }

    return data

def build_ranked_embed(main_summoner_name, main_tag):
    embed = discord.Embed(
        title=f"🏆 Ranked Stats Report",
        color=discord.Color.gold()
    )

    with open('data/players.json', 'r') as f:
        players_data = json.load(f)

    for player in players_data:
        summoner_name = players_data[player]['riot_name']
        tag = players_data[player]['riot_tag']
        puuid = get_puuid(summoner_name, tag)
        ranked_data = get_ranked_data(puuid)
        parsed_data = parse_ranked_data(ranked_data, gamemode="RANKED_SOLO_5x5")

        if isinstance(parsed_data, str):
            embed.add_field(name=summoner_name, value=parsed_data, inline=False)
        else:
            field_value = (f"Tier: {parsed_data['tier']} {parsed_data['rank']} ({parsed_data['lp']} LP)\n"
                           f"Wins: {parsed_data['wins']}, Losses: {parsed_data['losses']}\n"
                           f"Winrate: {int(parsed_data['winrate'])}%")
            embed.add_field(name=summoner_name, value=field_value, inline=False)


class Ranked(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("Ranked cog initialized")

    @commands.command()
    async def test_ranked(self, ctx):
        summoner_name = "Peafowl"
        tag = "EUNE" 
        puuid = get_puuid(summoner_name, tag)
        await ctx.send(json.dumps(get_soloque_performance_data(puuid)))

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

