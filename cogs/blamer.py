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

load_dotenv()
riot_token = os.getenv("RIOT_KEY")


puuids = {
    "Peafowl":{
        "riot_name" : "Peafowl",
        "riot_tag" : "EUNE",
        "riot_id" : "KD1yrq9-dAL_jZlnS5WWbPa3k8jj0Uveh4TJf0ACu8I_kP_cNGtmqRB-9h7Qpjw0-ip4V2BLYJH6jQ"
    }
}



matches = {
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
        
        Example: !loltlb abilities 5
        """
    
    @commands.command(aliases=["riotsregister"])
    async def register(self,ctx,username = None):
        if not username:
            await ctx.send("❌ Please provide a username!")
            return
        if "#" not in username:
            await ctx.send("❌ The username provided has no tag!")
            return
        split_username = username.split("#")
        playername = split_username[0]
        tag = split_username[1]
        response = requests.get(f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{playername}/{tag}",
                                params={"api_key": riot_token})
        data = response.json()
        print(data)
        author_name = ctx.author.name
        player_dict = {}
        player_dict = {
            "riot_name" : data["gameName"],
            "riot_tag" : data["tagLine"],
            "riot_id" : data["puuid"]
        }

        with open("players.json", "r", encoding="utf8") as file:
            players_dict = json.load(file)

        if author_name not in players_dict.keys():
            players_dict[author_name] = player_dict

            with open("players.json","w",encoding="utf8") as file:
                json.dump(players_dict,file,indent=4)
            await ctx.send(f"{ctx.author.mention}, we have linked you to account **{playername}**#*{tag}*.")
        else:
            await ctx.send(f"{ctx.author.mention}, you or your account have already been registered.")


async def setup(bot):
    try:
        await bot.add_cog(Blamer(bot))
    except Exception as e:
        raise