import requests
from dotenv import load_dotenv
import os

load_dotenv()
riot_token = os.getenv("RIOT_KEY")

#correct match : EUN1_3848320574

#TODO : import gold diff at 15 and exp diff at 15

def calculate_int_scores(match_json,match_log_json=None, target_player=None):
    #testers
    # match_id = "EUN1_3848320574"
    # match_json_response = requests.get(f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}", params={"api_key": riot_token})
    # match_json = match_json_response.json()

    # match_log_json_response = requests.get(f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline", params={"api_key": riot_token})
    # match_log_json = match_log_json_response.json()

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
            indiviual_position = participant["individualPosition"]
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
                vision_per_min_baseline = 0.6
                vision_per_min_harshness = 2.2

                gold_per_minute_baseline = 420
                gold_per_minute_harshness = 3.2
            

            vision_int_score = int(1000/(1+(vision_per_min/vision_per_min_baseline)**vision_per_min_harshness))
            gold_int_score = int(1000/(1+(gold_per_minute/gold_per_minute_baseline)**gold_per_minute_harshness))

            #DAMAGE INT VALUE
            damage_per_minute = participant["challenges"]["damagePerMinute"]
            if team_position == "UTILITY":
                damage_per_minute_baseline = 470
                damage_per_minute_harshness = 2.6
            if team_position == "JUNLGE":
                damage_per_minute_baseline = 650
                damage_per_minute_harshness = 2.8
            else:
                damage_per_minute_baseline = 800
                damage_per_minute_harshness = 3.4

            damage_int_score = int(1000/(1+(damage_per_minute/damage_per_minute_baseline)**damage_per_minute_harshness))

            #print(f"""Player has kda_int={kda_int_score} 
            #      vision_int={vision_int_score} 
            #      gold_int = {gold_int_score} 
            #      damage int = {damage_int_score}""")
            
 
            int_score = (kda_int_score + vision_int_score + gold_int_score + damage_int_score)/4
            int_scores[name] = int_score

    #print(f"INT SCORES : ")
    #print(int_scores)
    return int_scores


#purpose : 
# top : tower damage and damage
# jg : kp and objectives
# mid : damage and kp
# adc : damage and cs
# support : kp and vision

if __name__ == "__main__":
    calculate_int_scores("o","i")