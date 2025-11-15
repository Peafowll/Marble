import discord
from discord.ext import commands
from discord.ui import Button, View
import random
import json
import asyncio
import time, datetime
import logging
from dotenv import load_dotenv
import os
import requests
from match_score_calculator import calculate_int_scores
from helpers import convert_queue_type_to_id, convert_queue_aliases_to_queue
load_dotenv()
riot_token = os.getenv("RIOT_KEY")

# TODO : reformat the !mass_register command by hand and by using a register function called my both !register and !mass_register

# TODO : make the command work for soloqueue and randoms, or make a new one

# TODO : polish polish polish


def get_matches_by_player_id(riot_id, queue_name=None, count=20):
    """
    Gets a list of match IDs based on a player's ID.
    Args:
        riot_id: player's PUUID
        queue_name: the name of a specific queue type. (optional)
        count: number of match IDs to return (default: 20, max: 100)
    Returns:
        data
    """
    #POSSIBLE QUEUE TYPES:
        #"Ranked Solo/Duo"
        #"Ranked Flex"
        #"Normal Draft"
        #"Normal Blind"
        #"Normal (Quickplay)"
        #"ARAM"
        #"Clash"
        #"ARAM Clash"
        #"ARURF"
        #"URF"
        #"One for All"
        #"Nexus Blitz"
        #"Ultimate Spellbook"
        #"Arena"
        #"Co-op vs AI Intro"
        #"Co-op vs AI Beginner"
        #"Co-op vs AI Intermediate"
        #"TFT Normal"
        #"TFT Ranked"
        #"Swarm"
    params = {"api_key" : riot_token, "count" : count}
    if queue_name:
        queue_id = convert_queue_type_to_id(queue_name)
        if queue_id:
            params["queue"] = queue_id
    response = requests.get(f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{riot_id}/ids",params=params)
    data = response.json()
    return data

def get_match_stats_by_id(match_id):
    """
    Returns a dict of match data based on a match ID.
    """
    response = requests.get(f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}", params={"api_key": riot_token})
    data = response.json()
    return data 

def get_loses_data_list(riot_id, count = 5, queue_name = None):
    """
    Returns a list of full match data dicts for a player's recent loses.
    
    Args:
        riot_id: Player's PUUID
        count: Number of losses to retrieve (default: 5)
        queue_id: Queue type filter (optional)
    
    Returns:
        List of match data dictionaries
    """
    loses = 0
    loses_list = []
    while loses < count:
        matches_ids = get_matches_by_player_id(riot_id=riot_id,queue_name=queue_name,count=count)
        for match_id in matches_ids:
            if loses>=count:
                break
            match_data = get_match_stats_by_id(match_id=match_id)
            player_data = next((p for p in match_data["info"]["participants"] if p["puuid"] == riot_id), None)
            if not player_data["win"]:
                loses+=1
                loses_list.append(match_data)
    return loses_list
            
def get_match_int_scores_list(match_data_list, player_pool):
    """
    Returns a list of dicts containing int scores for players across multiple matches.

    Args:
        match_data_list: List of match data dictionaries
        player_pool: List of player names to calculate INT scores for

    Returns:
        list: List of dicts, where each dict contains INT scores for that match.
              Only includes players from player_pool.
        
        Example: 
        >>> get_match_int_scores_list(matches, ["PlayerA", "PlayerB"])
        [{"PlayerA": 890, "PlayerB": 426}, {"PlayerA": 752, "PlayerB": 381}]
    """
    match_scores_list = []

    for match_data in match_data_list:
        int_scores = calculate_int_scores(match_data)
        filtered_scores = {player: score for player, score in int_scores.items() 
                          if player in player_pool}
        if filtered_scores:
            match_scores_list.append(filtered_scores) 
    
    return match_scores_list
    
def get_player_pool():
    """
    Gets the pool of players registered with the !register commands, from the players.json file.
    Returns:
        A dict of players, of type `discord_name = {"riot_name": riot_name,"riot_tag": "EUNE","riot_id": id}`
    """
    with open("players.json", "r" ,encoding="utf8") as file:
        players = json.load(file)
    
    return players

def get_player_pool_names():
    """
    Gets the riot names of all players in the pool.
    Returns:
        List of names.
    """
    pool = get_player_pool()
    names = []
    for player in pool:
        names.append(pool[player]["riot_name"])
    return names

def find_inters(list_of_int_scores):
    """
    Looks at a set of int scores and finds the players most often inting the games.
    Args:
        list_of_int_scores : a list of dicts that contain int scores.
    Returns:

    """
    if len(list_of_int_scores) == 0:
        return None, None
    worst_player_frequency = {}
    total_int_scores = {}
    game_count = {}
    for int_scores in list_of_int_scores: # Go through all the games
        biggest_score = -1
        biggest_inter = None
        for player in int_scores:
            if int_scores[player] >= biggest_score: #Find biggest int score this game
                biggest_score = int_scores[player]
                biggest_inter = player
            
            if player not in total_int_scores: #Add the average int score of the player
                total_int_scores[player] = int_scores[player]
                game_count[player] = 1
            else:
                total_int_scores[player] += int_scores[player]
                game_count[player] += 1

        if biggest_inter not in worst_player_frequency:
            worst_player_frequency[biggest_inter] = 1
        else:
            worst_player_frequency[biggest_inter] +=1

    average_int_scores = {}
    for player in total_int_scores:
        average_int_scores[player] = total_int_scores[player] / game_count[player]
    
    most_frequent_worst_player = max(worst_player_frequency, key=worst_player_frequency.get)
    highest_average_int_score_player = max(average_int_scores, key=average_int_scores.get)
        
    return most_frequent_worst_player, highest_average_int_score_player
        

def get_match_history(riot_id, queue = None):
    match_ids = get_matches_by_player_id(riot_id=riot_id, queue=queue)
    result_list =[]
    for match in match_ids:
        match_stats = get_match_stats_by_id(match_id=match)
        result = ""
        for participant in match_stats["info"]["participants"]:
            if participant["puuid"] == riot_id:
                champion_played = participant["championName"]
                kills = participant["kills"]
                deaths = participant["deaths"]
                assists = participant["assists"]
                score = f"{kills}/{deaths}/{assists}"
                result = f"{champion_played} : {score}"
                result_list.append(result)
                break
    return result_list



class Blamer(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    @commands.command(aliases=['whydidwelose'], hidden=True)
    async def blame(self,ctx,match_count:int = 5 ,queue:str = "Flex"):
        """
        See who's fault it was you lost your previous games!
        Usage: !blame [match_count] [queue]
        - match_count : how many of your most recent losses you want to look at. (default = 5, max = 100)
                        Be CAREFUL! Big requests will take ages, so limit yourself to around 10 games!
        - queue : the queue type you want to look at (ex : flex, solo/duo etc.)
        
        - Example : !blame 5 Flex
        """
        queue_correct_name = convert_queue_aliases_to_queue(queue)
        await ctx.send(f"Let's see who lost you your last {match_count} {queue_correct_name} games...")
        registered_players = get_player_pool()
        author_name = ctx.author.name
        author_riot_id = registered_players[author_name]["riot_id"]
        loss_data = get_loses_data_list(riot_id=author_riot_id,count=match_count,queue_name=queue_correct_name)
        player_pool = get_player_pool_names()
        list_of_int_scores = get_match_int_scores_list(loss_data, player_pool)

        frequent_inter, worst_average_inter = find_inters(list_of_int_scores)
        if frequent_inter != worst_average_inter:
            await ctx.send(
            f"Overall, the person who's lost you the most matches was **{frequent_inter}**, "
            f"while **{worst_average_inter}** played the worst on average during your losses.")
        else:
            await ctx.send(f"Sheesh! **{worst_average_inter}** lost you your last {match_count} games.")
    

    @commands.command(aliases=["riotsregister"])
    async def register(self,ctx,username = None):
        """
        Registers your discord account to a Riot account.
        Usage : !register [riot username]#[riot tag]

        Example : !register HideOnBush#KR
        """
        if not username:
            await ctx.send("❌ Please provide a username!")
            return
        if "#" not in username:
            await ctx.send("❌ The username provided doesn't have the correct structure. Try the structure `username#tag`!")
            return
        # Split from the right to handle spaces in riot names
        playername, tag = username.rsplit("#", 1)
        response = requests.get(f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{playername}/{tag}",
                                params={"api_key": riot_token})
        data = response.json()
        author_name = ctx.author.name
        player_dict = {}
        player_dict = {
            "riot_name" : data["gameName"],
            "riot_tag" : data["tagLine"],
            "riot_id" : data["puuid"]
        }

        with open("players.json", "r", encoding="utf8") as file:
            players_dict = json.load(file)

        if author_name in players_dict.keys():
            await ctx.send(f"{ctx.author.mention}, you have already registered an account.")
            return
        for player_data in players_dict.items():
            if player_data.get("riot_id") == player_dict["riot_id"]:
                await ctx.send(f"{ctx.author.mention}, this Riot account is already registered to another user.")
                return

        players_dict[author_name] = players_dict
        with open("players.json","w",encoding="utf8") as file:
            json.dump(players_dict,file,indent=4)
        await ctx.send(f"{ctx.author.mention}, we have linked you to account **{playername}**#{tag}.")

    @commands.command(aliases=["mass_register"])
    @commands.is_owner()
    async def massregister(self, ctx, *, users_data: str = None):
        """
        Mass register multiple users at once. Owner only.
        Usage: !massregister
            discord_name1 riotname1#tag1
            discord_name2 riotname2#tag2
            ...
        
        Example: !massregister
                JohnDoe PlayerOne#NA1
                JaneSmith PlayerTwo#EUW
        """
        if not users_data:
            await ctx.send("❌ Please provide user data in the format:\n`discord_name riotname#tag` (one per line)")
            return
        
        with open("players.json", "r", encoding="utf8") as file:
            players_dict = json.load(file)
        
        lines = users_data.strip().split('\n')
        success_count = 0
        failed = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for # to split discord name from riot username
            if "#" not in line:
                failed.append(f"❌ Invalid format (no #): `{line}`")
                continue
            
            # Split on the first space to get discord name, then parse riot username#tag
            if " " not in line:
                failed.append(f"❌ Invalid format (no space): `{line}`")
                continue
            
            discord_name, riot_username = line.split(" ", 1)
            discord_name = discord_name.strip()
            riot_username = riot_username.strip()
            
            # Split riot username on the last # to get name and tag
            playername, tag = riot_username.rsplit("#", 1)
            playername = playername.strip()
            tag = tag.strip()
            
            if discord_name in players_dict:
                failed.append(f"⚠️ {discord_name}: Already registered")
                continue
            
            try:
                response = requests.get(
                    f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{playername}/{tag}",
                    params={"api_key": riot_token}
                )
                
                if response.status_code != 200:
                    failed.append(f"❌ {discord_name}: Riot account not found")
                    continue
                
                data = response.json()
                
                riot_id = data["puuid"]
                already_registered = False
                for existing_player in players_dict.values():
                    if existing_player.get("riot_id") == riot_id:
                        failed.append(f"❌ {discord_name}: Riot account already registered")
                        already_registered = True
                        break
                
                if already_registered:
                    continue
                
                players_dict[discord_name] = {
                    "riot_name": data["gameName"],
                    "riot_tag": data["tagLine"],
                    "riot_id": riot_id
                }
                success_count += 1
                
            except Exception as e:
                failed.append(f"❌ {discord_name}: Error - {str(e)}")
        
        if success_count > 0:
            with open("players.json", "w", encoding="utf8") as file:
                json.dump(players_dict, file, indent=4)
        
        result_msg = f"**Mass Registration Complete**\n✅ Successfully registered: {success_count}\n"
        if failed:
            result_msg += f"❌ Failed: {len(failed)}\n\n" + "\n".join(failed[:10])
            if len(failed) > 10:
                result_msg += f"\n... and {len(failed) - 10} more"
        
        await ctx.send(result_msg)


async def setup(bot):
    try:
        await bot.add_cog(Blamer(bot))
    except Exception as e:
        raise e