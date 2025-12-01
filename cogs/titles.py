from discord.ext import commands, tasks
import discord
import json
import requests
import datetime
import logging
import os
import copy
from dotenv import load_dotenv
from typing import List
import math
import random
from pprint import pprint

logger = logging.getLogger('discord.titles')

#TODO : CALL FOR @DAG ROLE (IMPLEMENTED BUT INTESTED)
#TODO : CONFIG
#TODO : ADD TANGERINE AND LEMON
#TODO : ADD AUTO-MESSAGE FOR PREMIER

load_dotenv()
hv_token = os.getenv("HD_KEY")
MARBLE_CHANNEL_ID = 1353156986547736758
DAG_ROLE_ID = 1443876656111685652
YKTP_GUILD_ID = 890252683657764894
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

DAG_EMOJIS ={
    "Painite" : "💎",
    "Peafowl" : "🦚",
    "vladimus2005" : "🪩",
    "Dani" : "🎯",
    "yoyo15" : "🤙"
}
STANDARD_HEADERS = {"Authorization": hv_token}


def get_emoji_from_player_name(player_name : str):
    return DAG_EMOJIS.get(player_name, "👤")

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
        self.set_plants(round_data=round_data)
        self.set_defuses(round_data=round_data)
        self.set_bloods(kills_data=kill_data)
        self.set_clutches(round_data=round_data, kill_data=kill_data)
        self.set_rebound_percent()

        

        
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

    def set_plants(self,round_data):
        plants = 0
        for round_details in round_data:
            if round_details["plant"]:
                if round_details["plant"]["player"]["name"] == self.name:
                    plants+=1
        
        self.title_stats["plants"] = plants

    def set_defuses(self,round_data):
        defuses = 0
        ninja_defuses = 0
        for round_details in round_data:
            if round_details["defuse"]:
                if round_details["defuse"]["player"]["name"] == self.name:
                    defuses+=1
                    if round_details["defuse"]["player_locations"] and any([player for player in round_details["defuse"]["player_locations"] if player["player"]["team"] != self.team_id]):
                        ninja_defuses+=1
        
        self.title_stats["defuses"] = defuses
        self.title_stats["ninja_defuses"] = ninja_defuses
    
    def set_bloods(self, kills_data):
        first_bloods = 0
        last_bloods = 0
        kills_by_round = {}
        for kill in kills_data:
            round_nr = kill["round"]
            if round_nr not in kills_by_round:
                kills_by_round[round_nr] = []
            kills_by_round[round_nr].append(kill)
        
        for round_nr in sorted(kills_by_round.keys()):
            round_kills = kills_by_round[round_nr]
            if round_kills and round_kills[0]["killer"]["name"] == self.name:
                first_bloods+=1
            if round_kills and round_kills[-1]["killer"]["name"] == self.name:
                last_bloods += 1
        
        self.title_stats["first_bloods"] = first_bloods
        self.title_stats["last_bloods"] = last_bloods

        #NOTE : The last_bloods also tracks kills that were obtained after a round's winner has been declared

    def set_clutches(self,round_data, kill_data):
        one_v_one_clutches = 0
        out_numbered_clutches = 0
        for round_details in round_data: # looking at all rounds
            round_ceremony = round_details["ceremony"]
            round_kills = [kill for kill in kill_data if kill["round"] == round_details["id"]] #getting all kills from this round

            if round_kills:
                last_kill = round_kills[-1]
                clutcher_name = last_kill["killer"]["name"]
                if clutcher_name == self.name:
                    if round_ceremony== "CeremonyCloser": #1v1 clutches
                        one_v_one_clutches+=1
                    elif round_ceremony == "CeremonyClutch": #1vMany clutches
                        out_numbered_clutches+=1
            
        self.title_stats["1v1_clutches"] = one_v_one_clutches
        self.title_stats["outnumbered_clutches"] = out_numbered_clutches

    def set_rebound_percent(self):
        kills_in_second_half = [kill for kill in self.my_kills if kill["round"]>12]
        kills_in_first_half = [kill for kill in self.my_kills if kill["round"]<=12]

        kill_count_first_half = len(kills_in_first_half)
        kill_count_second_half = len(kills_in_second_half)

        if kill_count_first_half == 0:
            if kill_count_second_half > 0:
                self.title_stats["rebound_percentage"] = 999.0
            else:
                self.title_stats["rebound_percentage"] = 0.0
            return

        rebound_percentage = ((kill_count_second_half-kill_count_first_half)/kill_count_first_half)*100

        self.title_stats["rebound_percentage"] = rebound_percentage

    def set_time_alive(self, round_data):
        pass
        #This will be developed later.
    
            
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

        if not found_player:
            raise ValueError(
                f"Player with ID {main_player_id} not found in match data. "
                f"Available players: {[p['player_id'] for p in self.player_data]}"
            )


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

        self.main_players.sort(key=lambda player: player.base_stats["score"], reverse=True)
        
        self.map_name = self.meta_data["map"]["name"]
        self.date = self.meta_data["started_at"].split("T")[0]

        self.enemy_team_tag = "Opponents"
        for team in self.team_data:
            if team["team_id"] != self.main_team_id:
                if team["premier_roster"]:
                    self.enemy_team_tag = team["premier_roster"]["tag"]

        self._set_team_scores()

        self.get_titles_from_zs()

    def str_main_players(self):
        message = ""
        for player in self.main_players:
            message += str(player)
            message += "\n"
        return message
    
    def _set_team_scores(self):
        """Extract round wins for each team"""
        for team in self.team_data:
            if team["team_id"] == self.main_team_id:
                self.main_team_rounds_won = team["rounds"]["won"]
                self.main_team_rounds_lost = team["rounds"]["lost"]
            else:
                self.enemy_team_rounds_won = team["rounds"]["won"]
                self.enemy_team_rounds_lost = team["rounds"]["lost"]

    def get_enemy_team_tag(self):
        return self.enemy_team_tag
    
    def get_main_team_score(self):
        """Returns main team's round score"""
        return self.main_team_rounds_won

    def get_enemy_team_score(self):
        """Returns enemy team's round score"""
        return self.main_team_rounds_lost

    def get_match_score_string(self):
        """Returns formatted score string"""
        return f"**{self.main_team_rounds_won}** — **{self.main_team_rounds_lost}**"

    def get_map_name(self):
        """Returns map name"""
        return self.map_name

    def get_match_date(self):
        """Returns match start date."""
        return self.date

    def get_title_manager(self):
        return self.title_manager
    
    def get_titles_from_zs(self):

        with open("titles.json", "r") as file:    
            titles_dict = json.load(file)

        self.title_manager = {}
        player_z_scores = {}
        
        log_file = open("titles_attribution_log.txt", "w")#LOGGING

        for stat in titles_dict:
            if not titles_dict[stat].get("implemented", True):
                continue
            players_score_in_this_stat = {}
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
            
            weight = titles_dict[stat].get("weight", 1.0)
            is_reverse = titles_dict[stat].get("reverse", False)


            for player in players_score_in_this_stat:
                z = (players_score_in_this_stat[player] - mean)/standard_dev
                if is_reverse:
                    z = -z

                z_weighted = z * weight

                if player not in player_z_scores:
                    player_z_scores[player] = []
                player_z_scores[player].append({
                    'z_score': z_weighted,
                    'title': titles_dict[stat],
                    'stat_nr' :players_score_in_this_stat[player]})
                


        threshold = 0.3  # The max range of z-scores between titles

        assigned_titles = set()

        players_by_best_z = sorted(
        player_z_scores.items(),
        key=lambda x: max(title['z_score'] for title in x[1]),
        reverse=True
        )# sort players by their best z-score

        for player, z_score_list in players_by_best_z:
            z_score_list.sort(key=lambda x: x['z_score'], reverse=True)
            max_z = z_score_list[0]['z_score']

            close_titles = [title for title in z_score_list if max_z - title['z_score'] <= threshold]

            # Filter for minimums
            close_titles = [title for title in close_titles if title["stat_nr"] >= title["title"].get("minimum", 0)]
            
            # Filter out already-assigned titles
            close_titles = [title for title in close_titles if title["title"]["title"] not in assigned_titles]
    
            close_title_names = [title["title"]["title"] for title in close_titles]

            print(f"Title candidates for {player} are : {close_title_names}")
            
            #LOGGING
            log_file.write(f"\n{'='*80}\n")
            log_file.write(f"PLAYER: {player}\n")
            log_file.write(f"{'='*80}\n")
            log_file.write(f"{'Title':<30} {'Stat':<30} {'Z-Score':<15} {'Stat Count':<15}\n")
            log_file.write(f"{'-'*90}\n")
            
            for title_data in z_score_list:
                title_name = title_data["title"]["title"]
                stat_name = title_data["title"]["award"]
                z_score = title_data['z_score']
                stat_count = title_data["stat_nr"]
                already_used = " [TAKEN]" if title_name in assigned_titles else ""
                log_file.write(f"{title_name:<30} {stat_name:<30} {z_score:<15.4f} {stat_count:<15}{already_used}\n")

            # Handle case where all titles are taken - assign "The Heart"
            if not close_titles:
                total_rounds = self.main_team_rounds_won + self.main_team_rounds_lost
                log_file.write(f"\n>>> WARNING: No unique titles available - assigning 'The Heart'\n\n")
                
                self.title_manager[player] = {
                    "title_name": "The Heart",
                    "award_text": "Rounds spent as the cheerleader of the team",
                    "stat_count": total_rounds
                }
                continue

            if len(close_titles) > 1:
                min_z = min(title['z_score'] for title in close_titles) # for shifting weights
                weights = [title['z_score'] - min_z + 1 for title in close_titles]
                chosen_title = random.choices(close_titles, weights=weights, k=1)[0]
            else:
                chosen_title = close_titles[0]
            
            # Mark title as assigned
            assigned_titles.add(chosen_title["title"]["title"])
            
            log_file.write(f"\n>>> ASSIGNED TITLE: {chosen_title['title']['title']}\n\n")
            #LOGGING

            self.title_manager[player] = {
                "title_name" : chosen_title["title"]["title"],
                "award_text" : chosen_title["title"]["award"],
                "stat_count" : chosen_title["stat_nr"]
            }

        #LOGGING
        log_file.close()
        #LOGGING

        # for player, data in player_best_z_scores.items():
        #     #player_titles_manger[player] = data['title']
        #     print(f"{player} gets title '{data['title']}")
            

        
