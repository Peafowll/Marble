from discord.ext import commands
import discord
import logging
from dotenv import load_dotenv
import requests
import os
import json
import aiohttp
import asyncio
logger = logging.getLogger('discord.ranked')

load_dotenv()
riot_token = os.getenv("RIOT_KEY")


class RiotAPIClient:
    """
    Riot API manager.
    """
    def __init__(self, token):
        self.token = token
        self.headers = {"X-Riot-Token": self.token}
        self.puuid_cache = {}
        self.semaphore = asyncio.Semaphore(5)

    async def request(self, url):
        """Generic async request wrapper with Rate Limit handling."""
        async with self.semaphore:
            async with aiohttp.ClientSession() as session:
                while True:
                    async with session.get(url, headers=self.headers) as response:
                        if response.status == 429:
                            retry_after = int(response.headers.get("Retry-After", 1))
                            logger.warning(f"Rate limited. Sleeping {retry_after}s.")
                            await asyncio.sleep(retry_after)
                            continue

                        if response.status != 200:
                            logger.error(f"API Error {response.status}: {url}")
                            return None
                        
                        return await response.json()

    async def get_puuid(self, name, tag):
        cache_key = f"{name.lower()}#{tag.lower()}"
        if cache_key in self.puuid_cache:
            return self.puuid_cache[cache_key]

        url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}"
        data = await self.request(url)
        
        if data:
            self.puuid_cache[cache_key] = data.get("puuid")
            return data.get("puuid")
        return None

    async def get_ranked_data(self, puuid, region="eun1"):
        url = f"https://{region}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
        return await self.request(url)

    async def get_match_history(self, puuid, count, region="europe", queue=420):
        url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count={count}&queue={queue}"
        return await self.request(url)

    async def get_match_details(self, match_id, region="europe"):
        url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        return await self.request(url)
    

# def build_ranked_embed(main_summoner_name, main_tag):
#     embed = discord.Embed(
#         title=f"🏆 Ranked Stats Report",
#         color=discord.Color.gold()
#     )

#     with open('data/players.json', 'r') as f:
#         players_data = json.load(f)

#     for player in players_data:
#         summoner_name = players_data[player]['riot_name']
#         tag = players_data[player]['riot_tag']
#         puuid = get_puuid(summoner_name, tag)
#         ranked_data = get_ranked_data(puuid)
#         parsed_data = parse_ranked_data(ranked_data, gamemode="RANKED_SOLO_5x5")

#         if isinstance(parsed_data, str):
#             embed.add_field(name=summoner_name, value=parsed_data, inline=False)
#         else:
#             field_value = (f"Tier: {parsed_data['tier']} {parsed_data['rank']} ({parsed_data['lp']} LP)\n"
#                            f"Wins: {parsed_data['wins']}, Losses: {parsed_data['losses']}\n"
#                            f"Winrate: {int(parsed_data['winrate'])}%")
#             embed.add_field(name=summoner_name, value=field_value, inline=False)


class Ranked(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_client = RiotAPIClient(os.getenv("RIOT_KEY"))
        logger.info("Ranked cog initialized")

    def parse_ranked_data(self, data, gamemode = None):
        """Parse ranked data into a readable format."""
        if not data:
            return "No ranked data found."
        
        results = {}
        for entry in data:
            current_results = {}
            current_results["queue_type"] = entry.get("queueType", "Unknown Queue")
            current_results["tier"] = entry.get("tier", "Unranked")
            current_results["rank"] = entry.get("rank", "")
            current_results["lp"] = entry.get("leaguePoints", 0)
            current_results["games"] = entry.get("wins", 0) + entry.get("losses", 0)
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

    async def get_performance_stats(self, puuid, count=25):
        match_ids = await self.api_client.get_match_history(puuid, count)
        if not match_ids: return None

        tasks = [self.api_client.get_match_details(mid) for mid in match_ids]
        matches_data = await asyncio.gather(*tasks)

        kills, deaths, assists, kda_accum = 0, 0, 0, 0
        valid = 0

        for match in matches_data:
            if not match: continue
            part = next((p for p in match['info']['participants'] if p['puuid'] == puuid), None)
            if part:
                k, d, a = part['kills'], part['deaths'], part['assists']
                kills += k; deaths += d; assists += a
                kda_accum += (k + a) / d if d > 0 else (k + a)
                valid += 1

        if valid == 0: return None

        return {
            "match_count" : valid,
            "avg_kills": round(kills/valid, 1),
            "avg_deaths": round(deaths/valid, 1),
            "avg_assists": round(assists/valid, 1),
            "avg_kda": round(kda_accum/valid, 2)
        }

    async def compile_ranked_data(self, summoner_name, tag):

        puuid = await self.api_client.get_puuid(summoner_name, tag)
        if not puuid:
            return None

        ranked_raw = await self.api_client.get_ranked_data(puuid)
        ranked_data = self.parse_ranked_data(ranked_raw, gamemode="RANKED_SOLO_5x5")
        if isinstance(ranked_data, str):
            return {
                "ranked_data": ranked_data,  # This passes the "No data" string to your embed
                "recent_performance": {
                    "performance_stats": None,
                    "games_analyzed": 0
                }
            }
        #print(ranked_data)
        count = 10 if ranked_data["games"]>=10 else ranked_data["games"]
        performance_stats = await self.get_performance_stats(puuid=puuid, count=count)

        return {
            "ranked_data": ranked_data,
            "recent_performance": {
                "performance_stats":performance_stats,
                "games_analyzed": count
            }
        }

    async def create_ranked_embed(self, summoner_name, tag):
        embed = discord.Embed(
            title=f"🏆 Ranked Report",
            color=discord.Color.gold()
        )

        with open('data/players.json', 'r') as f:
            players_data = json.load(f)
        for player in players_data:
            summoner_name = players_data[player]['riot_name']
            tag = players_data[player]['riot_tag']

            data = await self.compile_ranked_data(summoner_name, tag)
            if data is None:
                continue
            print(f"proccesing {summoner_name}#{tag}")
            print("data:", json.dumps(data,indent=4))
            ranked_data = data["ranked_data"]
            perf_stats = data["recent_performance"]["performance_stats"]

            if isinstance(ranked_data, str):
                embed.add_field(name=summoner_name, value=ranked_data, inline=False)
            else:
                field_value = (f"Tier: {ranked_data['tier']} {ranked_data['rank']} ({ranked_data['lp']} LP)\n"
                               f"Wins: {ranked_data['wins']}, Losses: {ranked_data['losses']}\n"
                               f"Winrate: {int(ranked_data['winrate'])}%\n")
                if perf_stats:
                    field_value += (f"Avg Kills: {perf_stats['avg_kills']}, Avg Deaths: {perf_stats['avg_deaths']}, "
                                    f"Avg Assists: {perf_stats['avg_assists']}, Avg KDA: {perf_stats['avg_kda']} "
                                    f"(over last {data['recent_performance']['games_analyzed']} games)")
                
                embed.add_field(name=summoner_name, value=field_value, inline=False)
        
        return embed

    @commands.command()
    async def test_ranked(self, ctx):
        summoner_name = "Peafowl"
        tag = "EUNE"
        await ctx.send(f"🔍 Fetching data for {summoner_name}#{tag}...")

        data = await self.compile_ranked_data(summoner_name, tag)
        if data is None:
            await ctx.send("❌ Could not retrieve data.")
            return

        await ctx.send(f"✅ Data fetched:\n```json\n{json.dumps(data, indent=4)}\n```")
        await ctx.send(embed=await self.create_ranked_embed(summoner_name, tag))

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

