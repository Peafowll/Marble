import discord
from discord.ext import commands
from discord.ui import Button, View
import random
import json
import asyncio
import time, datetime
import logging
from dotenv import load_dotenv
import os
import requests
from match_score_calculator import calculate_int_scores
from helpers import convert_queue_aliases_to_queue
from helpers import get_loses_data_list, get_match_int_scores_list
load_dotenv()
riot_token = os.getenv("RIOT_KEY")

# TODO : reformat the !mass_register command by hand anEd by using a register function called my both !register and !mass_register

# TODO : polish polish polish

# TODO : caching

logger = logging.getLogger('discord.blamer')

    
def get_player_pool():
    """
    Gets the pool of players registered with the !register commands, from the players.json file.
    Returns:
        A dict of players, of type `discord_name = {"riot_name": riot_name,"riot_tag": "EUNE","riot_id": id}`
    """
    filepath = "players.json"
    if not os.path.exists(filepath):
        with open(filepath,"w",encoding="utf8") as file:
            json.dump({}, file)
        logger.warning("Created missing players.json file")
    
    try:
        with open("players.json", "r" ,encoding="utf8") as file:
            players = json.load(file)
        logger.debug(f"Loaded {len(players)} players from pool")
        return players
    except Exception as e:
        logger.error(f"Error loading player pool: {e}")
        return {}

def get_player_pool_names():
    """
    Gets the riot names of all players in the pool.
    Returns:
        List of names.
    """
    pool = get_player_pool()
    names = []
    for player in pool:
        names.append(pool[player]["riot_name"])
    logger.debug(f"Retrieved {len(names)} player names from pool")
    return names

def find_inters(list_of_int_scores):
    """
    Looks at a set of int scores and finds the players most often inting the games.
    Args:
        list_of_int_scores : a list of dicts that contain int scores.
    Returns:

    """
    logger.debug(f"Analyzing {len(list_of_int_scores)} matches for inter detection")
    if len(list_of_int_scores) == 0:
        logger.warning("No int scores provided to find_inters")
        return None, None
    worst_player_frequency = {}
    total_int_scores = {}
    game_count = {}
    for int_scores in list_of_int_scores: # Go through all the games
        biggest_score = -1
        biggest_inter = None
        for player in int_scores:
            if int_scores[player] >= biggest_score: #Find biggest int score this game
                biggest_score = int_scores[player]
                biggest_inter = player
            
            if player not in total_int_scores: #Add the average int score of the player
                total_int_scores[player] = int_scores[player]
                game_count[player] = 1
            else:
                total_int_scores[player] += int_scores[player]
                game_count[player] += 1

        if biggest_inter not in worst_player_frequency:
            worst_player_frequency[biggest_inter] = 1
        else:
            worst_player_frequency[biggest_inter] +=1

    average_int_scores = {}
    for player in total_int_scores:
        average_int_scores[player] = total_int_scores[player] / game_count[player]
    
    most_frequent_worst_player = max(worst_player_frequency, key=worst_player_frequency.get)
    highest_average_int_score_player = max(average_int_scores, key=average_int_scores.get)
    
    logger.info(f"Most frequent worst: {most_frequent_worst_player} ({worst_player_frequency[most_frequent_worst_player]} times)")
    logger.info(f"Highest avg INT: {highest_average_int_score_player} ({average_int_scores[highest_average_int_score_player]:.1f})")
        
    return most_frequent_worst_player, highest_average_int_score_player
        
def get_solo_duo_avg_blame_percent(match_data_list, playerOne, playerTwo = None):
    logger.debug(f"Calculating blame percentage for {playerOne} across {len(match_data_list)} matches")
    match_count = 0
    percentages = []
    if not match_data_list:  # ADD THIS
        logger.warning(f"No match data for {playerOne}")
        return 0, []
    for match_data in match_data_list:
        randoms_int = 0
        personal_int = 0
        match_count+=1
        int_scores = calculate_int_scores(match_data)
        for player in int_scores:
            if player == playerOne:
                personal_int += int_scores[player]
            else:
                randoms_int += int_scores[player]
        total_int = randoms_int + personal_int
        percentage = (personal_int/total_int)*100
        percentages.append(percentage)

    average_percentages = sum(percentages)/match_count
    logger.info(f"{playerOne} avg blame percentage: {average_percentages:.1f}%")
    return  average_percentages,percentages

