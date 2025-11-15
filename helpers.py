import requests
import json
import os
import logging

logger = logging.getLogger('discord.helpers')

def find_lol_spells():
    try:
        with open("championFull.json", "r", encoding="utf8") as file:
            data=json.load(file)
        abilities = {}
        for champion_name,champion_data in data["data"].items():
            try:
                q_name,w_name,e_name,r_name = [champion_data["spells"][n]["name"]  for n in range(4)]
                passive_name = champion_data["passive"]["name"]
                title = champion_data["title"]
                abilities[champion_name] = [title,passive_name,q_name,w_name,e_name,r_name]
            except (KeyError, IndexError) as e:
                logger.warning(f"Missing data for champion {champion_name}: {e}")
                continue
        logger.info(f"Loaded {len(abilities)} champions")
        return abilities
    except FileNotFoundError:
        logger.error("championFull.json not found")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing championFull.json: {e}", exc_info=True)
        return {}
    except Exception as e:
        logger.error(f"Unexpected error in find_lol_spells: {e}", exc_info=True)
        return {}

def resfresh_ult_json():
    try:
        response = requests.get("https://ddragon.leagueoflegends.com/cdn/15.21.1/data/en_US/championFull.json", timeout=10)
        response.raise_for_status()
        data=response.text
        with open("championFull.json", "w", encoding="utf8") as file:
            file.write(response.text)
        logger.info("Successfully refreshed championFull.json")
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while refreshing champion data: {e}", exc_info=True)
    except IOError as e:
        logger.error(f"Error writing championFull.json: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Unexpected error in resfresh_ult_json: {e}", exc_info=True)

def convert_queue_type_to_id(queue_type):
    convert_dict = {
        "Ranked Solo/Duo": 420,
        "Ranked Flex": 440,

        "Normal Draft": 400,
        "Normal Blind": 430,
        "Normal (Quickplay)": 490,
        
        "ARAM": 450,
        
        "Clash": 700,
        "ARAM Clash": 720,
        
        "ARURF": 900,
        "URF": 1900,
        "One for All": 1020,
        "Nexus Blitz": 1300,
        "Ultimate Spellbook": 1400,
        "Arena": 1700,
        
        "Co-op vs AI Intro": 870,
        "Co-op vs AI Beginner": 880,
        "Co-op vs AI Intermediate": 890,
        
        "TFT Normal": 1090,
        "TFT Ranked": 1100,
        
        "Swarm": 1840,
    }
    return convert_dict.get(queue_type)

def convert_queue_aliases_to_queue(queue_alias):
    convert_dict = {
        "Ranked Solo/Duo": ["soloqueue","solo","soloduo","solo/duo","solo_queue","soloq","ranked_solo","ranked_solo/duo","ranked_solo_duo"],
        "Ranked Flex": ["flex","ranked_flex"],
        "Normal Draft": ["normal","normals","draft","draft_pick"],
        "Normal Blind": ["blind","blind_pick","blinds"],
        "Normal (Quickplay)": ["quickplay"],
        "ARAM": ["aram","all_random_all_mid"],
        "Clash": ["clash"],
        "ARAM Clash": ["clash_aram","aram_clash"],
        "ARURF": ["arurf","all_random_urf","all_random_ultra_rapid_fire","ar_ultra_rapid_fire"],
        "URF": ["urf","ultra_rapid_fire"],
        "One for All": ["1fa","ofa","one_for_all"],
        "Nexus Blitz": ["blitz","nexus_blitz"],
        "Ultimate Spellbook": ["spellbook","ulimatespellbook","ultimate_spellbook"],
        "Arena": ["arena"],
        "Co-op vs AI Intro": ["bots_intro","intro_bots"],
        "Co-op vs AI Beginner": ["bots_beginner","beginner_bots"],
        "Co-op vs AI Intermediate": ["bots_intermediate","intermediate_bots"],
        "TFT Normal": ["tft","tft_normal","normal_tft"],
        "TFT Ranked": ["ranked_tft","tft_ranked"],
        "Swarm": ["swarm","vampire_survivors"]
    }
    queue_alias_lower = queue_alias.lower()
    for queue_name,aliases in convert_dict.items():
        if queue_alias_lower in aliases:
            return queue_name
    return None
    