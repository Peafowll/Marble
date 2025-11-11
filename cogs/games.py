import discord
from discord.ext import commands
from helpers import find_lol_spells
import random
champion_ults = find_lol_spells()

class Games(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
    
    @commands.command()
    async def ult_game(self,ctx):
        """Plays a game of the LoL Ult Name guessing game."""
        author = ctx.author
        await ctx.send("Let's Play!")

async def setup(bot):
    await bot.add_cog(Games(bot))