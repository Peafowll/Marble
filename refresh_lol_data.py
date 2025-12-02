import requests
import json
import logging

logger = logging.getLogger('discord.refresh_lol_data')
try:
    response = requests.get("https://ddragon.leagueoflegends.com/api/versions.json", timeout=10)
    data = response.json()
    latest_patch = data[0]
except requests.exceptions.RequestException as e:
    logger.error(f"Network error while finding the latest LoL patch: {e}", exc_info=True)
except Exception as e:
    logger.error(f"Unexpected error in finding the most recent LoL patch : {e}", exc_info=True)


try:
    response = requests.get(f"https://ddragon.leagueoflegends.com/cdn/{latest_patch}/data/en_US/championFull.json", timeout=10)
    response.raise_for_status()
    data=response.text
    with open("static/championFull.json", "w", encoding="utf8") as file:
        file.write(data)
    logger.info("Successfully refreshed championFull.json")

    champion_data = json.loads(data)

    try: 
        with open("static/championAliases.json", "r", encoding="utf8") as f:
            aliases = json.load(f)
    except FileNotFoundError:
        aliases = {}
        logger.info("championAliases.json not found, creating new file")

    new_champs = []
    for champ_id, champion_info in champion_data["data"].items():
        champ_name = champion_info["id"]
        if champ_name not in aliases:
            aliases[champ_name] = [champ_name.lower()]
            new_champs.append(champ_name)
    
    with open("static/championAliases.json", "w", encoding="utf8") as f:
        json.dump(aliases, f, indent=4, ensure_ascii=False)
    
    if new_champs:
        logger.info(f"Added {len(new_champs)} new champion(s) to championAliases.json: {', '.join(new_champs)}")
    else:
        logger.info("No new champions to add to championAliases.json")

except requests.exceptions.RequestException as e:
    logger.error(f"Network error while refreshing champion data: {e}", exc_info=True)
except IOError as e:
    logger.error(f"Error writing championFull.json: {e}", exc_info=True)
except Exception as e:
    logger.error(f"Unexpected error in resfresh_ult_json: {e}", exc_info=True)
