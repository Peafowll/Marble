import discord
from discord.ext import commands
from discord.ui import Button, View
import random
import json
import asyncio
import time, datetime
import logging

class Blamer(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    @commands.command(aliases=['whydidwelose'], hidden=True)
    async def blame(self,ctx,difficulty: str = "all", count: int = 10):
        """
        See who's fault it was you lost your previous games!
        
        Usage: !loltlb [difficulty] [count]
        - difficulty: "ults", "abilities", "ag", or "all" (default: all)
        - count: Number of top players to display (default: 10, max: 50)
        
        Example: !loltlb abilities 5
        """
       
async def setup(bot):
    try:
        await bot.add_cog(Blamer(bot))
    except Exception as e:
        raise