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
from match_score_calculator import calculate_match_scores

load_dotenv()
riot_token = os.getenv("RIOT_KEY")


puuids = {
    "Peafowl":{
        "riot_name" : "Peafowl",
        "riot_tag" : "EUNE",
        "riot_id" : "KD1yrq9-dAL_jZlnS5WWbPa3k8jj0Uveh4TJf0ACu8I_kP_cNGtmqRB-9h7Qpjw0-ip4V2BLYJH6jQ"
    }
}



test_matches = {
    "Peafowl":[
    "EUN1_3857317403",
    "EUN1_3857293749",
    "EUN1_3857261941",
    "EUN1_3857196645",
    "EUN1_3853948327",
    "EUN1_3853429237",
    "EUN1_3853403499",
    "EUN1_3853376313",
    "EUN1_3848403280",
    "EUN1_3848369672",
    "EUN1_3848349183",
    "EUN1_3848320574",
    "EUN1_3848010913",
    "EUN1_3847985487",
    "EUN1_3847950008",
    "EUN1_3847914240",
    "EUN1_3847460137",
    "EUN1_3847432128",
    "EUN1_3847393981",
    "EUN1_3847364291"
    ]
}



def get_matches_by_player_id(riot_id,queue = None):
    response = requests.get(f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{riot_id}/ids",params={"api_key": riot_token})
    data = response.json()
    return data

def get_match_stats_by_id(match_id):
    response = requests.get(f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}", params={"api_key": riot_token})
    data = response.json()
    return data 

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
    # with open("test_match.json","w",encoding="utf8") as file:
    #     json.dump(match_stats,file,indent=4)
    #     print("match imported!")




class Blamer(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    @commands.command(aliases=['whydidwelose'], hidden=True)
    async def blame(self,ctx,game ="lol",match_count = 5):
        """
        See who's fault it was you lost your previous games!
        Usage: !loltlb [difficulty] [count]
        - difficulty: "ults", "abilities", "ag", or "all" (default: all)
        - count: Number of top players to display (default: 10, max: 50)
        
        Example: !
        """

        #result_list = get_match_history("KD1yrq9-dAL_jZlnS5WWbPa3k8jj0Uveh4TJf0ACu8I_kP_cNGtmqRB-9h7Qpjw0-ip4V2BLYJH6jQ")
        for i,match in enumerate(test_matches["Peafowl"]):
            match_data = get_match_stats_by_id(match)
            int_scores = calculate_match_scores(match_data,target_player="Peafowl")
            if not int_scores:  # Empty dict evaluates to False
                await ctx.send(f"Match #{i}: Target player won, skipping")
                continue

            target_participant = next((p for p in match_data["info"]["participants"] if p["riotIdGameName"] == "Peafowl"), None)
            champion_name = target_participant["championName"] if target_participant else "Unknown"

            await ctx.send(f"**In match #{i}** you played {champion_name}, with the following scores:")
            await ctx.send(int_scores)
            worst_player = max(int_scores, key=int_scores.get)
            await ctx.send(f"You lost because of {worst_player}, with score {int_scores[worst_player]}")
            await ctx.send("=========================")

    @commands.command(aliases=["riotsregister"])
    async def register(self,ctx,username = None):
        """
        Registerds your discord account to a Riot account.
        Usage : !register [riot username]#[riot tag]

        Example : !register HideOnBush#KR
        """
        if not username:
            await ctx.send("❌ Please provide a username!")
            return
        if "#" not in username:
            await ctx.send("❌ The username provided doesn't have the correct structure. Try the structure `username#tag`!")
            return
        split_username = username.split("#")
        playername = split_username[0]
        tag = split_username[1]
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


async def setup(bot):
    try:
        await bot.add_cog(Blamer(bot))
    except Exception as e:
        raise