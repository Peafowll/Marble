import discord
from discord.ext import commands
from discord.ui import Button, View
from helpers import find_lol_spells
import random
import json
import asyncio
import time, datetime
import logging

logger = logging.getLogger('discord.games')

# Create a separate logger for game debugging
game_debug_logger = logging.getLogger('game_debug')
game_debug_logger.setLevel(logging.DEBUG)
game_debug_handler = logging.FileHandler(f'game_debug_{datetime.datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8')
game_debug_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
game_debug_logger.addHandler(game_debug_handler)

try:
    champion_abilities = find_lol_spells()
    with open("championAliases.json","r",encoding="utf8") as file:
        champion_aliases=json.load(file)
    logger.info("Successfully loaded champion data")
except FileNotFoundError as e:
    logger.error(f"Required file not found: {e}", exc_info=True)
    champion_abilities = {}
    champion_aliases = {}
except json.JSONDecodeError as e:
    logger.error(f"Error parsing JSON file: {e}", exc_info=True)
    champion_abilities = {}
    champion_aliases = {}
except Exception as e:
    logger.error(f"Unexpected error loading champion data: {e}", exc_info=True)
    champion_abilities = {}
    champion_aliases = {}

def get_leaderboards():
    try:
        with open("loltriviaLeaderboards.json", "r",encoding="utf8") as file:
            data = json.load(file)
        logger.debug("Leaderboards loaded successfully")
        return data
    except FileNotFoundError:
        logger.warning("Leaderboards file not found, creating new one")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing leaderboards JSON: {e}", exc_info=True)
        return {}
    except Exception as e:
        logger.error(f"Unexpected error loading leaderboards: {e}", exc_info=True)
        return {}

def update_leaderboard(player_name,player_id,leaderboard,difficulty,score):
    date = datetime.datetime.now().date()

    if difficulty not in leaderboard:
        leaderboard[difficulty] = {}

    player_id_str = str(player_id)
    
    if player_id_str in leaderboard[difficulty]:
        if leaderboard[difficulty][player_id_str]["score"] >= score:
            return False

    leaderboard[difficulty][player_id_str] = {
        "player_name": player_name.capitalize(),
        "score": score,
        "date": str(date)
    }
    
    return leaderboard

