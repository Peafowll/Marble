import discord
from discord.ext import commands
import requests
class Games(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
    
    @commands.command()
    async def ult_game(self,ctx):
        """Lets you play the League of Legends ultimate name game."""
        author = ctx.author
        await ctx.send("Let's Play!")

async def setup(bot):
    await bot.add_cog(Games(bot))