def get_solo_duo_avg_position(match_data_list,playerOne,playerTwo = None):
    """
    Calculate a player's average position ranking across multiple matches based on INT scores.
    
    For each match, ranks all 5 losing players by their INT score (1 = best performer/lowest INT,
    5 = worst performer/highest INT) and tracks where the target player placed.
    
    Args:
        match_data_list (list): List of match data dictionaries from get_loses_data_list()
        playerOne (str): Riot ID of the target player to analyze
        playerTwo (str, optional): Currently unused. Reserved for future duo analysis. Defaults to None.
    
    Returns:
        tuple: (average_position, positions_list)
            - average_position (float): Mean position across all matches (1.0 = always best, 5.0 = always worst)
            - positions_list (list): Individual position for each match (1-5)
    
    Examples:
        >>> # Player who consistently performed worst
        >>> get_solo_duo_avg_position(matches, "BadPlayer")
        (4.6, [5, 5, 4, 5, 4])
        
        >>> # Player who consistently performed best
        >>> get_solo_duo_avg_position(matches, "GoodPlayer")
        (1.4, [1, 2, 1, 1, 2])
        
        >>> # Average performer
        >>> get_solo_duo_avg_position(matches, "OkayPlayer")
        (3.0, [3, 2, 4, 3, 3])
    
    Note:
        - Position 1 = lowest INT score = best performance in the loss
        - Position 5 = highest INT score = worst performance in the loss
        - Only analyzes the 5 players on the losing team
    """
    logger.debug(f"Calculating position for {playerOne} across {len(match_data_list)} matches")
    match_count = 0
    positions = []
    if not match_data_list:  # ADD THIS
        logger.warning(f"No match data for {playerOne}")
        return 0, []
    for match_data in match_data_list:
        randoms_int = 0
        personal_int = 0
        match_count+=1
        int_scores = calculate_int_scores(match_data)
        sorted_players = sorted(int_scores,key=int_scores.get)
        for i, player in enumerate(sorted_players):
            if player == playerOne:
                place = i + 1
        positions.append(place)

    average_pos= sum(positions)/match_count
    logger.info(f"{playerOne} avg position: {average_pos:.2f}/5")

    return  average_pos,positions