def save_leaderboard(leaderboards):
    try:
        with open("loltriviaLeaderboards.json", "w", encoding="utf8") as file:
            json.dump(leaderboards,file,indent=4)
        logger.info("Leaderboards saved successfully")
    except IOError as e:
        logger.error(f"Error writing leaderboards file: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Unexpected error saving leaderboards: {e}", exc_info=True)

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
        """Play a League of Legends trivia game! Guess champions by their abilities, ultimates, or titles. Choose your difficulty and see how high you can score!"""
        try:
            channel = ctx.channel
            author_name = ctx.author.name
            author_id = ctx.author.id
            author_mention = ctx.author.mention
            champion_names = list(champion_abilities.keys())
            if not champion_names:
                await ctx.send("❌ Champion data is not available. Please contact the bot administrator.")
                logger.error("Champion data is empty")
                return

            leaderboards = get_leaderboards()

            embed = discord.Embed(
                title="Guess the champion!",
                description=f"{author_mention}\n### What difficulty would you like?\n\n**Ults** = Ultimates Only\n**Abilities** = Ultimates and Basic Abilities\n**Anything Goes** = Ults, Basic Abilities, Passives and Titles!\n\n*Type the champion name to answer, or type 'ff' to surrender.*",
                color=discord.Color.gold()
            )
            view = DifficultyView()

            await ctx.send(embed=embed, view=view)
            await view.wait()

            if view.game_difficulty is None:
                await ctx.send(f"{author_mention}, you took too long to select a difficulty.")
                logger.info(f"{author_name} timed out on difficulty selection")
                return

            difficulty = view.game_difficulty
            logger.info(f"{author_name} started loltrivia game with difficulty: {difficulty}")

            if difficulty == "Ults":
                embed_color = discord.Color.green()
            elif difficulty == "Abilities":
                embed_color = discord.Color.blue()
            elif difficulty == "AG":
                embed_color = discord.Color.red()

            score = 0
            game_on = True
            remaining_hints = []

            if difficulty == "Ults":
                for champ in champion_names:
                    remaining_hints.append((champ, champion_abilities[champ][5]))
            elif difficulty == "Abilities":
                for champ in champion_names:
                    for ability in champion_abilities[champ][2:6]:
                        remaining_hints.append((champ, ability))
            elif difficulty == "AG":
                for champ in champion_names:
                    for i, ability in enumerate(champion_abilities[champ]):
                        if i == 0: 
                            remaining_hints.append((champ, ability.title()))
                        else:
                            remaining_hints.append((champ, ability))

            while game_on:
                try:
                    hint_index = random.randrange(len(remaining_hints))
                    current_champion, hint = remaining_hints.pop(hint_index)
                    
                    game_debug_logger.debug(f"Hint given to {author_name}: '{hint}' (Answer: {current_champion}, Difficulty: {difficulty})")

                    if difficulty == "Ults":
                        description = f"{author_mention}\nWhat champion has the ultimate **{hint}**?"
                    elif difficulty == "Abilities":
                        description = f"{author_mention}\nWhat champion has the ability **{hint}**?"
                    elif difficulty == "AG":
                        if hint in [champion_abilities[c][0].title() for c in champion_names]:
                            description = f"{author_mention}\nWhat champion has the title **{hint}**?"
                        else:
                            description = f"{author_mention}\nWhat champion has the ability **{hint}**?"

                    embed = discord.Embed(
                        title="Guess the champion!",
                        description=description,
                        color=embed_color
                    )           
                    embed.set_footer(text=f"Score: {score} | You have 30 seconds to answer")
                    
                    def check(m):
                         return m.channel.id == channel.id and m.author.id == author_id
                    
                    wait_task = asyncio.create_task(self.bot.wait_for("message", check=check, timeout=30.0))
                    await ctx.send(embed=embed)
                    
                    try:
                        reply = await wait_task
                        reply_text = reply.content
                        answer = reply_text.lower()
                        
                        if answer in ["quit", "q", "ff"]:
                            await ctx.send(f"{author_mention}, you surrendered.")
                            game_on = False
                            logger.info(f"{author_name} surrendered with score: {score}")
                        elif answer in champion_aliases.get(current_champion, []):
                            score += 1
                            await ctx.send(f"{author_mention} ✅ Correct! **+1 point**")
                        else:
                            await ctx.send(f"{author_mention} ❌ Wrong! The answer was **{current_champion}**")
                            game_on = False
                            logger.info(f"{author_name} got wrong answer. Final score: {score}")
                    except asyncio.TimeoutError:
                        await ctx.send(f"{author_mention} ⏱️ Time's up! The answer was **{current_champion}**")
                        game_on = False
                        logger.info(f"{author_name} timed out. Final score: {score}")
                except Exception as e:
                    logger.error(f"Error during game loop: {e}", exc_info=True)
                    await ctx.send(f"❌ An error occurred during the game.")
                    game_on = False
            
            if not remaining_hints and game_on:
                await ctx.send(f"{author_mention} 🎉 Congratulations! You've gone through all possible hints!")

            await ctx.send(f"{author_mention}, you got a **final score** of **{score} points**!")
            
            if score > 0:
                try:
                    updated_leaderboards = update_leaderboard(author_name, author_id, leaderboards, difficulty, score)
                    if updated_leaderboards is not False:
                        save_leaderboard(updated_leaderboards)
                        await ctx.send("🏆 New personal best recorded!")
                        logger.info(f"{author_name} set new personal best: {score} points in {difficulty}")
                except Exception as e:
                    logger.error(f"Error updating leaderboard: {e}", exc_info=True)
                    await ctx.send("⚠️ Score was not saved due to an error.")
        
        except Exception as e:
            logger.error(f"Fatal error in loltrivia command: {e}", exc_info=True)
            await ctx.send(f"❌ A critical error occurred. Please try again later.")

    @commands.command(aliases=['loltrivialeaderboard'])
    async def loltlb(self,ctx,difficulty: str = "all", count: int = 10):
        """
        View the League of Legends trivia leaderboard.
        
        Usage: !loltlb [difficulty] [count]
        - difficulty: "ults", "abilities", "ag", or "all" (default: all)
        - count: Number of top players to display (default: 10, max: 50)
        
        Example: !loltlb abilities 5
        """
        try:
            leaderboards = get_leaderboards()
            
            difficulty_map = {
                "ults": "Ults",
                "ult": "Ults",
                "abilities": "Abilities",
                "ability": "Abilities",
                "ag": "AG",
                "anything": "AG",
                "anythinggoes": "AG",
                "all": "all"
            }
            
            normalized_difficulty = difficulty_map.get(difficulty.lower())
            
            if normalized_difficulty is None:
                await ctx.send(f"❌ Invalid difficulty! Please use: `Ults`, `Abilities`, `AG`, `all` or nothing.")
                logger.warning(f"{ctx.author.name} used invalid difficulty: {difficulty}")
                return
            
            if count < 1:
                await ctx.send(f"❌ Count must be at least 1!")
                return
            if count > 50:
                count = 50
                await ctx.send(f"⚠️ Count limited to 50.")
            
            if normalized_difficulty == "all":
                embed = discord.Embed(
                    title="🏆 LoL Trivia Leaderboards",
                    color=discord.Color.gold()
                )
                for diff in ["Ults","Abilities","AG"]:
                    top_players = display_leaderboard(leaderboards,diff,count)
                    if top_players:
                        medal_emojis = ["🥇", "🥈", "🥉"]
                        leaderboard_text = "\n".join([
                            f"{medal_emojis[i]} **{name}** - `{score} pts`" if i < 3 
                            else f"`{i+1}.` **{name}** - `{score} pts`" 
                            for i, (name, score) in enumerate(top_players)
                        ])
                        embed.add_field(name=f"**{diff}**", value=leaderboard_text, inline=False)
                    else:
                        embed.add_field(name=f"**{diff}**", value="*No scores yet!*", inline=False)
            else:
                embed = discord.Embed(
                    title=f"🏆 LoL Trivia Leaderboard - {normalized_difficulty}",
                    color=discord.Color.gold()
                )
                top_players = display_leaderboard(leaderboards, normalized_difficulty, count)
                if top_players:
                    medal_emojis = ["🥇", "🥈", "🥉"]
                    leaderboard_text = "\n".join([
                        f"{medal_emojis[i]} **{name}** - `{score} pts`" if i < 3 
                        else f"`{i+1}.` **{name}** - `{score} pts`" 
                        for i, (name, score) in enumerate(top_players)
                    ])
                    embed.description = leaderboard_text
                else:
                    embed.description = "*No scores yet!*"

            await ctx.send(embed=embed)
            logger.info(f"{ctx.author.name} viewed leaderboard: {normalized_difficulty}")
        
        except Exception as e:
            logger.error(f"Error in loltlb command: {e}", exc_info=True)
            await ctx.send(f"❌ An error occurred while fetching the leaderboard.")
       
async def setup(bot):
    try:
        await bot.add_cog(Games(bot))
        logger.info("Games cog loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load Games cog: {e}", exc_info=True)
        raise