def get_last_match(puuid, match_type = None):
    """
    Fetch the last match for a player from Henrik API.
    
    Args:
        puuid: Player's Henrik API UUID
        match_type: Optional filter (e.g., "premier", "competitive")
    
    Returns:
        Dictionary containing match data
        
    Raises:
        requests.RequestException: Network or API errors
        ValueError: Invalid API response structure
    """
    url = f"https://api.henrikdev.xyz/valorant/v4/by-puuid/matches/eu/pc/{puuid}"
    if match_type:
        url += f"?mode={match_type}"
    
    try:
        response = requests.get(
            url, 
            headers=STANDARD_HEADERS, 
            timeout=10  # Prevent infinite hangs
        )
        response.raise_for_status()  # Raises exception for 4xx/5xx status codes
        
        data = response.json()
        
        # Validate response structure
        if "data" not in data:
            raise ValueError(f"API response missing 'data' field: {data}")
        
        if not data["data"]:
            raise ValueError(f"No matches found for player {puuid}")
        
        return data["data"][0]
        
    except requests.Timeout:
        logger.error(f"API request timed out for player {puuid}")
        raise
    except requests.HTTPError as e:
        if e.response.status_code == 429:
            logger.error("API rate limit exceeded")
        else:
            logger.error(f"API returned error {e.response.status_code}: {e}")
        raise
    except requests.RequestException as e:
        logger.error(f"Network error fetching match for {puuid}: {e}")
        raise
    except (KeyError, IndexError, ValueError) as e:
        logger.error(f"Unexpected API response structure: {e}")
        raise

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


    def get_response_from_match_score(self,our_score, enemy_score, team_name="**DAG**"):
        score_diff = our_score - enemy_score
        is_overtime = our_score >= 13 or enemy_score >= 13

        responses = []
        # Surrender
        if our_score<=13 and enemy_score<=13:
            responses = [
                f"Got them quivering, {team_name}! They were so intimidated by you, they didn't even let the match end naturally. Your awards are below.",
                f"Woah, {team_name}, way to do it to them! A forfeit means you dominated. Match report below."
                f"Sheesh, {team_name}. White flags waving, and you winning! Perfect combination! Let's see how bad you crushed 'em."
            ]
        # --- Wins ---
        if score_diff >= 7:
            # Stomp
            responses = [
                f"Incredible performance, {team_name}! You absolutely dominated out there. Let's see what you each did well.",
                f"What a statement win, {team_name}! The opposition never stood a chance. Let's see those stats.",
                f"Flawless execution, {team_name}! That's how champions play. Your awards await below."
            ]
        elif 4 <= score_diff < 7:
            # Solid Win
            responses = [
                f"Strong showing today, {team_name}! That's some great consistency. Match report incoming.",
                f"Well-earned victory, {team_name}. Ups and down, but closed it out. Check your performance below.",
                f"Professional performance, {team_name}! You played like the pros do. Let's see what you all specialized in."
            ]
        elif 1 <= score_diff < 4:
            # Close Win
            if is_overtime:
                responses = [
                    f"GREAT Overtime, {team_name}! You kept your composure when it mattered most. That's championship mentality right there.",
                    f"What resilience, {team_name}! Overtime wins are the mark of a great team. Your match report tells the story.",
                    f"Nerves of steel in overtime, {team_name}! Those are the wins that build legends. Check out your titles below."
                ]
            else:
                responses = [
                    f"Heart-pounding victory, {team_name}! You stayed focused under pressure and won. Match report below.",
                    f"Close battles forge strong teams, {team_name}. Great mental fortitude today! Now let's see those stats.",
                    f"You grinded it out and came out on top, {team_name}. That's the winning mentality! Report incoming."
                ]

        # --- Losses ---
        elif -4 < score_diff <= -1:
            # Close loss
            if is_overtime:
                responses = [
                    f"Overtime heartbreaker, {team_name}, but you fought with everything you had. Hold your heads high and check your titles.",
                    f"So close in overtime, {team_name}. That competitive fire is exactly what we need. Review your stats and come back stronger.",
                    f"Tough overtime loss, {team_name}, but you proved you can compete with anyone. The match report shows some accolades to cheer you up."
                ]
            else:
                responses = [
                    f"Narrow defeat, {team_name}, but you battled hard to the end. Check your individual performances below - we'll get the next one.",
                    f"Just a few rounds away, {team_name}. Your effort was there, now let's sharpen the execution. Match report ready.",
                    f"You competed well today, {team_name}. Let's get motivated for the next game with some accolades you've earned. Check below."
                ]
        elif -7 < score_diff <= -4:
            # Solid loss
            responses = [
                f"Tough game, {team_name}, but every setback is a setup for a comeback. Next time, you've got this.",
                f"Not our day, {team_name}, but champions learn from losses. Your performance breakdown is below.",
                f"We've got work to do, {team_name}, but the effort is there. Next game, we'll come back stronger. Titles below."
            ]
        else:
            # Stomp loss
            responses = [
                f"Rough match, {team_name}, but even the best teams have off days. Here are some titles to maybe cheer you up.",
                f"That was a tough one, {team_name}, but adversity builds character. Your match report is below - use it as fuel for the next game.",
                f"Not the result we wanted, {team_name}, but stay determined. We've still got some work to do. Stats below."
            ]
            
        return random.choice(responses)
    @commands.Cog.listener()
    async def on_ready(self):   
        logger.info("Titles cog on_ready triggered.")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def last_match_test(self,ctx):
        match_data = get_last_premier_match_stats()
        match = create_match_object_from_last_premier(match_data=match_data, main_player_id='64792ac3-0873-55f5-9348-725082445eef')
        for player in match.main_players:
            message = f"{player.name}:\n "
            message += json.dumps(player.get_title_stats(), indent=4)
            await ctx.send(message)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def force_send_premier_results(self,ctx, location = "here"):
        match_data = get_last_premier_match_stats()
        match = create_match_object_from_last_premier(match_data=match_data, main_player_id='64792ac3-0873-55f5-9348-725082445eef')
        rounds_won = match.get_main_team_score()
        rounds_lost = match.get_enemy_team_score()
        map_name = match.get_map_name()
        date = match.get_match_date()
        enemy_team_tag = match.get_enemy_team_tag()
        result = "🟢 **WIN** 🟢" if rounds_won > rounds_lost else "🔴 **LOSS** 🔴"
        score_line = f"**DAG** {rounds_won} — {rounds_lost} **{enemy_team_tag}**"

        map_image = discord.File(f"map_photos/{map_name.lower()}.jpeg",filename="map_image.jpeg")
        embed = discord.Embed(
            title="DAG Match Report",
            colour=0xf50000,
            timestamp=datetime.datetime.now(),
            description=(
                f"{result}\n"
                f"{score_line}\n\n"
                f"🗺️ **Map:** `{map_name}`\n"
                f"📅 **Date:** `{date}`"
            )
        )
        title_manager = match.get_title_manager()
        #print(title_manager)
        for player in match.main_players:
            player_name = player.name
            title_name = title_manager[player_name]["title_name"]
            award_text = title_manager[player_name]["award_text"]
            stat_count = title_manager[player_name]["stat_count"]
            kill_count = player.base_stats['kills']
            assist_count = player.base_stats['assists']
            death_count = player.base_stats['deaths']
            player_emoji = get_emoji_from_player_name(player_name=player_name)
            embed.add_field(
            name=f"{player_emoji} {player.name}  •  {player.agent}  •  **{kill_count}** / **{death_count}** / **{assist_count}**",
                value=(
                    f"\n**【 {title_name} 】**\n"
                    f"⠀*{award_text}* : **{stat_count}**"
                ),
                inline=False
            )
        embed.set_image(url="attachment://map_image.jpeg")
        guild_yktp = self.bot.get_guild(YKTP_GUILD_ID)
        if guild_yktp is None:
            guild_yktp = await self.bot.fetch_guild(YKTP_GUILD_ID)  
        role = guild_yktp.get_role(DAG_ROLE_ID)
        if role is None:
            return await ctx.send("Could not find the role in the target server.")
        role_mention = role.mention
        message = self.get_response_from_match_score(our_score=rounds_won, enemy_score=rounds_lost,team_name=role_mention) + "\n"
        if location == "server":
            channel = self.bot.get_channel(MARBLE_CHANNEL_ID)
            if channel is None:
                channel = await self.bot.fetch_channel(MARBLE_CHANNEL_ID)
            await channel.send(content=message ,file=map_image,embed=embed)
        else:
            await ctx.send(content=message ,file=map_image,embed=embed)


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
