from discord.ext import commands
import discord
import logging
from dotenv import load_dotenv
import requests
import os
import json
import aiohttp
import asyncio
from datetime import datetime, timezone, timedelta
logger = logging.getLogger('discord.ranked')

load_dotenv()
riot_token = os.getenv("RIOT_KEY")

# TODO : add up and down for recent lp changes
# TODO : add caching
# TODO : add last cached time

RANKED_EMOJIS = {
    "IRON": "⚫",        
    "BRONZE": "🟤",      
    "SILVER": "⚪",     
    "GOLD": "🟡",       
    "PLATINUM": "💠",    
    "EMERALD": "🟢",     
    "DIAMOND": "🔷",     
    "MASTER": "🟣",      
    "GRANDMASTER": "🔴", 
    "CHALLENGER": "👑",  
    "UNRANKED": "❔"
}

HELPER_EMOJIS = {
    "DEFEAT": "🔴",
    "VICTORY": "🔵",
    "HOT_STREAK": "🔥",
    "COLD_STREAK": "❄️"
}

def rank_to_lp(rank, tier, lp):
    """Convert rank and tier to total LP for comparison."""
    tier_values = {
        "IRON": 0,
        "BRONZE": 1,
        "SILVER": 2,
        "GOLD": 3,
        "PLATINUM": 4,
        "EMERALD": 5,
        "DIAMOND": 6,
        "MASTER": 7,
        "GRANDMASTER": 8,
        "CHALLENGER": 9
    }
    rank_values = {
        "IV": 0,
        "III": 1,
        "II": 2,
        "I": 3
    }

    if rank == "UNRANKED":
        return 0

    tier_value = tier_values.get(rank.upper(), 0)
    rank_value = rank_values.get(tier.upper(), 0)

    total_lp = (tier_value * 400) + (rank_value * 100) + lp
    return total_lp

def get_kda_emoji(kda: float) -> str:
    if kda>=5.0:
        return "✦"
    if kda>=4.0:
        return "✧"
    if kda>=3.0:
        return "◈"
    if kda>=2.0:
        return "◇"
    if kda>=1.0:
        return "⬩"
    return "•"

def get_rank_emoji(rank: str, division: str = None) -> str:
    """
    Returns the custom Discord emoji string for a given rank and division
    based on the provided ID list.
    
    Args:
        rank (str): The rank name (e.g., 'Gold', 'Diamond', 'Master').
        division (str/int, optional): The division (e.g., 'I', 1, 'IV', 4). 
                                      Not required for Master+.
    
    Returns:
        str: The formatted emoji string <:name:ID> or an error message if not found.
    """
    
    rank_key = rank.lower().strip()
    
    if rank_key == "platinum":
        rank_key = "plat"

    emojis = {

        "iron_i": "1463907947296985110",
        "iron_ii": "1463907948722913281",
        "iron_iii": "1463907950165758116",
        "iron_iv": "1463907951554334897",
        

        "bronze_i": "1463907913876770908",
        "bronze_ii": "1463907921858531531",
        "bronze_iii": "1463907923897090151",
        "bronze_iv": "1463907924916043776",
        

        "silver_i": "1463907959716184125",
        "silver_ii": "1463907961310154804",
        "silver_iii": "1463907962572505293",
        "silver_iv": "1463907963969212510",
        

        "gold_i": "1463907940309143674",
        "gold_ii": "1463907941425090651",
        "gold_iii": "1463907942838308906",
        "gold_iv": "1463907944386138133",
        

        "plat_i": "1463907954591010826",
        "plat_ii": "1463907955983257725",
        "plat_iii": "1463907957333950710",
        "plat_iv": "1463907958604959920",
        

        "emerald_i": "1463907932700803134",
        "emerald_ii": "1463907935557259284",
        "emerald_iii": "1463907937868185804",
        "emerald_iv": "1463907938988064818",
        

        "diamond_i": "1463907927424241695",
        "diamond_ii": "1463907928904962253",
        "diamond_iii": "1463907930125373460",
        "diamond_iv": "1463907931488784475",
        

        "master": "1463907953051439199",
        "grandmaster": "1463907946210529291",
        "challenger": "1463907925956366387"
    }

    apex_tiers = ["master", "grandmaster", "challenger"]
    
    if rank_key in apex_tiers:
        final_key = rank_key
    else:
        div_map = {
            "1": "_i", "i": "_i",
            "2": "_ii", "ii": "_ii",
            "3": "_iii", "iii": "_iii",
            "4": "_iv", "iv": "_iv"
        }
        
        div_str = str(division).lower().strip() if division else ""
        suffix = div_map.get(div_str)
        
        if not suffix:
            return "Invalid division provided."
            
        final_key = f"{rank_key}{suffix}"

    if final_key in emojis:
        emoji_id = emojis[final_key]
        return f"<:{final_key}:{emoji_id}>"
    else:
        return "Rank not found."

