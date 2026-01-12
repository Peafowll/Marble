import logging
import requests
import discord
import random
from discord.ext import commands
from discord import Color, Embed
import datetime
import json
import math
import os
from typing import Dict, List, Union
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



class DailyRatingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) 

    @discord.ui.select(
        placeholder="Rate this Pokémon (1-10)",
        custom_id="daily_pokemon:rating_select", # Unique ID required for persistence
        options=[discord.SelectOption(label=str(i), value=str(i)) for i in range(1, 11)]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        pokemon_name = interaction.message.embeds[0].title
        rating = select.values[0]
        user_id = interaction.user.id
        
        # --- SAVE LOGIC ---
        # save_rating(user_id, pokemon_name, rating)
        # ------------------

        await interaction.response.send_message(
            f"✅ You rated **{pokemon_name}** a **{rating}/10**!",
            ephemeral=True
        )


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

    def save_rating(self, user_id: int, pokemon_name: str, rating: int) -> None:
        """Saves or updates a user's rating for a specific Pokémon."""
        history = self._load_db()
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        user_key = str(user_id)

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

    os.makedirs(os.path.dirname(data_location), exist_ok=True)

    try:
        with open(data_location, 'r') as f:
            unused_ids = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        with open("valid_pokemon_ids.json", 'r') as f:
            valid_ids = json.load(f)
        unused_ids =  valid_ids.copy()
        with open(data_location, 'w') as f:
            json.dump(unused_ids, f)

    id = random.choice(unused_ids)

    url = f"https://pokeapi.co/api/v2/pokemon/{id}"
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

# TODO : make daily
# TODO : make ratings
# TODO : make json for no repeats

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
    
    #print(json.dumps(parsed_data, indent=4))

    return parsed_data
    
def generate_stat_bar(stat_value):
    RED_SQURE = "🟥"
    GREEN_SQUARE = "🟩"
    YELLOW_SQUARE = "🟨"
    BLUE_SQUARE = "🟦"
    PURPLE_SQUARE = "🟪"
    BLACK_SQUARE = "⬛"

    # if stat_value < 30:
    #     square = RED_SQURE
    # elif stat_value < 60:
    #     square = ORANGE_SQUARE
    # elif stat_value < 90:
    #     square = YELLOW_SQUARE
    # elif stat_value < 120:
    #     square = GREEN_SQUARE
    # elif stat_value < 150:
    #     square = BLUE_SQUARE
    # else:
    #     square = PURPLE_SQUARE    

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

    typing = EMOJI_TYPE_DICT[type_one] + " " + type_one.upper()

    if len(parsed_data["types"])>1:
        type_two = parsed_data["types"][1]
        typing = typing + " / " + EMOJI_TYPE_DICT[type_two] + " " + type_two.upper()

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

    embed.add_field(name="Abilities : ",
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

async def setup(bot: commands.Bot):
    try:
        await bot.add_cog(DailyPokemon(bot))
        logger.info("DailyPokemon cog loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load DailyPokemon cog: {e}", exc_info=True)
        raise
