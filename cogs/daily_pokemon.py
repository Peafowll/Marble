import logging
import requests
import discord
import random
from discord.ext import commands
import json

logger = logging.getLogger('discord.daily_pokemon')

def get_random_pokemon():

    id = random.randint(1, 1025)
    url = f"https://pokeapi.co/api/v2/pokemon/{id}"
    response = requests.get(url)

    if response.status_code != 200:
        logger.error(f"Failed to fetch Pokémon data: {response.status_code}")
        return None
    
    data = response.json()

    return data


# TODO : parse regioanl forms like alola

def parse_random_pokemon(data):
    
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
        "image" : data['sprites']['other']['official-artwork']['front_default']
    }
    
    print(json.dumps(parsed_data, indent=4))

    return parsed_data
    


class DailyPokemon(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(hidden=True)
    @commands.is_owner()
    async def random_mon(self, ctx):
        await ctx.send(parse_random_pokemon(get_random_pokemon()))


async def setup(bot: commands.Bot):
    try:
        await bot.add_cog(DailyPokemon(bot))
        logger.info("DailyPokemon cog loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load DailyPokemon cog: {e}", exc_info=True)
        raise
