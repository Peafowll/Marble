import logging
import requests
import discord
import random
from discord.ext import commands, tasks
from discord import Color, Embed
import datetime
import json
import math
import os
from typing import Dict, List, Union
import aiohttp
from zoneinfo import ZoneInfo
logger = logging.getLogger('discord.daily_pokemon')


EMOJI_TYPE_DICT = {
    "bug" : "🪲",
    "dark" : "🕶️",
    "dragon" : "🐉",
    "electric" : "⚡",
    "fairy" : "✨",
    "fighting" : "🥊",
    "fire" : "🔥",
    "flying" : "🪽",
    "ghost" : "👻",
    "grass" : "🌱",
    "ground" : "⛰️",
    "ice" : "🧊",
    "normal" : "⚪",
    "poison" : "☠️",
    "psychic" : "🔮",
    "rock" : "🪨",
    "steel" : "🔩",
    "water" : "💧",
}

def _boldify(text: str) -> str:
    return f"**{text}**"

class DailyRatingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) 

    @discord.ui.select(
        placeholder="Rate this Pokémon (1-10)",
        custom_id="daily_pokemon:rating_select", 
        options=[discord.SelectOption(label=str(i), value=str(i)) for i in range(1, 11)]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        pokemon_name = interaction.message.embeds[0].title
        rating = select.values[0]
        user_id = interaction.user.id
        username = interaction.user.name
        save_rating(user_id,username, pokemon_name, rating)

        await interaction.response.send_message(
            f"✅ You rated **{pokemon_name}** a **{rating}/10**!",
            ephemeral=True
        )


def save_rating(user_id: int,username : str, pokemon_name: str, rating: str):
    """
    Global helper function to bridge the View and the Manager.
    Instantiates the manager to save the data to JSON.
    """
    manager = PokemonRatingManager()
    
    try:
        rating_int = int(rating)
        manager.save_rating(user_id,username, pokemon_name, rating_int)
    except ValueError:
        logger.error(f"Failed to convert rating '{rating}' to integer for User {user_id}")

class PokemonSubscriberManager:
    def __init__(self, filepath: str = 'data/dailyPokemonSubscribers.json'):
        """
        Initialize the manager with a file path. 
        Creates the directory if it doesn't exist.
        """
        self.filepath = filepath
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)

    def _load_db(self) -> Dict[str, str]:
        """Internal helper to load data from disk safely."""
        try:
            with open(self.filepath, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_db(self, data: Dict[str, str]) -> None:
        """Internal helper to save data to disk."""
        with open(self.filepath, 'w') as f:
            json.dump(data, f, indent=4) 

    def add_subscriber(self, user_id: int, name: str) -> None:
        """Adds or updates a subscriber."""
        subscribers = self._load_db()
        subscribers[str(user_id)] = name
        self._save_db(subscribers)
        print(f"Subscribed: {name} ({user_id})")

    def remove_subscriber(self, user_id: int) -> bool:
        """
        Removes a subscriber. 
        Returns True if successful, False if user wasn't subscribed.
        """
        subscribers = self._load_db()
        if str(user_id) in subscribers:
            del subscribers[str(user_id)]
            self._save_db(subscribers)
            return True
        return False

    def get_subscribers(self) -> Dict[str, str]:
        """Returns the full dictionary of subscribers."""
        return self._load_db()

    def get_subscriber_ids(self) -> List[int]:
        """Returns a list of integer IDs for easy iteration."""
        subscribers = self._load_db()
        return [int(uid) for uid in subscribers.keys()]

    def is_subscribed(self, user_id: int) -> bool:
        """Check if a specific ID is already in the list."""
        subscribers = self._load_db()
        return str(user_id) in subscribers      

class PokemonRatingManager:
    def __init__(self, filepath: str = 'data/dailyPokemonRatings.json'):
        """
        Initialize the manager with a file path. 
        Creates the directory if it doesn't exist.
        """
        self.filepath = filepath
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)

    def _load_db(self) -> Dict[str, Dict[str, int]]:
        """Internal helper to load data from disk safely."""
        try:
            with open(self.filepath, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_db(self, data: Dict[str, Dict[str, int]]) -> None:
        """Internal helper to save data to disk."""
        with open(self.filepath, 'w') as f:
            json.dump(data, f, indent=4) 

    def save_rating(self, user_id: int, username : str, pokemon_name: str, rating: int) -> None:
        """Saves or updates a user's rating for a specific Pokémon."""
        history = self._load_db()
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        user_key = str(username) + "_" + str(user_id)

        if today not in history:
            history[today] = {}

        entry = history[today]

        entry["pokemon_name"] = pokemon_name

        entry["ratings"] = entry.get("ratings", {})

        entry["ratings"][user_key] = rating

        history[today] = entry

        self._save_db(history)
        print(f"Saved rating: User {user_id} rated {pokemon_name} a {rating}/10, date = {datetime.datetime.now().strftime('%Y-%m-%d')}")
    

def get_random_pokemon():

    data_location = 'data/unusedPokemonIDs.json'
    valid_ids_location = 'valid_pokemon_ids.json'

    try:
        with open(data_location, 'r') as f:
            unused_ids = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.info(f"{data_location} not found or invalid. Initializing from {valid_ids_location}...")
        try:
            with open(valid_ids_location, 'r') as f:
                unused_ids = json.load(f)
            os.makedirs(os.path.dirname(data_location), exist_ok=True)
            with open(data_location, 'w') as f:
                json.dump(unused_ids, f, indent=4)
            logger.info(f"Successfully initialized {data_location} with {len(unused_ids)} Pokémon IDs.")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load {valid_ids_location}: {e}")
            return None

    if not unused_ids:
        logger.warning("No more Pokemon left in the list!")
        return None

    mon_id = random.choice(unused_ids)
    unused_ids.remove(mon_id)


    with open(data_location, 'w') as f:
        json.dump(unused_ids, f)

    url = f"https://pokeapi.co/api/v2/pokemon/{mon_id}"
    response = requests.get(url)

    if response.status_code != 200:
        logger.error(f"Failed to fetch Pokémon data: {response.status_code}")
        return None
    
    data = response.json()

    return data

def query_pokemon_by_id(mon_id: int):

    url = f"https://pokeapi.co/api/v2/pokemon/{mon_id}"
    response = requests.get(url)

    if response.status_code != 200:
        logger.error(f"Failed to fetch Pokémon data: {response.status_code}")
        return None
    
    data = response.json()

    return data

def get_pokemon_species_data(species_url: str):
    response = requests.get(species_url)

    if response.status_code != 200:
        logger.error(f"Failed to fetch Pokémon species data: {response.status_code}")
        return None
    
    data = response.json()

    return data

def get_evolution_chain_data(evolution_chain_url: str):
    response = requests.get(evolution_chain_url)

    if response.status_code != 200:
        logger.error(f"Failed to fetch Pokémon evolution chain data: {response.status_code}")
        return None
    
    data = response.json()

    return data

def get_ability_data(ability_url: str):
    response = requests.get(ability_url)

    if response.status_code != 200:
        logger.error(f"Failed to fetch Pokémon ability data: {response.status_code}")
        return None
    
    data = response.json()

    return data

def get_abillity_description(ability_data):
    entries = ability_data['effect_entries']
    for entry in entries:
        if entry['language']['name'] == 'en':
            return entry['short_effect']
    return "No description available."

# TODO : add mass sub

def get_evo_stages(chain_data):

    def clean(n): 
        return n.title().replace("-", " ")
    
    chain = chain_data['chain']
    
    stage_1 = [clean(chain['species']['name'])]
    
    stage_2 = []
    stage_3 = []
    
    for evo in chain['evolves_to']:
        stage_2.append(clean(evo['species']['name']))
        
        for sub_evo in evo['evolves_to']:
            stage_3.append(clean(sub_evo['species']['name']))
            
    return stage_1, stage_2, stage_3

def parse_pokemon_data(data):
    
    type1 = data['types'][0]['type']['name']
    type2 = data['types'][1]['type']['name'] if len(data['types']) > 1 else None

    types = [type1]
    if type2:
        types.append(type2)

    stats = {
        "hp": data['stats'][0]['base_stat'],
        "attack": data['stats'][1]['base_stat'],
        "defense": data['stats'][2]['base_stat'],
        "special-attack": data['stats'][3]['base_stat'],
        "special-defense": data['stats'][4]['base_stat'],
        "speed": data['stats'][5]['base_stat']
    }

    kilogram_weight = data['weight'] / 10
    if kilogram_weight.is_integer():
        kilogram_weight = int(kilogram_weight)
    meter_height = data['height'] / 10
    if meter_height.is_integer():
        meter_height = int(meter_height)

    species_url = data['species']['url']

    species_data = get_pokemon_species_data(species_url)

    pokedex_entries_english = [entry["flavor_text"] for entry in species_data['flavor_text_entries'] if entry['language']['name'] == 'en']

    evolution_chain_url = species_data['evolution_chain']['url']

    evolution_chain_data = get_evolution_chain_data(evolution_chain_url)

    evo_stages = get_evo_stages(evolution_chain_data)

    abilities = {
        ability_entry['ability']['name'].title().replace("-", " ") : get_abillity_description(get_ability_data(ability_entry['ability']['url']))
        for ability_entry in data['abilities']
    }

    parsed_data = {
        "form_name" : data['forms'][0]['name'],
        "species_name" : species_data['name'],
        "abilities" : abilities,
        "types" : types,
        "stats" : stats,
        "image_link" : data['sprites']['other']['official-artwork']['front_default'],
        "pokedex_number" : data['id'],
        "weight" : kilogram_weight,
        "height" : meter_height,
        "entries" : pokedex_entries_english,
        "evolution_stages" : evo_stages
    }


    return parsed_data
    
def generate_stat_bar(stat_value):
    RED_SQURE = "🟥"
    GREEN_SQUARE = "🟩"
    YELLOW_SQUARE = "🟨"
    BLUE_SQUARE = "🟦"
    PURPLE_SQUARE = "🟪"
    BLACK_SQUARE = "⬛"

    if stat_value <= 40:
        square = RED_SQURE
    elif stat_value <= 80:
        square = YELLOW_SQUARE
    elif stat_value <= 120:
        square = GREEN_SQUARE
    elif stat_value <= 160:
        square = BLUE_SQUARE
    else:
        square = PURPLE_SQUARE
    
    blocks = math.ceil(stat_value / 20)

    max_blocks = 10
    if blocks > max_blocks:
        blocks = max_blocks
    return square * (blocks) + BLACK_SQUARE * (max_blocks - blocks)

def build_evolution_line(evo_stages, current_name):
    stage_1, stage_2, stage_3 = evo_stages
    
    separator = " | "
    header_width = 7 
    
    evolution_str = "```\n"

    def format_name(name):
        return f"> {name}" if name.lower() == current_name.lower() else f"  {name}"

    for i, name in enumerate(stage_1):
        label = "Stage 1" if i == 0 else ""
        evolution_str += f"{label:<{header_width}}{separator}{format_name(name)}\n"

    if stage_2:
        for i, name in enumerate(stage_2):
            label = "Stage 2" if i == 0 else ""
            evolution_str += f"{label:<{header_width}}{separator}{format_name(name)}\n"

    if stage_3:
        for i, name in enumerate(stage_3):
            label = "Stage 3" if i == 0 else ""
            evolution_str += f"{label:<{header_width}}{separator}{format_name(name)}\n"

    return evolution_str + "```"

def create_embed(parsed_data):

    display_name = parsed_data["form_name"].title().replace("-", " ")
    
    species_name = parsed_data["species_name"].title().replace("-", " ")

    type_one = parsed_data["types"][0]

    typing = EMOJI_TYPE_DICT[type_one] + " " + _boldify(type_one.upper())

    if len(parsed_data["types"])>1:
        type_two = parsed_data["types"][1]
        typing = typing + " / " + EMOJI_TYPE_DICT[type_two] + " " + _boldify(type_two.upper())

    embed = discord.Embed(
        title = display_name,
        color = discord.Color.red(),
        timestamp = datetime.datetime.now(),
        description = (
            f"*#{parsed_data['pokedex_number']:03d}*\n"
            f"**Typing** : {typing} \n"
            f"**Height** : {parsed_data["height"]} m\n"
            f"**Weight** : {parsed_data["weight"]} kg\n"
        ),
        
    )
    embed.set_author(name="DAILY POKEMON!")

    embed.set_image(url=parsed_data["image_link"])

    embed.add_field(name="Possible Abilities : ",
                    value='\n'.join([f"- **{ability}**\n  {desc}" for ability, desc in parsed_data["abilities"].items()]),
                    inline=False)
    
    
    evolution_str = build_evolution_line(parsed_data["evolution_stages"], species_name)

    embed.add_field(name="Evolution : ",
                    value = evolution_str,
                    inline=False)

    stats_str = ""

    stat_aliases = {
        "Hp" : "HP",
        "Attack" : "ATK",
        "Defense" : "DEF",
        "Special Attack" : "SP.ATK",
        "Special Defense" : "SP.DEF",
        "Speed" : "SPD"
    }
    for stat in parsed_data["stats"]:
        stat_name = stat.title().replace("-"," ")
        stat_diplay_name = stat_aliases[stat_name]
        stat_value = parsed_data["stats"][stat]
        stats_str += f"{stat_diplay_name:<6}: {stat_value:<3}{generate_stat_bar(stat_value=stat_value)}\n"

    embed.add_field(name="Stats : ",
                    value="```"+stats_str+"```",
                    inline=False)
    
    entry = random.choice(parsed_data["entries"]).replace("\n"," ")

    embed.add_field(name="Pokedex Entry : ",
                    value=entry,
                    inline=False)
    
    
    
    return embed

class DailyPokemon(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(DailyRatingView())
        self.sub_manager = PokemonSubscriberManager()

    @commands.Cog.listener()
    async def on_ready(self):
        """
        Called when the bot is ready.
        """
        if not self.daily_pokemon.is_running():
            self.daily_pokemon.start()


    @tasks.loop(time=datetime.time(hour=22, minute=59, tzinfo=ZoneInfo("Europe/Bucharest")))
    async def daily_pokemon(self):
        data = get_random_pokemon() 
        if not data: 
            return
        parsed_data = parse_pokemon_data(data)
        embed = create_embed(parsed_data)
        view = DailyRatingView()

        subscriber_ids = self.sub_manager.get_subscriber_ids()

        for user_id in subscriber_ids:
            try:
                user = self.bot.get_user(user_id)
                
                # if not in cache 
                if not user:
                    try:
                        user = await self.bot.fetch_user(user_id)
                    except discord.NotFound:
                        logger.warning(f"User {user_id} no longer exists. Removing from DB.")
                        self.sub_manager.remove_subscriber(user_id)
                        continue
                    except discord.HTTPException:
                        logger.warning(f"Failed to fetch user {user_id} due to network/API error.")
                        continue

                if user:
                    await user.send(embed=embed, view=view)
                    logger.info(f"Sent daily Pokemon to {user.name} ({user.id})")

            except discord.Forbidden:
                logger.warning(f"Cannot send message to user ID {user_id} (Forbidden - DMs closed).")
            except Exception as e:
                logger.error(f"Error sending daily Pokémon to user ID {user_id}: {e}", exc_info=True)

    @daily_pokemon.before_loop
    async def before_daily_pokemon(self):
        await self.bot.wait_until_ready()

    @commands.command(hidden=True)
    @commands.is_owner()
    async def random_mon(self, ctx):

        data = get_random_pokemon()
        if not data:
            await ctx.send("Failed to fetch Pokémon data.")
            return
        
        parsed_data = parse_pokemon_data(data)

        embed = create_embed(parsed_data)

        view = DailyRatingView()

        await ctx.send(embed=embed, view=view   )

    @commands.command(hidden=True)
    @commands.is_owner()
    async def specific_mon(self, ctx, mon_id: int):
        await ctx.send(embed=create_embed(parse_pokemon_data(query_pokemon_by_id(mon_id))))


    @commands.command()
    async def sub_pokemon(self, ctx):
        """Subscribe to daily Pokémon messages."""
        user_id = ctx.author.id
        user_name = ctx.author.name

        if self.sub_manager.is_subscribed(user_id):
            await ctx.send("❌ You are already subscribed to daily Pokémon messages!")
            return

        self.sub_manager.add_subscriber(user_id, user_name)
        await ctx.send("✅ You have been subscribed to daily Pokémon messages!")

    @commands.command()
    async def unsub_pokemon(self, ctx):
        """Unsubscribe from daily Pokémon messages."""
        user_id = ctx.author.id

        if not self.sub_manager.is_subscribed(user_id):
            await ctx.send("❌ You are not subscribed to daily Pokémon messages!")
            return

        self.sub_manager.remove_subscriber(user_id)
        await ctx.send("✅ You have been unsubscribed from daily Pokémon messages!")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def list_pokemon_subs(self, ctx):
        """List all users subscribed to daily Pokémon messages."""
        subscribers = self.sub_manager.get_subscribers()
        if not subscribers:
            await ctx.send("No users are currently subscribed to daily Pokémon messages.")
            return

        sub_list = "\n".join([f"- {name} (ID: {uid})" for uid, name in subscribers.items()])
        embed = discord.Embed(
            title="Daily Pokémon Subscribers",
            description=sub_list,
            color=Color.blue()
        )
        await ctx.send(embed=embed)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def show_pokemon_ratings_history(self, ctx):
        """Show the Pokémon ratings history (for debugging)."""
        rating_manager = PokemonRatingManager()
        history = rating_manager._load_db()  # Accessing the internal method for demonstration
        formatted_history = json.dumps(history, indent=4)
        if len(formatted_history) > 2000:
            await ctx.send("The ratings history is too long to display.")
        else:
            await ctx.send(f"```json\n{formatted_history}\n```")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def set_mass_subscribers(self, ctx):
        """Set mass subscribers from a predefined list."""
        starting_users = [
            (370638781998694410, "arrow_san"),
            (785545332788035614, "143.dariaa"),
            (457123490080751626, "vladimus2005"),
            (246956083934003211, "painite01"),
            (440831015456473089, "yoyoo0722"),
            (608761289442852895, "itz_wolfseer"),
            (322758058679861258, "frogthephrog"),
            (371975159923343362, "el_donte"),
            (1224715729056694366, "tepeel"), 
            (264416824777637898, "peafowl")
        ]
        for user_id, user_name in starting_users:
            if not self.sub_manager.is_subscribed(user_id):
                self.sub_manager.add_subscriber(user_id, user_name)
            user = await self.bot.fetch_user(user_id)
            await user.send(
                    "**🎉 You have been** ***(pre)*** **subscribed to Daily Pokémon messages!**\n\n"
                    "You will receive a daily message with a random Pokémon and the option to rate it.\n\n"
                    "**How to Rate:**\n"
                    "• Use the dropdown menu to select your score.\n"
                    "• ⚠️ **Careful:** Clicking an option submits the rating **instantly**.\n"
                    "• Rate based on design, stats, interesting abilities, or just personal vibe!\n\n"
                    "If you want to opt-out, use the `!unsub_pokemon` command."
                )
            
        await ctx.send("✅ Test users have been subscribed to daily Pokémon messages.")
        await ctx.send("The file looks like this now:")
        await self.list_pokemon_subs(ctx)

async def setup(bot: commands.Bot):
    try:
        await bot.add_cog(DailyPokemon(bot))
        logger.info("DailyPokemon cog loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load DailyPokemon cog: {e}", exc_info=True)
        raise
