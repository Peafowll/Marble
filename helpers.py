import requests
import json
import os
def find_lol_spells():
    with open("championFull.json", "r", encoding="utf8") as file:
        data=json.load(file)
    abilties = {}
    for champion_name,champion_data in data["data"].items():
        q_name,w_name,e_name,r_name = [champion_data["spells"][n]["name"]  for n in range(4)]
        passive_name = champion_data["passive"]["name"]
        title = champion_data["title"]
        abilties[champion_name] = [title,passive_name,q_name,w_name,e_name,r_name]
    return abilties

def resfresh_ult_json():
    response = requests.get("https://ddragon.leagueoflegends.com/cdn/15.21.1/data/en_US/championFull.json")
    data=response.text
    with open("championFull.json", "w", encoding="utf8") as file:
        file.write(response.text)


find_lol_spells()