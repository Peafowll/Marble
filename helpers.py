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
        "Ranked Flex" : 440,
        "Ranked Solo/Duo" : 420,
        "ARAM" : 450,
        
    }
