import discord
from discord.ext import commands
from discord.ui import Button, View
from helpers import find_lol_spells
import random
import json
import asyncio
import time, datetime
import logging
import re

logger = logging.getLogger('discord.random_teams')
alises = {
    "peafowl": ["paun","tudor","peafowl"],
    "yoyoo0722": ["yoyo","ioncii","ionci","ionchi","ionchii"],
    "vladimus2005": ["vladimus"],
    "arrow_san" : ["dani","arrow"],
    "itz_wolfseer" : ["raisa","wolfseer"],
    "frogthephrog": ["frog","phrog","matei"],
    "boria.": ["boria"],
    "tavi71" : ["tavone","tavi","octavian"],
    "tepel": ["vlad","kingmordecai","mordecai","iquitgambling","blackjewvu"],
    "el_donte" : ["cristi","tachanka","dante","criti"],
    "painte01" : ["fabi","painite"]
}


def get_current_vc_members(voice_channel):
    vc_members = voice_channel.members
    vc_member_names = [member.name for member in vc_members]
    return vc_member_names


def check_response(m, vc_member_names):
    """
    Checks a random_teams type message.
    
    Takes the commands a/d/r/t.

    If an invalid command is issued, returns None.

    If d is issued, returns ("d", None).

    If a/r/t are issued, returns (*letter*, *value*)
    """
    if m == "d":
        return ("d",None)

    split_m = m.split(" ")

    if len(split_m) < 2:
        return None
    
    command = split_m[0]
    value = split_m[1]

    if command not in ["a","r","t"]:
        return None
    
    if command == "t":
        if not value.isdigit():
            return None
        return ("t",int(value))
    
    if command == "r":
        if value not in vc_member_names:
            return None
    
    return (command, value)

def generate_teams(players : list, teams_count : int):
    """
    Takes a list of players and a number of teams and returns a list of lists representing randomly generated teams.
    """
    random.shuffle(players)
    teams = []
    for index in range(teams_count):
        team = players[index::teams_count]
        teams.append(team)

    return teams

class RandomTeams(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
    
    @commands.command(aliases=["randomteams"])
    async def random_teams(self,ctx, playercount = None, team_count = 2):
        voice_channel = ctx.author.voice.channel if ctx.author.voice else None
        channel = ctx.channel
        author_id = ctx.author.id
        if not voice_channel:
            await ctx.send("You need to be in a voice channel to use this!")
            return
                
        def check(m):
            return m.channel.id == channel.id and m.author.id == author_id

        vc_member_names = get_current_vc_members(voice_channel)
        message = "# Random Team Builder\nPlayer Pool : \n"
        for member in vc_member_names:
            message+=f"- **{member}**\n"
        
        await ctx.send(message + f"Generating **{team_count}** teams.\n")
        message = "--------------------------------------------------\n"
        message += "Send the following commands to edit the list :\n"
        message += "- **a** *name* to add a player.\n"
        message += "- **r** *name* to remove a player.\n"
        message += "- **t** *number* to set the amount of teams to generate.\n"
        message += "- **d** to generate teams."
        await ctx.send(message)
        called_command = ""
        first_pass = True
        while called_command!= "d":
            try:
                if first_pass == False:
                    message = ""
                    message += "Current Player Pool :\n"
                    for member in vc_member_names:
                        message+=f"- **{member}**\n"
                    message += f"Generating **{team_count}** teams."
                    await ctx.send(message)

                first_pass = False
                response_input = (await self.bot.wait_for('message', check=check, timeout=60.0)).content
                called_command, called_value = check_response(response_input, vc_member_names)
                if not called_command:
                    await ctx.send("Invalid command or argument.")
                elif called_command == "d":
                    break
                elif called_command == "a":
                    vc_member_names.append(called_value)
                    await ctx.send(f"Added player {called_value}.")
                elif called_command == "t":
                    team_count = called_value
                    await ctx.send(f"Set team count to {team_count} teams.")
                elif called_command == "r":
                    await ctx.send(f"Removed player {called_value}")
                    vc_member_names.remove(called_value)

            except asyncio.TimeoutError:
                await ctx.send("Response time limit reached. Operation canceled.")
                return

        random.shuffle(vc_member_names)
        teams = generate_teams(vc_member_names, team_count)

        message = ""
        for i, team in enumerate(teams):
            message+=f"## Team {i+1}\n"
            for player in team:
                message+=f"- {player}\n"

        await ctx.send(message)
        
        #TODO : add warning message for uneven teams
        #TODO : add aliases support
        
async def setup(bot):
    try:
        await bot.add_cog(RandomTeams(bot))
        logger.info("RandomTeams cog loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load RandomTeams cog: {e}", exc_info=True)
        raise