"""
Configuration file for the Marble Discord bot.
Contains constants and configuration data used across different cogs.
"""

# Discord Server and Channel IDs
MARBLE_CHANNEL_ID = 1445025916802568222
DAG_ROLE_ID = 1443876656111685652
YKTP_GUILD_ID = 890252683657764894

# API Configuration
API_REQUEST_TIMEOUT = 10  # seconds


#TITLES.PY CONFIGS:

# DAG Team Members Configuration
DAG_MEMBERS = {
    "peafowl": {
        "riot_name": "Peafowl",
        "riot_tag": "EUNE",
        "hv_id": "64792ac3-0873-55f5-9348-725082445eef"
    },
    "yoyoo0722": {
        "riot_name": "yoyo15",
        "riot_tag": "EUNE",
        "riot_id": "zy4F2oQ6IXGNMCOJKlUj7gN_ML4tW43zMxECvtD6m2EJCs1JX_fFCiJfR8cQjgJWGp5VbgB4WsCmhg",
        "hv_id": "7f15608b-dd61-564f-9e1a-94a4936b08f9"
    },
    "vladimus2005": {
        "riot_name": "vladimus2005",
        "riot_tag": "EUNE",
        "riot_id": "E6rjy-vG9AMa_dp1HWePQBsJKPwcw36C-JDOyGWJgqw1GQM89t_u39ZPA4KNjWD965mJJrGAYiQxNQ",
        "hv_id": "c08f6c44-378c-5c82-8ce1-d12f33a0264e"
    },
    "arrow_san": {
        "riot_name": "Dani",
        "riot_tag": "EUNE1",
        "riot_id": "lP2icP8VVAMMRnOHlEnFROqdEbd205nRtwD3vOzGZQVsErNjJp5iinXUlxcaZfLJcxpCrRchqPZGow",
        "hv_id": "7ff1ac69-8901-5634-a4ea-26684d52d9e9"
    },
    "painite01": {
        "riot_name": "Painite",
        "riot_tag": "4349",
        "riot_id": "w-bK59spgQkicdzS2WgHp8edRn5MG0lhYdHtYPj5OkEa3JQ0Pow31lsFtSTM34_rGi-nLtpxRZS9-w",
        "hv_id": "1c8ee468-4a77-5f18-b2c3-2016e0c74bba"
    }
}

# Player Emojis
DAG_EMOJIS = {
    "Painite": "💎",
    "Peafowl": "🦚",
    "vladimus2005": "🪩",
    "Dani": "🎯",
    "yoyo15": "🤙"
}

# Valorant Weapon Categories
WEAPON_CATEGORIES = {
    "pistols": ["Classic", "Frenzy", "Sheriff", "Ghost"],
    "smgs": ["Stinger", "Spectre"],
    "shotguns": ["Shorty", "Judge", "Bucky"],
    "snipers": ["Marshall", "Outlaw", "Operator"],
    "lmgs": ["Ares", "Odin"],
    "rifles": ["Bulldog", "Phantom", "Vandal", "Guardian"],
    "knives": ["Knife", "Melee"]
}

# Title Assignment Configuration
TITLE_ASSIGNMENT_THRESHOLD = 0.3  # Max range of z-scores between titles

# Kill Distance Ranges (in meters)
SHORT_RANGE_THRESHOLD = 7.5
LONG_RANGE_THRESHOLD = 34.0