def check_streak(recent_matches):
    """Check for hot or cold streaks in recent matches."""
    if len(recent_matches) < 3:
        return None

    last_results = recent_matches[:3]
    if all(result == "w" for result in last_results):
        return "hotstreak"
    elif all(result == "l" for result in last_results):
        return "coldstreak"
    return None


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

    async def get_emoji_for_rank(self, rank):
        """Get the emoji corresponding to a given rank."""
        app_emojis = await self.fetch_application_emojis()
        target_emoji = discord.utils.get(app_emojis, name=rank)

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

class Ranked(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_client = RiotAPIClient(os.getenv("RIOT_KEY"))
        self.report_cache = {
            "data": None,
            "timestamp": discord.utils.utcnow() - timedelta(minutes=10)
        }
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

        kills, deaths, assists = 0, 0, 0
        valid = 0
        recent_matches = []
        for match in matches_data:
            if not match: continue
            participant = next((p for p in match['info']['participants'] if p['puuid'] == puuid), None)
            if participant:
                k, d, a = participant['kills'], participant['deaths'], participant['assists']
                kills += k; deaths += d; assists += a
                recent_matches.append("w") if participant['win'] else recent_matches.append("l")
                valid += 1

        if valid == 0: return None
        kda = (kills + assists) / deaths if deaths > 0 else (kills + assists)
        return {
            "match_count" : valid,
            "avg_kills": round(kills/valid, 1),
            "avg_deaths": round(deaths/valid, 1),
            "avg_assists": round(assists/valid, 1),
            "avg_kda": round(kda,1),
            "recent_matches": recent_matches
        }

    async def compile_ranked_data(self, summoner_name, tag):

        puuid = await self.api_client.get_puuid(summoner_name, tag)
        if not puuid:
            return None

        ranked_raw = await self.api_client.get_ranked_data(puuid)
        ranked_data = self.parse_ranked_data(ranked_raw, gamemode="RANKED_SOLO_5x5")
        if isinstance(ranked_data, str):
            return {
                "ranked_data": ranked_data, 
                "recent_performance": {
                    "performance_stats": None,
                    "games_analyzed": 0
                }
            }
        count = 5 if ranked_data["games"]>=5 else ranked_data["games"]
        performance_stats = await self.get_performance_stats(puuid=puuid, count=count)

        return {
            "ranked_data": ranked_data,
            "recent_performance": {
                "performance_stats":performance_stats,
                "games_analyzed": count
            }
        }

    async def create_ranked_embed(self, author_summoner_name, author_tag):
        print("creating ranked embed")
        embed = discord.Embed(
            title=f"🏆 Ranked Report",
            color=discord.Color.gold()
        )

        with open('data/players.json', 'r') as f:
            players_data = json.load(f)

        report_players_data = []


        if (discord.utils.utcnow() - self.report_cache["timestamp"]).total_seconds() < 300:
            logger.info("Using cached ranked report data")
            report_players_data = self.report_cache["data"]
        else:
            for player in players_data:
                summoner_name = players_data[player]['riot_name']
                tag = players_data[player]['riot_tag']

                data = await self.compile_ranked_data(summoner_name, tag)
                if data is None:
                    continue

                #print(f"proccesing {summoner_name}#{tag}")
                #print("data:", json.dumps(data,indent=4))

                ranked_data = data["ranked_data"]
                performance_stats = data["recent_performance"]["performance_stats"]
                games_analyzed = data["recent_performance"]["games_analyzed"]
                if isinstance(ranked_data, str):
                    continue
                
                total_lp = rank_to_lp(
                    ranked_data['tier'],
                    ranked_data['rank'],
                    ranked_data['lp']
                )
                current_player_data = {
                    "discord_id": player,
                    "riot_name": summoner_name,
                    "riot_tag": tag,
                    "ranked_data": ranked_data,
                    "performance_stats": performance_stats,
                    "games_analyzed": games_analyzed,
                    "total_lp": total_lp
                }

                report_players_data.append(current_player_data)

                self.report_cache["data"] = report_players_data
                self.report_cache["timestamp"] = discord.utils.utcnow()


                
        report_players_data.sort(key=lambda x: x['total_lp'], reverse=True)
        for player in report_players_data:
            ranked_data = player["ranked_data"]
            performance_stats = player["performance_stats"]

            rank_emoji = get_rank_emoji(ranked_data['tier'], ranked_data['rank'])
            
            if ranked_data['tier'] == "UNRANKED":
                rank_str = "Unranked"
            else:
                rank_str = f"*{ranked_data['lp']} LP*"

            field_value = f"{rank_emoji} {rank_str}\n"
            winrate = ranked_data['winrate']
            field_value += f"**{int(winrate)}% WR** ({ranked_data["wins"]}W / {ranked_data["losses"]}L)\n"

            if performance_stats:
                avg_kills = performance_stats.get("avg_kills", 0)
                avg_deaths = performance_stats.get("avg_deaths", 0)
                avg_assists = performance_stats.get("avg_assists", 0)
                avg_kda = performance_stats.get("avg_kda", 0)
                
                kda_emoji = get_kda_emoji(avg_kda)
                field_value += f" {kda_emoji}  **{performance_stats["avg_kda"]}** Recent KDA ({int(avg_kills)}/{int(avg_deaths)}/{int(avg_assists)})\n"
            else:
                field_value += "No recent performance data available.\n"

            win_emoji = HELPER_EMOJIS["VICTORY"]
            loss_emoji = HELPER_EMOJIS["DEFEAT"]
            hot_streak_emoji = HELPER_EMOJIS["HOT_STREAK"]
            cold_streak_emoji = HELPER_EMOJIS["COLD_STREAK"]
            recent_match_emojis = ""

            if performance_stats and performance_stats["recent_matches"]:
                for result in player["performance_stats"]["recent_matches"]:
                    if len(recent_match_emojis)>5:
                        continue
                    else:
                        if result == "w":
                            recent_match_emojis += win_emoji
                        else:
                            recent_match_emojis += loss_emoji
            streak = check_streak(player["performance_stats"]["recent_matches"])
            if streak == "hotstreak":
                recent_match_emojis += hot_streak_emoji
            elif streak == "coldstreak":
                recent_match_emojis += cold_streak_emoji

            
            field_value += f"Past 5 Matches : {recent_match_emojis}\n"
            print(f"checking {author_summoner_name} against r={player['riot_name']}")
            if author_summoner_name == player["riot_name"]:
                name = f"**➡ __{player['riot_name']}__**"
            else:
                name = f"{player['riot_name']}"

            embed.add_field(
                name=name,
                value=field_value,
                inline=False
            )
        
        cache_unix = int(self.report_cache["timestamp"].timestamp())    
        embed.description=f"Last updated: <t:{cache_unix}:R>"
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

        await ctx.send(embed=await self.create_ranked_embed(summoner_name, tag))

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.default)
    async def ranked_report(self, ctx):
        await ctx.send(f"🔍 Generating ranked report...")
        discord_name = str(ctx.author)

        print("called by:", discord_name)

        with open('data/players.json', 'r') as f:
            players_data = json.load(f)

        if discord_name not in players_data:
            await ctx.send("❌ Your Discord name is not linked to a Riot account.")
            return
        
        summoner_name = players_data[discord_name]['riot_name']
        tag = players_data[discord_name]['riot_tag']

        print(f"{discord_name} is linked to {summoner_name}#{tag}")

        await ctx.send(embed=await self.create_ranked_embed(summoner_name, tag))

    @ranked_report.error
    async def ranked_report_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ This command is on a global cooldown. Try again in {error.retry_after:.1f}s.")
        else:
            raise error

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

