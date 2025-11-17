import requests
import json
import os
import logging
from dotenv import load_dotenv
logger = logging.getLogger('discord.helpers')

from match_score_calculator import calculate_int_scores

load_dotenv()
riot_token = os.getenv("RIOT_KEY")


# TODO : str command explanations

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
    
def get_matches_by_player_id(riot_id, queue_name=None, count=20, start=0):
    """
    Gets a list of match IDs based on a player's ID.
    Args:
        riot_id: player's PUUID
        queue_name: the name of a specific queue type. (optional)
        count: number of match IDs to return (default: 20, max: 100)
        start: starting index for pagination (default: 0)
    Returns:
        data
    """
    #POSSIBLE QUEUE TYPES:
        #"Ranked Solo/Duo"
        #"Ranked Flex"
        #"Normal Draft"
        #"Normal Blind"
        #"Normal (Quickplay)"
        #"ARAM"
        #"Clash"
        #"ARAM Clash"
        #"ARURF"
        #"URF"
        #"One for All"
        #"Nexus Blitz"
        #"Ultimate Spellbook"
        #"Arena"
        #"Co-op vs AI Intro"
        #"Co-op vs AI Beginner"
        #"Co-op vs AI Intermediate"
        #"TFT Normal"
        #"TFT Ranked"
        #"Swarm"
    params = {"api_key" : riot_token, "count" : count, "start": start}
    if queue_name:
        queue_id = convert_queue_type_to_id(queue_name)
        if queue_id:
            params["queue"] = queue_id
    try:
        response = requests.get(f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{riot_id}/ids",params=params)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching matches for {riot_id}")
        return []
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            logger.warning("Rate limit hit")
        logger.error(f"HTTP error: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in get_matches_by_player_id: {e}")
        return []
    
    data = response.json()
    return data

def get_match_stats_by_id(match_id):
    """
    Returns a dict of match data based on a match ID.
    """
    try:
        response = requests.get(f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}", params={"api_key": riot_token})
        response.raise_for_status()
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching match stats for {match_id}")
        return []
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            logger.warning("Rate limit hit")
        logger.error(f"HTTP error: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in get_match_stats_by_id: {e}")
        return []
    data = response.json()
    return data 

def get_loses_data_list(riot_id, count = 5, queue_name = None):
    """
    Returns a list of full match data dicts for a player's recent loses.
    
    Args:
        riot_id: Player's PUUID
        count: Number of losses to retrieve (default: 5)
        queue_id: Queue type filter (optional)
    
    Returns:
        List of match data dictionaries
    """
    loses = 0
    loses_list = []
    start_index = 0
    
    while loses < count:
        matches_ids = get_matches_by_player_id(
            riot_id=riot_id,
            queue_name=queue_name,
            count=count,
            start=start_index
        )
        
        if not matches_ids:
            break
            
        for match_id in matches_ids:
            if loses >= count:
                break
            match_data = get_match_stats_by_id(match_id=match_id)

            if not match_data or "info" not in match_data:
                logger.info(f"Skipping match {match_id} - invalid or missing data")
                continue
        

            game_duration = match_data["info"]["gameDuration"]
            if game_duration < 300:
                continue
            player_data = next((p for p in match_data["info"]["participants"] if p["puuid"] == riot_id), None)
            if not player_data["win"]:
                loses+=1
                loses_list.append(match_data)
        
        # Move to the next batch of matches
        start_index += len(matches_ids)

    return loses_list
            
def get_match_int_scores_list(match_data_list, player_pool):
    """
    Returns a list of dicts containing int scores for players across multiple matches.

    Args:
        match_data_list: List of match data dictionaries
        player_pool: List of player names to calculate INT scores for

    Returns:
        list: List of dicts, where each dict contains INT scores for that match.
              Only includes players from player_pool.
        
        Example: 
        >>> get_match_int_scores_list(matches, ["PlayerA", "PlayerB"])
        [{"PlayerA": 890, "PlayerB": 426}, {"PlayerA": 752, "PlayerB": 381}]
    """
    match_scores_list = []

    for match_data in match_data_list:
        int_scores = calculate_int_scores(match_data)
        filtered_scores = {player: score for player, score in int_scores.items() 
                          if player in player_pool}
        if filtered_scores:
            match_scores_list.append(filtered_scores) 
    
    return match_scores_list