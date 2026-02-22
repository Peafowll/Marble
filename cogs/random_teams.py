import discord
from discord.ext import commands
from discord.ui import Button, View
from helpers import find_lol_spells
import random
import json
import asyncio
import time, datetime
import logging

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

class RandomTeams(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
    
    @commands.command(aliases=["randomteams"])
    async def random_teams(self,ctx, playercount = None, team_count = 2):
        voice_channel = ctx.author.voice.channel if ctx.author.voice else None

        if not voice_channel:
            await ctx.send("You need to be in a voice channel to use this!")
            return
    

        vc_member_names = get_current_vc_members(voice_channel)
        message = "#Random Team Builder\n The people in your voice chat are :"
        for member in vc_member_names:
            message+=f"- {member}\n"
        
        await ctx.send(message)
        await ctx.send("Send the following messages to edit the list : ")
        message = """
        - `a` *name* to add a player.
        - `r` *name* to remove a player.
        - `t` *number* to set the amount of teams to generate.
        - `d` to generate teams.
        """


        # print(f"random teams called, members in vc: {vc_member_names}")
        # if not playercount:
        #     playercount = len(vc_member_names)
        
        # count_per_team = playercount / team_count

        # count_per_team = int(count_per_team)
        # #TODO : always enter edit mode
        # if count_per_team == int(count_per_team):

        #     teams = []
        #     random.shuffle(vc_member_names)
        #     for i in range(team_count):
        #         teams.append([])
        #         for j in range(count_per_team):
        #             selected_member_name = vc_member_names.pop()
        #             teams[i].append(selected_member_name)
        # else:
        #     channel = ctx.channel
        #     author_id = ctx.author.id
        #     message = "You are not an even number of people in your current voice chat."
        #     message += "Please respond as follows to remedy :\n"
        #     message += "'+name1+name2+etc' for anyone to add to the list of participants.\n"
        #     message += "'-name1-name2-etc' for anyone to remove from the list.\n"
        #     message += "'ignore' to make the teams anyway, but receive them unbalanced.\n"
        #     message += "You may respond with '+name1+name2-name3-name4', jsut keep them in that order and without spaces." 
        #     await ctx.send(message)
        #     def check(m):
        #         return m.channel.id == channel.id and m.author.id == author_id
                        
        #     wait_task = asyncio.create_task(self.bot.wait_for("message", check=check, timeout=30.0))
            
        #     try:
        #         reply = await wait_task
        #         reply_text = reply.content
        #         answer = reply_text.lower()
        #         if answer == "ignore":
        #             print("ignore")
        #             #send

        #         else:
        #             split_string = answer.split('+')
        #             negative_unsplit_string = split_string[-1:]
        #             negative_string = negative_unsplit_string.split('-')
        #             positive_string = split_string[:-1]
        #             teams = []
        #             print(f"Positive string = {positive_string}")
        #             print(f"Negative string = {negative_string}")
        #             for member in positive_string:
        #                 vc_member_names.append(member)
        #             for member in negative_string:
        #                 if member in vc_member_names:
        #                     vc_member_names.remove(member)

        #             print(f"New teams after changes : {vc_member_names}")
                


        #     except asyncio.TimeoutError:
        #         await ctx.send(f"You didnt mention who was extra in time.")

        # print(teams)
        
async def setup(bot):
    try:
        await bot.add_cog(RandomTeams(bot))
        logger.info("RandomTeams cog loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load RandomTeams cog: {e}", exc_info=True)
        raise