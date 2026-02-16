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

class RandomTeams(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
    
    @commands.command(aliases=["randomteams"])
    async def random_teams(self,ctx, playercount = None, team_count = 2):
        voice_channel = ctx.author.voice.channel if ctx.author.voice else None
        if not voice_channel:
            await ctx.send("You need to be in a voice channel to use this!")
            return
        vc_members = voice_channel.members
        vc_member_names = [member.name for member in vc_members]
        print(f"random teams called, members in vc: {vc_member_names}")
        if not playercount:
            playercount = len(vc_member_names)
        
        count_per_team = playercount / team_count

        count_per_team = int(count_per_team)
        #TODO : add if count_per_team == int(count_per_team)

        teams = []
        random.shuffle(vc_member_names)
        for i in range(team_count):
            teams.append([])
            for j in range(count_per_team):
                selected_member_name = vc_member_names.pop()
                teams[i].append(selected_member_name)

        print(teams)
        
async def setup(bot):
    try:
        await bot.add_cog(RandomTeams(bot))
        logger.info("RandomTeams cog loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load RandomTeams cog: {e}", exc_info=True)
        raise