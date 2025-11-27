from discord.ext import commands, tasks
import json
import requests
import datetime
import logging
import os
import copy
from dotenv import load_dotenv
from typing import List
import math
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

    def get_stats(self, player_data : dict, kill_data, round_data, meta_data, all_players_data):
        self.agent = player_data["agent"]["name"]
        self.team_id = player_data["team_id"]
        self.base_stats = player_data["stats"] #"score", "kills", "deats", "assists", "headshots", "bodyshots", "legshots", "damage" : {"dealt", "received"}
        self.ability_casts = player_data["ability_casts"] # "grenade", "ability1", "ability2", "ultimate"
        self.title_stats = {}

        self.title_stats["hs_percentage"] = round(self.base_stats["headshots"]/self.base_stats["bodyshots"]*100)
        self.title_stats["deaths"] = self.base_stats["deaths"]
        self.title_stats["damage_dealt"] = self.base_stats["damage"]["dealt"]

        self.rounds_stats = []

        self.rounds_stats =[
            player_data
            for game_round in round_data
            for player_data in game_round["stats"]
            if player_data["player"]["name"] == self.name
        ]

        self.my_kills = [
            kill
            for kill in kill_data
            if kill["killer"]["name"] == self.name
        ]
        
        self.my_assists = [
            kill
            for kill in kill_data
            if any(assistant["name"] == self.name for assistant in kill["assistants"])
        ]

        self.set_multikills()   
        self.set_unique_weapon_kills()
        self.set_targeted_kills(all_players_data)
        self.set_assists()
        self.set_ability_kills()
        self.set_kills_by_ranges()
        self.set_weapon_types_kills()
        if self.name == "Peafowl":
            self.set_kills_by_ranges()

        

        
    def __str__(self):
        return f"{self.name}, id = {self.hv_puuid}"
    
    def title_stats_str(self):
        return str(self.title_stats)
    
    def get_title_stats(self):
        return self.title_stats
    
    def get_round_stats(self):
        return self.rounds_stats
    
    def set_multikills(self):
        self.title_stats["phantom_kills"]=len([
            kill
            for kill in self.my_kills
            if kill["weapon"]["name"] == "Phantom"
        ])

        self.title_stats["triple_kills"] = len([
            round_data
            for round_data in self.rounds_stats
            if round_data["stats"]["kills"] == 3]
            )
        
        self.title_stats["double_kills"] = len([
            round_data
            for round_data in self.rounds_stats
            if round_data["stats"]["kills"] == 2]
            )
        
        self.title_stats["quadra_kills"] = len([
            round_data
            for round_data in self.rounds_stats
            if round_data["stats"]["kills"] == 4]
            )
        
        self.title_stats["aces"] = len([
            round_data
            for round_data in self.rounds_stats
            if round_data["stats"]["kills"] == 5]
            )
        
        self.title_stats["hexakills"] =len([
            round_data
            for round_data in self.rounds_stats
            if round_data["stats"]["kills"] == 6]
            )
    
    def set_unique_weapon_kills(self):
        weapons_used = set()
        for kill in self.my_kills:
            weapons_used.add(kill["weapon"]["name"])
        self.title_stats["unique_weapon_kills"] = len(weapons_used)

    def set_targeted_kills(self, all_players_data):
        targeted_kills = dict()
        for kill in self.my_kills:
            victim_name = kill["victim"]["name"]
            if not targeted_kills.get(victim_name):
                targeted_kills[victim_name] = 1
            else:
                targeted_kills[victim_name] += 1

        enemy_scores = dict()
        for player_data in all_players_data:
            if player_data["team_id"] == self.team_id:
                continue
            player_score = player_data["stats"]["score"]
            player_name = player_data["name"]
            enemy_scores[player_name] = player_score
        
        sorted_enemies = sorted(enemy_scores.items(), key = lambda x:x[1] , reverse=True)

        enemy_carry_name = sorted_enemies[0][0]
        enemy_inter_name = sorted_enemies[4][0]

        carry_kills = targeted_kills.get(enemy_carry_name)
        inter_kills = targeted_kills.get(enemy_inter_name)

        if not carry_kills:
            carry_kills = 0
        if not inter_kills:
            inter_kills = 0
        self.title_stats["enemy_top_frag_killed"] = carry_kills
        self.title_stats["enemy_bottom_frag_killed"] = inter_kills

    def set_assists(self):
        self.title_stats["assists"] = self.base_stats["assists"]

    def set_ability_kills(self):
        self.title_stats["ability_kills"]=len([
            kill
            for kill in self.my_kills
            if kill["weapon"]["type"] == "Ability"
        ])

    def set_weapon_types_kills(self):
        pistols = ["Classic", "Frenzy", "Sheriff", "Ghost"]
        smgs = ["Stinger", "Spectre"]
        shotguns = ["Shorty", "Judge", "Bucky"]
        snipers = ["Marshall", "Outlaw", "Operator"]
        lmgs = ["Ares", "Odin"]
        rifles = ["Bulldog", "Phantom", "Vandal","Guardian"]
        knives = ["Knife", "Melee"]
        pistol_kills = []
        smg_kills = []
        lmg_kills = []
        shotgun_kills = []
        sniper_kills = []
        rifle_kills = []
        knife_kills = []


        for kill in self.my_kills:
            if kill["weapon"]["name"] in pistols:
                pistol_kills.append(kill)
            elif kill["weapon"]["name"] in smgs:
                smg_kills.append(kill)
            elif kill["weapon"]["name"] in shotguns:
                shotgun_kills.append(kill)
            elif kill["weapon"]["name"] in snipers:
                sniper_kills.append(kill)
            elif kill["weapon"]["name"] in lmgs:
                lmg_kills.append(kill)    
            elif kill["weapon"]["name"] in rifles:
                rifle_kills.append(kill)
            elif kill["weapon"]["name"] in knives:
                knife_kills.append(kill)

        self.title_stats["pistol_kills"] = len(pistol_kills)
        self.title_stats["smg_kills"] = len(smg_kills)
        self.title_stats["lmg_kills"] = len(lmg_kills)
        self.title_stats["shotgun_kills"] = len(shotgun_kills)
        self.title_stats["sniper_kills"] = len(sniper_kills)
        self.title_stats["rifle_kills"] = len(rifle_kills)
        self.title_stats["knife_kills"] = len(knife_kills)
    
    def set_kills_by_ranges(self):

        kill_distances =[]

        for kill in self.my_kills:
            killer_name = self.name
            victim_name = kill["victim"]["name"]
            victim_x = kill["location"]["x"]
            victim_y = kill["location"]["y"]
            for player_data in kill["player_locations"]:
                if player_data["player"]["name"] == killer_name:
                    killer_x = player_data["location"]["x"]
                    killer_y = player_data["location"]["y"]
                    distance = math.sqrt((killer_x - victim_x)**2 + (killer_y - victim_y)**2)
                    distance_in_meters = round(distance/100,1)
                    kill_distances.append(distance_in_meters)

        short_range_kills = [distance for distance in kill_distances if distance<=7.5]
        long_range_kills = [distance for distance in kill_distances if distance>=34]

        self.title_stats["short_range_kills"] = len(short_range_kills)
        self.title_stats["long_range_kills"] = len(long_range_kills)

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

        self.main_players : List[Player] = []
        for player_data_dict in self.main_players_data:
            player_object = Player(name=player_data_dict["name"], hv_puuid=player_data_dict["puuid"])
            player_object.get_stats(player_data=player_data_dict, 
                                    kill_data=self.kill_data, 
                                    round_data=self.round_data, 
                                    meta_data=self.meta_data,
                                    all_players_data=self.player_data)
            self.main_players.append(player_object)

        self.get_zs()

    def str_main_players(self):
        message = ""
        for player in self.main_players:
            message += str(player)
            message += "\n"
        return message
    
    def get_titles_from_tiers(self):
        pass
    def get_zs(self):

        with open("titlesFakeComplete.json", "r") as file:    
            titles_dict = json.load(file)

        player_best_z_scores = {}

        for stat in titles_dict:
            players_score_in_this_stat = {}
            player_titles_manger = {}
            for player in self.main_players:
                players_score_in_this_stat[player.name] = player.title_stats[stat]
            all_scores = [score for score in players_score_in_this_stat.values()]
            print(f"All_scores for {stat} = {all_scores}")

            mean = sum(all_scores)/len(all_scores)
            print(f"The mean is {mean}")

            numerator = sum([(score-mean)**2 for score in all_scores])
            standard_dev = math.sqrt(numerator/(len(all_scores)-1))
            print(f"The standard dev is {standard_dev}")

            if standard_dev == 0:
                print(f"All players have the same {stat} score")
                continue

            for player in players_score_in_this_stat:
                z = (players_score_in_this_stat[player] - mean)/standard_dev
                print(f"Player {player} has a z score of {z}")

                if player not in player_best_z_scores or z > player_best_z_scores[player]['z_score']:
                    player_best_z_scores[player] = {
                        'z_score': z,
                        'title': titles_dict[stat],
                        'stat': stat
                    }
    
            for player, data in player_best_z_scores.items():
                #player_titles_manger[player] = data['title']
                print(f"{player} gets title '{data['title']}")

        
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
        # for player in match.main_players:
        #     message = f"{player.name}:\n "
        #     message += json.dumps(player.get_title_stats(), indent=4)
        #     await ctx.send(message)

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
