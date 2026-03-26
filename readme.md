# Marble, Personal Discord Bot
A multi-feature Discord bot focused on League of Legends, Valorant, and community fun. Marble mixes game stats, trivia, daily Pokemon, and voice activity tracking. Most features are implemented as Discord cogs under `cogs/` and loaded automatically.


## What This Project Does
- League of Legends tools:
  - `!blame` analyzes recent losses and performance using a custom INT score model.
  - `!ranked_report` generates a ranked status report for registered players.
  - `!loltrivia` runs a LoL trivia game with leaderboards.
- Valorant tools:
  - Match report + title attribution for DAG team matches via HenrikDev API. (DAG being the Valorant team me and my friends play in)
- Pokemon tools:
  - Daily Pokemon DMs with ratings and a top-rated list.
- Community tools:
  - Voice activity tracking with weekly reports.
  - Random team generator for voice channel members.
- Utility:
  - Built-in changelog command and bot status updates.


## Key Features (By Cog)
- `activity.py`
  - Tracks voice state changes, builds daily stats, and sends weekly leaderboards.
  - Owner-only commands for manual saves and previews.
- `blamer.py`
  - Player registration and loss analysis for LoL using Riot API.
  - Solo queue blame scoring + flex games blame attribution.
- `daily_pokemon.py`
  - Daily Pokemon message with custom embed featuring stats, evolution line, and ratings via PokeAPI.
  - Subscriber management and top-rated list.
- `games.py`
  - LoL trivia game with difficulty modes and leaderboards.
- `random_teams.py`
  - Random team generator from the current voice channel.
  - Custom message commands to fine-tune the generation process.
- `ranked.py`
  - Ranked report across registered players, featuring a custom Embed with hot/cold streaks and history previews.
- `titles.py`
  - Valorant match report, title attribution, and detailed stat logging.


## Commands (User-Facing)
- `!hi`
- `!changelog [major|minor|patch|all]`
- `!register <riot_name#tag>`
- `!blame [match_count] [queue]`
- `!ranked_report`
- `!loltrivia`
- `!loltlb [difficulty] [count]`
- `!random_teams`
- `!sub_pokemon`
- `!unsub_pokemon`
- `!best_mons [count]`

## Data and Storage
This bot writes persistent data under `data/`:
- `players.json` (Riot registrations)
- `voicePresences.json`, `dailyPresences.json` (voice activity)
- `loltriviaLeaderboards.json` (trivia scores)
- `dailyPokemonSubscribers.json`, `dailyPokemonRatings.json` (Pokemon feature)
- Static logs are written to `static/` for Valorant title attribution and stats.

## APIs used
- Discord API via `discord.py`
- Riot API (LoL) via REST
- PokeAPI for Pokemon data
- Data Dragon (LoL champion data)
- HenrikDev API for Valorant match data



## Setup
1. Create and activate a Python virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with:

   ```env
   BOT_TOKEN=your_discord_bot_token
   RIOT_KEY=your_riot_api_key
   HD_KEY=your_henrikdev_api_key
   ```
4. Run the bot:
   ```bash
   python bot.py
   ```


## Scripts and Utilities
- `refresh_lol_data.py` downloads the latest LoL champion data and updates aliases.
- `tools/get_last_game_int_scores.py` prints detailed INT scores for a player.


## Project Structure
- `bot.py` bootstraps the bot and loads cogs.
- `config.py` central configuration/constants.
- `helpers.py` shared Riot/LoL helper functions.
- `match_score_calculator.py` INT score calculation.
- `cogs/` feature modules.
- `data/` JSON data storage.
- `static/` logs for Valorant match reporting.


## Notes / Gotchas
- The bot expects certain JSON files to exist in `data/`. The cogs create missing files on first run.
- Riot API rate limiting is handled in some cogs, but large requests can still be slow.
- The Valorant features require `HD_KEY` and expect DAG member IDs in `config.py`.
