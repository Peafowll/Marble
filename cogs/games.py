import discord
from discord.ext import commands
from discord.ui import Button, View
from helpers import find_lol_spells
import random
import json
import asyncio
import time, datetime


champion_abilities = find_lol_spells()
with open("championAliases.json","r",encoding="utf8") as file:
    champion_aliases=json.load(file)

def get_leaderboards():
    with open("loltriviaLeaderboards.json", "r",encoding="utf8") as file:
        data = json.load(file)
    return data

def update_leaderboard(player_name,player_id,leaderboard,difficulty,score):
    date = datetime.datetime.now().date()

    if difficulty not in leaderboard:
        leaderboard[difficulty] = {}

    player_id_str = str(player_id)
    
    if player_id_str in leaderboard[difficulty]:
        if leaderboard[difficulty][player_id_str]["score"] >= score:
            return False

    leaderboard[difficulty][player_id_str] = {
        "player_name": player_name,
        "score": score,
        "date": str(date)
    }
    
    return leaderboard

def save_leaderboard(leaderboards):
    with open("loltriviaLeaderboards.json", "w", encoding="utf8") as file:
        json.dump(leaderboards,file,indent=4)

def display_leaderboard(leaderboards, difficulty, count):
    """Display top players for a given difficulty."""
    leaderboard = leaderboards.get(difficulty, {})

    leaderboard_list = [(entry["player_name"], entry["score"]) for entry in leaderboard.values()]
    
    sorted_leaderboard = sorted(leaderboard_list, key=lambda x: x[1], reverse=True)

    return sorted_leaderboard[:count]

    

class DifficultyView(View):
    def __init__(self, timeout=60):
        super().__init__(timeout=timeout)
        self.game_difficulty = None

    @discord.ui.button(label="Ults Only", style=discord.ButtonStyle.green, custom_id="ults_only")
    async def ults_button(self, interaction: discord.Interaction, button: Button):
        self.game_difficulty = "Ults"
        await interaction.response.send_message("You have chosen ULTS ONLY.")
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        self.stop()

    @discord.ui.button(label="Abilities", style=discord.ButtonStyle.primary, custom_id="abilities")
    async def abilities_button(self, interaction: discord.Interaction, button: Button):
        self.game_difficulty = "Abilities"
        await interaction.response.send_message("You have chosen ABILITIES.")
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        self.stop()

    @discord.ui.button(label="Anything Goes", style=discord.ButtonStyle.red, custom_id="AG")
    async def anything_goes_button(self, interaction: discord.Interaction, button: Button):
        self.game_difficulty = "AG"
        await interaction.response.send_message("You have chosen ANYTHING GOES.")
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        self.stop()

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

class Games(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
    
    @commands.command(aliases=["lol_trivia"])
    async def loltrivia(self,ctx):
        """Plays a game of the LoL Ult Name guessing game."""
        channel = ctx.channel
        author_name = ctx.author.name
        author_id = ctx.author.id
        author_mention = ctx.author.mention
        champion_names = list(champion_abilities.keys())

        leaderboards = get_leaderboards()

        embed = discord.Embed(
            title="Guess the champion!",
            description="### What difficulty would you like?\n\n**Ults** = Ultimates Only\n**Abilities** = Ultimates and Basic Abilities\n**Anything Goes** = Ults, Basic Abilities, Passives and Titles!\n\n*Type the champion name to answer, or type 'ff' to surrender.*",
            color=discord.Color.gold()
        )
        view = DifficultyView()

        await ctx.send(embed=embed, view=view)
        await view.wait()

        if view.game_difficulty is None:
            await ctx.send(f"{author_mention}, you took too long to select a difficulty.")
            return

        difficulty = view.game_difficulty

        score = 0
        game_on = True
        while game_on == True:
            current_champion = random.choice(champion_names)

            if difficulty == "Ults":
                hint = champion_abilities[current_champion][5]
                description = f"What champion has the ultimate **{hint}**?"
            elif difficulty == "Abilities":
                hint = random.choice(champion_abilities[current_champion][2:6])
                description = f"What champion has the ability **{hint}**?"
            elif difficulty == "AG":
                ability_type = random.randint(0, 5)
                hint = champion_abilities[current_champion][ability_type]
                
                if ability_type == 0:
                    hint = hint.title()
                    description = f"What champion has the title **{hint}**?"
                else:
                    description = f"What champion has the ability **{hint}**?"

            embed = discord.Embed(
                title="Guess the champion!",
                description=description,
                color=discord.Color.green()
            )           
            embed.set_footer(text=f"Score: {score} | You have 30 seconds to answer")
            await ctx.send(embed=embed)
            def check(m):
                return m.channel == channel and m.author.id == author_id
            try:
                reply = await self.bot.wait_for("message", check=check, timeout=30.0)
                reply_text = reply.content
                answer = reply_text.lower()
                if answer in ["quit", "q", "ff"]:
                    await ctx.send(f"{author_mention}, you surrendered.")
                    game_on = False
                elif answer in champion_aliases[current_champion]:
                    score += 1
                    await ctx.send(f"{author_mention} ✅ Correct! **+1 point**")
                else:
                    await ctx.send(f"{author_mention} ❌ Wrong! The answer was **{current_champion}**")
                    game_on = False
            except asyncio.TimeoutError:
                await ctx.send(f"{author_mention} ⏱️ Time's up! The answer was **{current_champion}**")
                game_on = False
        
        await ctx.send(f"{author_mention}, you got a **final score** of **{score} points**!")
        
        if score > 0:
            updated_leaderboards = update_leaderboard(author_name, author_id, leaderboards, difficulty, score)
            if updated_leaderboards:
                save_leaderboard(updated_leaderboards)
                await ctx.send("🏆 New personal best recorded!")

async def setup(bot):
    await bot.add_cog(Games(bot))