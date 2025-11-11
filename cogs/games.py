import discord
from discord.ext import commands
from discord.ui import Button, View
from helpers import find_lol_spells
import random
import json
champion_abilities = find_lol_spells()
with open("championAliases.json","r",encoding="utf8") as file:
    champion_aliases=json.load(file)


class DiffcultyView(View):
    def __init__(self):
        super().__init__()
        self.game_difficulty = None

    @discord.ui.button(label="Ults Only", style=discord.ButtonStyle.green,custom_id="ults_only")
    async def ults_button(self, interaction :discord.Interaction,button:Button):
        self.game_difficulty = "Ults"
        await interaction.response.send_message("You have chosen ULTS ONLY.")
        self.stop()

    @discord.ui.button(label="Abilities", style=discord.ButtonStyle.primary, custom_id="abilities" )
    async def abilities_button(self,interaction :discord.Interaction,button:Button):
        self.game_difficulty = "Abilities"
        await interaction.response.send_message("You have chosen ABILITIES.")
        self.stop()

    @discord.ui.button(label="Anything Goes", style=discord.ButtonStyle.red, custom_id="AG" )
    async def anything_goes_button(self,interaction :discord.Interaction,button:Button):
        self.game_difficulty = "AG"
        await interaction.response.send_message("You have chosen ANYTHING GOES.")
        self.stop()

class Games(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
    
    @commands.command(aliases=["ultgame"])
    async def ult_game(self,ctx):
        """Plays a game of the LoL Ult Name guessing game."""
        channel = ctx.channel
        autho_name = ctx.author.name
        author_id = ctx.author.id
        author_mention = ctx.author.mention
        champion_names = list(champion_abilities.keys())

        embed = discord.Embed(
            title="Guess the champion!",
            description="### What difficulty would you like?\n\n**Ults** = Ultimates Only\n**Abilities** = Ultimates and Basic Abilities\n**Anything Goes** = Ults, Basic Abilities and Passives",
            color=discord.Color.gold()
        )
        view = DiffcultyView()

        await ctx.send(embed=embed,view=view)
        await view.wait()

        diffculty = view.game_difficulty

        score = 0
        game_on = 1
        while game_on == 1:
            current_champion = random.choice(champion_names)

            embed = discord.Embed(
                title = "Guess the champion!",
                description=f"What champion has the ultimate **{champion_abilities[current_champion][4]}**?",
                color=discord.Color.green()
            )           
            embed.set_footer(text = f"Score : {score}")
            await ctx.send(embed=embed)
            def check(m):
                return m.channel == channel and m.author.id == author_id
            reply = await self.bot.wait_for("message", check=check)
            reply_text = reply.content
            answer = reply_text.lower()
            if answer in ["quit","q","ff"]:
                await ctx.send(f"{author_mention}, you surrendered.")
                game_on = 0
            if answer in champion_aliases[current_champion]:
                score+=1
                await ctx.send(f"{author_mention} ✅ Correct! **+1 point**.")
            else:
                await ctx.send(f"{author_mention} ❌ Wrong! The answer was **{current_champion}**!")
                game_on = 0
        await ctx.send(f"{author_mention}, you got a **final score** of **{score} points**!")

async def setup(bot):
    await bot.add_cog(Games(bot))