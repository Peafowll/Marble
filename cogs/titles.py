from discord.ext import commands, tasks
import json
import requests
import datetime
import logging
import os
import copy
from dotenv import load_dotenv

logger = logging.getLogger('discord.titles')

load_dotenv()
hv_token = os.getenv("HD_KEY")

DAG_MEMBERS = {
    "peafowl": {
        "riot_name": "Peafowl",
        "riot_tag": "EUNE",
        "hv_id": "64792ac3-0873-55f5-9348-725082445eef"
    },
    "yoyoo0722": {
        "riot_name": "yoyo15",
        "riot_tag": "EUNE",
        "riot_id": "zy4F2oQ6IXGNMCOJKlUj7gN_ML4tW43zMxECvtD6m2EJCs1JX_fFCiJfR8cQjgJWGp5VbgB4WsCmhg",
        "hv_id": "7f15608b-dd61-564f-9e1a-94a4936b08f9"
    },
    "vladimus2005": {
        "riot_name": "vladimus2005",
        "riot_tag": "EUNE",
        "riot_id": "E6rjy-vG9AMa_dp1HWePQBsJKPwcw36C-JDOyGWJgqw1GQM89t_u39ZPA4KNjWD965mJJrGAYiQxNQ",
        "hv_id": "c08f6c44-378c-5c82-8ce1-d12f33a0264e"
    },
    "arrow_san": {
        "riot_name": "Dani",
        "riot_tag": "EUNE1",
        "riot_id": "lP2icP8VVAMMRnOHlEnFROqdEbd205nRtwD3vOzGZQVsErNjJp5iinXUlxcaZfLJcxpCrRchqPZGow",
        "hv_id":"7ff1ac69-8901-5634-a4ea-26684d52d9e9"
    },
    "painite01":{
        "riot_name": "Painite",
        "riot_tag": "4349",
        "riot_id": "w-bK59spgQkicdzS2WgHp8edRn5MG0lhYdHtYPj5OkEa3JQ0Pow31lsFtSTM34_rGi-nLtpxRZS9-w",
        "hv_id": "1c8ee468-4a77-5f18-b2c3-2016e0c74bba"
    }
}
STANDARD_HEADERS = {"Authorization": hv_token}

def get_last_match(puuid, match_type = None):
    url = f"https://api.henrikdev.xyz/valorant/v4/by-puuid/matches/eu/pc/{puuid}"
    response = requests.get(url, headers=STANDARD_HEADERS)
    data = response.json()
    matches_checked = 0
    if match_type:
        for match in data["data"]:
            if match["metadata"]["mode"] == match_type:
                match_id = match["metadata"]["match_id"]
                return match_id
            matches_checked+=1
            if matches_checked == 10:
                return None
    else:
        match_id = data["data"][0]["metadata"]["match_id"]
        return match_id
    return None

def get_match_stats(match_id):

    url = f"https://api.henrikdev.xyz/valorant/v4/match/eu/{match_id}"

    response = requests.get(url, headers=STANDARD_HEADERS)
    data = response.json()
    return data

def get_last_premier_match_stats():
    for player in DAG_MEMBERS:
        puuid = DAG_MEMBERS[player]["hv_id"]
        match_id = get_last_match(puuid=puuid, match_type="Premier")
        if match_id:
            return get_match_stats(match_id=match_id)
    return None

class Titles(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):   
        logger.log("Activity cog loaded!")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def tester(self,ctx):
        with open("testValoMatch.json", "w", encoding="utf8") as file:
            match_id = get_last_match("64792ac3-0873-55f5-9348-725082445eef")
            match_data = get_match_stats(match_id)
            json.dump(match_data, file, indent=4)

async def setup(bot):
    """
    Set up the Titles cog.
    
    Parameters
    ----------
    bot : commands.Bot
        The Discord bot instance.
    """
    try:
        await bot.add_cog(Titles(bot))
    except Exception as e:
        raise e
