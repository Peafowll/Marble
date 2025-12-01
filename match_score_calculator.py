import requests
from dotenv import load_dotenv
import os
import logging

load_dotenv()
riot_token = os.getenv("RIOT_KEY")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def calculate_int_scores(match_json,match_log_json=None, target_player=None):
    """
    Calculate "INT scores" for players in a League of Legends match to identify underperformers.
    
    The INT score is a composite metric (0-1000) that increases with poor performance. It combines:
    - KDA ratio (kills, deaths, assists)
    - Vision score per minute
    - Gold earned per minute  
    - Damage dealt per minute
    
    Position-specific baselines and harshness values are used.
    Higher INT scores indicate worse performance relative to expectations.
    
    Args:
        match_json (dict): Full match data from Riot API (v5/matches/{matchId})
        match_log_json (dict, optional): Match timeline data (currently unused). Defaults to None.
        target_player (str, optional): Only calculate scores if this player lost. 
                                      If provided and player won, returns empty dict. Defaults to None.
    
    Returns:
        dict: Player names mapped to their INT scores (float). Only includes players who lost.
        
    Examples:
        >>> # Match where 5 players lost
        >>> calculate_int_scores(match_data)
        {
            'Peafowl': 456.78,
            'yoyo15': 892.34,
            'vladimus2005': 234.56,
            'Dani': 678.90,
            'PlayerFive': 345.12
        }
        
        >>> # Target player filter - player won, so return empty
        >>> calculate_int_scores(match_data, target_player='Peafowl')
        {}
        
        >>> # Target player filter - player lost, calculate all losing team scores
        >>> calculate_int_scores(match_data, target_player='yoyo15')
        {
            'Peafowl': 456.78,
            'yoyo15': 892.34,  # Highest score = worst performer
            'vladimus2005': 234.56,
            'Dani': 678.90,
            'PlayerFive': 345.12
        }
    
    Note:
        - Only calculates scores for losing players (win == False)
        - Supports get different baselines for vision/gold/damage metrics
        - Scores range from 0 (perfect performance) to 1000 (terrible performance)
        - Score of ~500 represents average/baseline performance
    """
    
    participants = match_json["info"]["participants"]
    int_scores = {}
    game_duration_seconds = match_json["info"]["gameDuration"]
    #print(f"The game lasted {game_duration_seconds} seconds")
    if target_player:
        target_lost = any(p["riotIdGameName"] == target_player and not p["win"] for p in participants)
        if not target_lost:
            return {}
    for participant in participants:
        int_score = 0
        if participant["win"] == False:
            name = participant["riotIdGameName"]
            kills = participant["kills"]
            deaths = participant["deaths"]
            assists = participant["assists"]
            team_position = participant["teamPosition"]

            if deaths == 0:
                kda = kills+assists
            else:
                kda = (kills+assists)/deaths

            kda_baseline = 2
            kda_harshness = 2.8
            kda_int_score = int( 1000 / (1 + (kda / kda_baseline)**kda_harshness) )
            
           # print(f"Detected player {participant["riotIdGameName"]} had a kda of {kda}, indie pos ={indiviual_position}, team pos = {team_position}")

            vision = participant["visionScore"]
            vision_per_min = participant["challenges"]["visionScorePerMinute"]
            gold = participant["goldEarned"]
            gold_per_minute = participant["challenges"]["goldPerMinute"]            

            #VISION & GOLD INT VALUE
            if team_position == "UTILITY":
                vision_per_min_baseline = 1.6
                vision_per_min_harshness = 3.2

                gold_per_minute_baseline = 385
                gold_per_minute_harshness = 2.4

            else:
                vision_per_min_baseline = 0.5
                vision_per_min_harshness = 1.2

                gold_per_minute_baseline = 420
                gold_per_minute_harshness = 3.2
            

            vision_int_score = int(1000/(1+(vision_per_min/vision_per_min_baseline)**vision_per_min_harshness))
            gold_int_score = int(1000/(1+(gold_per_minute/gold_per_minute_baseline)**gold_per_minute_harshness))

            #DAMAGE INT VALUE
            damage_per_minute = participant["challenges"]["damagePerMinute"]
            if team_position == "UTILITY":
                damage_per_minute_baseline = 470
                damage_per_minute_harshness = 2.6
            if team_position == "JUNGLE":
                damage_per_minute_baseline = 650
                damage_per_minute_harshness = 2.8
            else:
                damage_per_minute_baseline = 800
                damage_per_minute_harshness = 3.4

            damage_int_score = int(1000/(1+(damage_per_minute/damage_per_minute_baseline)**damage_per_minute_harshness))


            #KP INT VALUE
            kill_participation = round(participant["challenges"]["killParticipation"]*10,2)
            
            kill_participation_baseline = 47
            print(f"kill participation ={kill_participation}")
            if team_position in ["UTILITY","JUNGLE"]:
                kill_participation_harshness = 3.4
            else:
                kill_participation_harshness = 2.8

            kill_participation_score = int(1000/(1+(kill_participation/kill_participation_baseline)**kill_participation_harshness))

            int_score = (kda_int_score + vision_int_score + gold_int_score + damage_int_score+kill_participation_score)/5
            
            # Log the blame score breakdown
            logger.info(f"{name} ({team_position}): INT={int_score:.1f} | KDA={kda_int_score} Vision={vision_int_score} Gold={gold_int_score} Damage={damage_int_score} KP={kill_participation_score}")
            
            int_scores[name] = int_score
  
    return int_scores


#purpose : 
# top : tower damage and damage
# jg : kp and objectives
# mid : damage and kp
# adc : damage and cs
# support : kp and vision

if __name__ == "__main__":
    calculate_int_scores("o","i")