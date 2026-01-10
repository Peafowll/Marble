import logging
import requests
import discord
import random
from discord.ext import commands
from discord import Color, Embed
import datetime
import json
import math

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


def get_random_pokemon():

    id = random.randint(1, 1025)
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

# TODO : parse regioanl forms like alola
# TODO : add pokedex entry
# TODO : add pokedex number
# TODO : add height/weight
# TODO : add evolution line
# TODO : make daily
# TODO : make ratings
# TODO : make json for no repeats
# TODO : add emoji bars for more stats
# TODO : add ability descriptions


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



    parsed_data = {
        "form_name" : data['forms'][0]['name'],
        "abilities" : [name for name in [ability_entry['ability']['name'] for ability_entry in data['abilities']]],
        "types" : types,
        "stats" : stats,
        "image_link" : data['sprites']['other']['official-artwork']['front_default']
    }
    
    print(json.dumps(parsed_data, indent=4))

    return parsed_data
    
def generate_stat_bar(stat_value):
    RED_SQURE = "🟥"
    GREEN_SQUARE = "🟩"
    ORANGE_SQUARE = "🟧"
    YELLOW_SQUARE = "🟨"
    BLUE_SQUARE = "🟦"
    PURPLE_SQUARE = "🟪"
    BLACK_SQUARE = "⬛"

    if stat_value <= 29:
        square = RED_SQURE
    elif stat_value <= 59:
        square = ORANGE_SQUARE
    elif stat_value <= 89:
        square = YELLOW_SQUARE
    elif stat_value <= 119:
        square = GREEN_SQUARE
    elif stat_value <= 149:
        square = BLUE_SQUARE
    else:
        square = PURPLE_SQUARE    

    blocks = math.ceil(stat_value / 20)
    max_blocks = 10
    if blocks > max_blocks:
        blocks = max_blocks
    return square * (blocks) + BLACK_SQUARE * (max_blocks - blocks)

def create_embed(parsed_data):


    name = parsed_data["form_name"].title().replace("-", " ")

    type_one = parsed_data["types"][0]

    typing = EMOJI_TYPE_DICT[type_one] + " " + type_one.upper()

    if len(parsed_data["types"])>1:
        type_two = parsed_data["types"][1]
        typing = typing + " / " + EMOJI_TYPE_DICT[type_two] + " " + type_two.upper()

    embed = discord.Embed(
        title = name,
        color = discord.Color.red(),
        timestamp = datetime.datetime.now(),
        description = (
            f"*Typing* : {typing} "
        ),
        
    )
    embed.set_author(name="DAILY POKEMON!")

    embed.set_image(url=parsed_data["image_link"])
    
    abilities = ["- "+ ability.title().replace("-"," ") for ability in parsed_data["abilities"]]

    abilities_str = "\n".join(abilities)

    embed.add_field(name="Abilities : ",
                    value=abilities_str,
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
    
    return embed

class DailyPokemon(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(hidden=True)
    @commands.is_owner()
    async def random_mon(self, ctx):
        await ctx.send(embed=create_embed(parse_pokemon_data(get_random_pokemon())))

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
