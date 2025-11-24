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

class Player():
    def __init__(self, hv_puuid : str = "placeholder-id", name : str = "placeholder-name"):
        self.name = name
        self.hv_puuid = hv_puuid

    def get_stats(self, player_data : dict, kill_data, round_data, meta_data):
        self.agent = player_data["agent"]["name"]
        self.base_stats = player_data["stats"] #"score", "kills", "deats", "assists", "headshots", "bodyshots", "legshots", "damage" : {"dealt", "received"}
        self.ability_casts = player_data["ability_casts"] # "grenade", "ability1", "ability2", "ultimate"
        self.title_stats = {}

        self.title_stats["hs_percentage"] = round(self.base_stats["headshots"]/self.base_stats["bodyshots"]*100)
        self.title_stats["deaths"] = self.base_stats["deaths"]
        self.title_stats["damage"] = self.base_stats["damage"]


    def __str__(self):
        return f"{self.name}, id = {self.hv_puuid}"
    
    def title_stats_str(self):
        return str(self.title_stats)
    

class Match():
    def __init__(self, match_json, main_player_id):

        #Parses data from the match_json
        match_data = match_json # DICT
        self.player_data = match_data["players"] # LIST 
        self.team_data = match_data["teams"] # LIST
        self.meta_data = match_data["metadata"] # DICT
        self.round_data = match_data["rounds"] # LIST
        self.kill_data = match_data["kills"] # LIST

        #Finds the team that the main player was in
        self.main_team_id = "none"
        found_player = False

        for player in self.player_data:
            if player["puuid"] == main_player_id:
                self.main_team_id = player["team_id"]
                found_player=True
                break

        if found_player == False:
            return None


        self.main_players_data = [player for player in self.player_data if player["team_id"] == self.main_team_id]     

        self.main_players_names = [player_data["name"] for player_data in self.main_players_data]

        self.main_players = []
        for player_data_dict in self.main_players_data:
            player_object = Player(name=player_data_dict["name"], hv_puuid=player_data_dict["puuid"])
            player_object.get_stats(player_data=player_data_dict, kill_data=self.kill_data, round_data=self.round_data, meta_data=self.meta_data)
            self.main_players.append(player_object)


    def str_main_players(self):
        message = ""
        for player in self.main_players:
            message += str(player)
            message += "\n"
        return message

        
def get_last_match(puuid, match_type = None):
    url = f"https://api.henrikdev.xyz/valorant/v4/by-puuid/matches/eu/pc/{puuid}"
    if match_type:
        url+=f"?mode={match_type}"
    response = requests.get(url, headers=STANDARD_HEADERS)
    data = response.json()
    return data["data"][0]

def get_match_stats(match_id):

    url = f"https://api.henrikdev.xyz/valorant/v4/match/eu/{match_id}"

    response = requests.get(url, headers=STANDARD_HEADERS)
    data = response.json()
    return data

def get_last_premier_match_stats():
    for player in DAG_MEMBERS:
        puuid = DAG_MEMBERS[player]["hv_id"]
        match_stats = get_last_match(puuid=puuid, match_type="premier")
        return match_stats
    return None

def create_match_object_from_last_premier(match_data, main_player_id) -> Match: #TODO : make it so i only need player id
    match = Match(match_json=match_data, main_player_id=main_player_id)
    return match


class Titles(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):   
        logger.log("Activity cog loaded!")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def last_match_test(self,ctx):
        match_data = get_last_premier_match_stats()
        match = create_match_object_from_last_premier(match_data=match_data, main_player_id='64792ac3-0873-55f5-9348-725082445eef')
        #print(match.main_players)
        for player in match.main_players:
            print(player.title_stats_str())

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