class Blamer(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    @commands.command(aliases=['whydidwelose'])
    @commands.cooldown(1, 15, commands.BucketType.guild) 
    async def blame(self,ctx,match_count:int = 5 ,queue:str = "Flex"):
        """
        See who's fault it was you lost your previous games!
    
        This command DOES NOT LOOK AT *ANY* WINS.

        When using this command for any queue type that isn't Ranked Solo/Duo, it will look at all the registered players and tell you who lost you your games out of those.
        Be careful! This means if someone is not registered, they can't be blamed!
        This also means if you're the only registered player, it will always blame you =).

        When using this commad for Ranked Solo/Duo, it will instead tell you if, overall, your last ranked games loses were your fault or your team's faults.

        Usage: !blame [match_count] [queue]
        - match_count : how many of your most recent losses you want to look at. (default = 5, max = 25)
                        Be CAREFUL! Big requests will take ages, so limit yourself to around 10 games!
        - queue : the queue type you want to look at (ex : flex, solo/duo etc.)
        
        - Example : !blame 5 Flex
        """
        logger.info(f"Blame command invoked by {ctx.author.name} in {ctx.guild.name if ctx.guild else 'DM'}: {match_count} matches, queue={queue}")
        author_name = ctx.author.name
        registered_players = get_player_pool()

        if author_name not in registered_players:
            logger.warning(f"Unregistered user {author_name} attempted to use blame command")

            await ctx.send(f"❌ {author_name} is not registered! Use `!register` first.")
            return
        author_riot_id = registered_players[author_name]["riot_id"]
        author_riot_name = registered_players[author_name]["riot_name"]

        queue_correct_name = convert_queue_aliases_to_queue(queue)
        if not queue_correct_name:
            logger.warning(f"Invalid queue type provided: {queue}")
            await ctx.send("Invalid queue type.")
            return
        
        logger.debug(f"Queue alias '{queue}' resolved to '{queue_correct_name}'")
        
        if match_count < 1 :
            logger.warning(f"Invalid match count: {match_count}")
            await ctx.send("Please ask for at least one match. ")
            return
        if match_count > 25:
            logger.info(f"Match count {match_count} capped at 25")
            match_count = 25
            await ctx.send("The match has been capped at 25 to avoid long wait times.")

        if not queue_correct_name == "Ranked Solo/Duo":
            proccesing_text = f"🔍 Let's see who lost you your last **{match_count}** {queue_correct_name} games...\n⌛ *This may take a moment.*"
            proccesing_message = await ctx.send(proccesing_text)
            async with ctx.typing():
                loss_data = get_loses_data_list(riot_id=author_riot_id,count=match_count,queue_name=queue_correct_name)
                logger.info(f"Retrieved {len(loss_data)} losses for {author_name}")
                
                if match_count > len(loss_data):
                    logger.info(f"Requested {match_count} matches but only found {len(loss_data)}")
                    await ctx.send(f"ℹ️ Only found {len(loss_data)} matches.")
                
                player_pool = get_player_pool_names()
                list_of_int_scores = get_match_int_scores_list(loss_data, player_pool)
                logger.debug(f"Calculated INT scores for {len(list_of_int_scores)} matches")
                
                frequent_inter, worst_average_inter = find_inters(list_of_int_scores)

            await proccesing_message.delete()
            if not frequent_inter or not worst_average_inter:
                await ctx.send(f"❓ No registered players were in your {queue_correct_name} losses.")
                logger.warning(f"No registered players found in last {match_count} {queue_correct_name} losses of {author_name}")
                return

            if frequent_inter != worst_average_inter:
                logger.info(f"Flex blame result: frequent={frequent_inter}, worst_avg={worst_average_inter}")
                await ctx.send(
                f"Overall, the person who's lost you the most matches was **{frequent_inter}**, "
                f"while **{worst_average_inter}** played the worst on average during your losses.")
            else:
                logger.info(f"Flex blame result: {worst_average_inter} was both frequent and worst average")
                await ctx.send(f"Sheesh! **{worst_average_inter}** lost you your last {match_count} games.")
        else:
            proccesing_text = f"🔍 Let's see if you or your team are to blame for your last {match_count} soloQ losses...\n⌛ *This might take a while.*"
            proccesing_message = await ctx.send(proccesing_text)

            async with ctx.typing():
                loss_data = get_loses_data_list(riot_id=author_riot_id,count=match_count,queue_name=queue_correct_name)
                logger.info(f"Retrieved {len(loss_data)} solo queue losses for {author_name}")
                
                if match_count > len(loss_data):
                    logger.info(f"Requested {match_count} matches but only found {len(loss_data)}")
                    await ctx.send(f"ℹ️ Only found {len(loss_data)} matches.")
                
                avg_percentage, percentages = get_solo_duo_avg_blame_percent(loss_data,author_riot_name)
                avg_pos , poses = get_solo_duo_avg_position(loss_data,author_riot_name)

                percentage_score = ((avg_percentage - 15) / 10) * 40
                position_score = (avg_pos / 4) * 60
                blame_score = percentage_score + position_score
                
                logger.info(f"Solo blame calculated: score={blame_score:.1f}, avg_pos={avg_pos:.2f}, avg_pct={avg_percentage:.1f}%")

            blame_thresholds = [
            (70, "💀", "Yeah, it was definitely your fault.", "You were the main problem in these losses."),
            (60, "💧", "Mostly your fault.", "You contributed significantly to these losses."),
            (40, "😐", "About equal blame.", "You and your teammates share the responsibility."),
            (30, "😅", "Your team lost you your games.", "Your team held you back more than you held them back."),
            (0, "🙏", "Team gap.", "These losses were NOT on you.")
            ]

            await proccesing_message.delete()

            message = ""
            for threshold, emoji, verdict, advice in blame_thresholds:
                if blame_score >= threshold:
                    message = f"{emoji} **{verdict}** *{advice}*"
                    logger.info(f"Solo blame verdict for {author_name}: {verdict} (score={blame_score:.1f})")
                    break
            if message:
                await ctx.send(message)
            else:
                logger.error(f"Unable to calculate blame score for {author_name}")
                await ctx.send("Oops! Unable to calculate blame score.")

    

    @commands.command(aliases=["riotsregister"])
    async def register(self, ctx, *, username = None):
        """
        Registers your discord account to a Riot account.
        Usage : !register [riot username]#[riot tag]

        Example : !register HideOnBush#KR
        Example : !register clover chance#77777
        """
        logger.info(f"Register command invoked by {ctx.author.name} for username: {username}")
        
        if not username:
            logger.warning(f"Registration attempted by {ctx.author.name} with no username")
            await ctx.send("❌ Please provide a username!")
            return
        if "#" not in username:
            logger.warning(f"Registration attempted with invalid format: {username}")
            await ctx.send("❌ The username provided doesn't have the correct structure. Try the structure `username#tag`!")
            return
        # Split from the right to handle spaces in riot names
        playername, tag = username.rsplit("#", 1)
        logger.debug(f"Parsed registration request: {playername}#{tag}")

        try:
            logger.debug(f"Fetching Riot account data for {playername}#{tag}")
            response = requests.get(f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{playername}/{tag}",
                                params={"api_key": riot_token}, timeout=10)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching profile for {playername}#{tag}")
            await ctx.send("❌ Request timed out. Please try again.")
            return
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.warning("Rate limit hit during registration")
                await ctx.send("❌ Rate limit reached. Please try again in a moment.")
            elif e.response.status_code == 404:
                logger.warning(f"Riot account not found: {playername}#{tag}")
                await ctx.send(f"❌ Riot account **{playername}#{tag}** not found.")
            else:
                logger.error(f"HTTP error during registration: {e}")
                await ctx.send("❌ Error contacting Riot API. Please try again.")
            return
        except Exception as e:
            logger.error(f"Unexpected error in register: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again.")
            return

        data = response.json()
        author_name = ctx.author.name
        player_dict = {}
        player_dict = {
            "riot_name" : data["gameName"],
            "riot_tag" : data["tagLine"],
            "riot_id" : data["puuid"]
        }

        with open("players.json", "r", encoding="utf8") as file:
            players_dict = json.load(file)

        if author_name in players_dict.keys():
            logger.warning(f"{author_name} attempted to register but is already registered")
            await ctx.send(f"{ctx.author.mention}, you have already registered an account.")
            return
        
        for discord_name, existing_player in players_dict.items():
            if existing_player.get("riot_id") == player_dict["riot_id"]:
                logger.warning(f"{author_name} attempted to register {playername}#{tag} but it's already linked to {discord_name}")
                await ctx.send(f"{ctx.author.mention}, this Riot account is already registered to another user.")
                return

        players_dict[author_name] = player_dict
        with open("players.json","w",encoding="utf8") as file:
            json.dump(players_dict,file,indent=4)
        
        logger.info(f"Successfully registered {author_name} to Riot account {playername}#{tag} (PUUID: {player_dict['riot_id']})")
        await ctx.send(f"{ctx.author.mention}, we have linked you to account **{playername}**#{tag}.")

    @commands.command(aliases=["mass_register"], hidden=True)
    @commands.is_owner()
    async def massregister(self, ctx, *, users_data: str = None):
        """
        Mass register multiple users at once. Owner only.
        Usage: !massregister
            discord_name1 riotname1#tag1
            discord_name2 riotname2#tag2
            ...
        
        Example: !massregister
                JohnDoe PlayerOne#NA1
                JaneSmith PlayerTwo#EUW
        """
        logger.info(f"Mass register command invoked by {ctx.author.name} in {ctx.guild.name if ctx.guild else 'DM'}")
        
        if not users_data:
            logger.warning("Mass register attempted with no data")
            await ctx.send("❌ Please provide user data in the format:\n`discord_name riotname#tag` (one per line)")
            return
        
        with open("players.json", "r", encoding="utf8") as file:
            players_dict = json.load(file)
        
        lines = users_data.strip().split('\n')
        logger.info(f"Processing {len(lines)} registration lines")
        success_count = 0
        failed = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for # to split discord name from riot username
            if "#" not in line:
                failed.append(f"❌ Invalid format (no #): `{line}`")
                continue
            
            # Split on the first space to get discord name, then parse riot username#tag
            if " " not in line:
                failed.append(f"❌ Invalid format (no space): `{line}`")
                continue
            
            discord_name, riot_username = line.split(" ", 1)
            discord_name = discord_name.strip()
            riot_username = riot_username.strip()
            
            # Split riot username on the last # to get name and tag
            playername, tag = riot_username.rsplit("#", 1)
            playername = playername.strip()
            tag = tag.strip()
            
            if discord_name in players_dict:
                failed.append(f"⚠️ {discord_name}: Already registered")
                continue
            
            try:
                logger.debug(f"Mass register: Fetching {playername}#{tag} for {discord_name}")
                response = requests.get(
                    f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{playername}/{tag}",
                    params={"api_key": riot_token},
                    timeout=10
                )
                
                if response.status_code != 200:
                    logger.warning(f"Mass register: Riot account not found for {discord_name}: {playername}#{tag}")
                    failed.append(f"❌ {discord_name}: Riot account not found")
                    continue
                
                data = response.json()
                
                riot_id = data["puuid"]
                already_registered = False
                for existing_player in players_dict.values():
                    if existing_player.get("riot_id") == riot_id:
                        logger.warning(f"Mass register: {playername}#{tag} already registered")
                        failed.append(f"❌ {discord_name}: Riot account already registered")
                        already_registered = True
                        break
                
                if already_registered:
                    continue
                
                players_dict[discord_name] = {
                    "riot_name": data["gameName"],
                    "riot_tag": data["tagLine"],
                    "riot_id": riot_id
                }
                success_count += 1
                logger.info(f"Mass register: Successfully added {discord_name} -> {playername}#{tag}")
                
            except Exception as e:
                logger.error(f"Mass register error for {discord_name}: {e}")
                failed.append(f"❌ {discord_name}: Error - {str(e)}")
        
        if success_count > 0:
            with open("players.json", "w", encoding="utf8") as file:
                json.dump(players_dict, file, indent=4)
            logger.info(f"Mass register: Saved {success_count} new registrations to players.json")
        
        result_msg = f"**Mass Registration Complete**\n✅ Successfully registered: {success_count}\n"
        if failed:
            result_msg += f"❌ Failed: {len(failed)}\n\n" + "\n".join(failed[:10])
            if len(failed) > 10:
                result_msg += f"\n... and {len(failed) - 10} more"
        
        logger.info(f"Mass register complete: {success_count} success, {len(failed)} failed")
        await ctx.send(result_msg)

    @commands.command(aliases=["wholepool"],hidden=True)
    @commands.is_owner()
    async def allplayers(self,ctx, command = False):
        players = get_player_pool()
        player_message = ""
        mass_register_command = "!massregister\n"
        for player in players: 
            individual = players[player]
            individual_message = f"**{player}** *discord account* is linked to **{individual["riot_name"]}#{individual["riot_tag"]}**\n"
            individual_command = f"{player} {individual["riot_name"]}#{individual["riot_tag"]}\n"
            mass_register_command+= individual_command
            player_message+=individual_message
        if player_message == "":
            await ctx.send("Player message empty.")
            return
        await ctx.send(player_message)
        if command == True:
            await ctx.send(f"==== THE MASS REGISTER COMMAND IS : ============")
            await ctx.send(mass_register_command)
            await ctx.send(f"================================================")
        

async def setup(bot):
    try:
        await bot.add_cog(Blamer(bot))
    except Exception as e:
        raise e
