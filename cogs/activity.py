import discord
from discord.ext import commands, tasks
from discord.member import Member
from discord import VoiceState
import json
import datetime
import logging
import os
import copy

# Logger and constants
logger = logging.getLogger('discord.activity')
MAX_DAYS_SAVED = 100


# ============================================================================
# Data Classes
# ============================================================================

class VoiceActivity:
    def __init__(self, member : Member,  before : VoiceState, after : VoiceState):
        """
        Represents an instance of a user's VoiceState changing.

        Attributes
        ------------
        activity_type: :class:`str`
            Indicates the type of change in state that took place.
            
            Options: ``"connect"``, ``"disconnect"``, ``"mute"``, ``"unmute"``, 
            ``"deaf"``, ``"undeaf"``, ``"switch"``, ``"afk"``, or ``"unknown"``.
        discord_name: :class:`str`
            The discord username of the user.
        before_channel_name: :class:`str`
            The name of the channel the user left.
        after_channel_name: :class:`str`
            The name of the channel the user joined.
        timestamp: :class:`datetime`
            Represents the timestamp of when the activity took place.
        """
        self.discord_name = member.name
        self.before_channel_name = before.channel.name if before.channel else None
        self.after_channel_name = after.channel.name if after.channel else None
        self.activity_type = self.detect_activity_type(before, after)
        self.timestamp = datetime.datetime.now()

    def detect_activity_type(self, before : VoiceState, after : VoiceState):
        """
        Determine the type of activity that occurred based on voice state changes.
        
        Parameters
        ----------
        before : VoiceState
            The user's voice state before the change.
        after : VoiceState
            The user's voice state after the change.
            
        Returns
        -------
        str
            The activity type: "connect", "disconnect", "mute", "unmute",
            "deaf", "undeaf", "switch", "afk", or "unknown".
        """
        if after.afk:
            return "afk"
        if (before is None or not before.channel) and after.channel:
            return "connect"
        if before is None:
            return "unknown"
        if before.channel and not after.channel:
            return "disconnect"
        if (not before.deaf and after.deaf) or (not before.self_deaf and after.self_deaf):
            return "deaf"
        if (before.deaf and not after.deaf) or (before.self_deaf and not after.self_deaf):
            return "undeaf"
        if (not before.mute and after.mute) or (not before.self_mute and after.self_mute):
            return "mute"
        if (before.mute and not after.mute) or (before.self_mute and not after.self_mute):
            return "unmute"
        if before.channel != after.channel and (before.channel and after.channel):
            return "switch"
        return "unknown"
    
    def __str__(self):
        return f"{self.discord_name} - {self.activity_type} - {self.before_channel_name} -> {self.after_channel_name}"


class VoicePresence:
    """
    Represents a period of time in which a member was active in a voice chat.

    Attributes
    ------------
    discord_name: :class:`str`
        The name of the user.
    timestamp_start: :class:`datetime`
        The timestamp at which the presence began.
    timestamp_end: :class:`datetime`
        The timestamp at which the presence ended.
    total_time: :class:`datetime`
        How long (in seconds) the presence lasted.
    channel_name: class:`str`
        The name of the channel the user was present in.
    """
    def __init__(self, discord_name: str, timestamp_start: datetime.datetime, timestamp_end: datetime.datetime, channel_name: str, present : bool):
        self.discord_name = discord_name
        self.timestamp_start = timestamp_start
        self.timestamp_end = timestamp_end
        self.total_time = (self.timestamp_end - self.timestamp_start).total_seconds()
        self.channel_name = channel_name
        self.present = present

    @classmethod
    def get_presence_from_activities(clss, activity1 : VoiceActivity, activity2 : VoiceActivity):
        """
        Create a VoicePresence from two consecutive VoiceActivity instances.
        
        Parameters
        ----------
        activity1 : VoiceActivity
            The first (earlier) activity.
        activity2 : VoiceActivity
            The second (later) activity.
            
        Returns
        -------
        VoicePresence
            A presence object representing the period between the two activities.
        """
        if activity1.activity_type in ["disconnect", "deaf", "mute", "afk"]:
            return clss(
                discord_name = activity1.discord_name,
                timestamp_start = activity1.timestamp,
                timestamp_end = activity2.timestamp,
                channel_name = activity1.after_channel_name,
                present = False
            )
        else:
            return clss(
                discord_name = activity1.discord_name,
                timestamp_start = activity1.timestamp,
                timestamp_end = activity2.timestamp,
                channel_name = activity1.after_channel_name,
                present = True
            )

    def to_dict(self):
        """
        Convert the VoicePresence to a dictionary for JSON serialization.
        
        Returns
        -------
        dict
            Dictionary representation of the presence.
        """
        return {
            "discord_name": self.discord_name,
            "timestamp_start": self.timestamp_start.isoformat(),
            "timestamp_end": self.timestamp_end.isoformat(),
            "total_time": self.total_time,
            "channel_name": self.channel_name,
            "present": self.present
        }
    
    @classmethod
    def from_dict(cls, data):
        """
        Create a VoicePresence instance from a dictionary.
        
        Parameters
        ----------
        data : dict
            Dictionary containing presence data.
            
        Returns
        -------
        VoicePresence
            A new VoicePresence instance.
        """
        return cls(
            discord_name=data["discord_name"],
            timestamp_start=datetime.datetime.fromisoformat(data["timestamp_start"]),
            timestamp_end=datetime.datetime.fromisoformat(data["timestamp_end"]),
            channel_name=data["channel_name"],
            present=data["present"]
        )

    def __str__(self):
        return(f"Name : {self.discord_name}- PRESENT={self.present}, from {self.timestamp_start} to {self.timestamp_end} ({self.total_time}), in {self.channel_name}")


# ============================================================================
# Main Cog
# ============================================================================

class Activity(commands.Cog):
    """
    Discord cog for tracking voice channel activity and presence.
    
    This cog monitors user voice state changes, tracks time spent in voice channels,
    and maintains historical presence data with automatic persistence.
    """
    
    def __init__(self,bot):
        """
        Initialize the Activity cog.
        
        Parameters
        ----------
        bot : commands.Bot
            The Discord bot instance.
        """
        self.bot = bot
        self.voice_presences = {}
        self.user_last_activity = {}
        self._artificial_connects_created = False

    # ------------------------------------------------------------------------
    # Lifecycle methods
    # ------------------------------------------------------------------------

    async def cog_load(self):
        """Called when the cog is loaded."""
        logger.info("Activity cog loaded.")

    @commands.Cog.listener()
    async def on_ready(self):
        """
        Called when the bot is ready.
        
        Loads saved presences, creates artificial connects for users already
        in voice channels, and starts all background tasks.
        """
        self.load_presences()
        await self.create_artificial_connects()
        if not self.auto_save_presences.is_running():
            self.auto_save_presences.start()
        if not self.get_daily_presence.is_running():
            self.get_daily_presence.start()

    def cog_unload(self):
        """
        Called when the cog is unloaded.
        
        Creates artificial disconnects for active users and saves all presences
        before stopping background tasks.
        """
        self.create_artificial_disconnects()
        self.save_presences()
        self.auto_save_presences.cancel()

    # ------------------------------------------------------------------------
    # Data persistence methods
    # ------------------------------------------------------------------------

    def save_presences(self):
        """
        Save all voice presences to JSON file.
        
        Serializes presence data and writes it to data/voicePresences.json,
        then performs cleanup of old data.
        """
        data = {
            username: [p.to_dict() for p in presences]
            for username, presences in self.voice_presences.items()
        }
        os.makedirs("data", exist_ok=True)
        with open("data/voicePresences.json", "w", encoding="utf8") as f:
            json.dump(data, f, indent=4)
        self.cleanup_presences()

    def load_presences(self):
        """
        Load voice presences from JSON file.
        
        Reads presence data from data/voicePresences.json and deserializes
        it into VoicePresence objects.
        """
        if not os.path.exists("data/voicePresences.json"):
                return
        try:
            with open("data/voicePresences.json","r",encoding="utf8") as f:
                data = json.load(f)
                self.voice_presences = {
                    username: [VoicePresence.from_dict(p) for p in presences]
                    for username, presences in data.items()
                }
        except Exception as e:
            logger.error(f"Error loading presences : {e}")

    def cleanup_presences(self):
        """
        Clean up old presences and stale user data.
        
        Removes presences older than MAX_DAYS_SAVED (100 days) and cleans up
        user_last_activity entries for users who haven't been active recently.
        """
        cutoff = datetime.datetime.now() - datetime.timedelta(days=MAX_DAYS_SAVED)
        for username in list(self.voice_presences.keys()):
            self.voice_presences[username] = [
                presence for presence in self.voice_presences[username]
                if presence.timestamp_end > cutoff
            ]
            if not self.voice_presences[username]:
                del self.voice_presences[username]
        
        #Cleanup stale users
        for username in list(self.user_last_activity.keys()):
            if self.user_last_activity[username].timestamp < cutoff:
                del self.user_last_activity[username]

    # ------------------------------------------------------------------------
    # Artificial connect/disconnect helpers
    # ------------------------------------------------------------------------

    async def create_artificial_connects(self):
        """
        Create artificial connect activities for users already in voice channels.
        
        When the bot starts, this creates VoiceActivity entries for users who are
        already connected to voice channels, allowing proper tracking of their presence
        even though the bot didn't see them connect.
        """
        if self._artificial_connects_created:
            return
        self._artificial_connects_created = True

        for guild in self.bot.guilds:
            if guild.id == 890252683657764894 or guild.id == 932887674413535262: #TODO : CHANGE AFTER TESTING
                for member in guild.members:
                    if member.voice and member.voice.channel:
                        voice_entry = VoiceActivity(
                            member = member,
                            before = discord.VoiceState(data = {}, channel = None),
                            after = member.voice
                        )
                        self.user_last_activity[member.name] = voice_entry
                        logger.info(f"Created artifical connect for {member.name} in {member.voice.channel.name}")

    def create_artificial_disconnects(self):
        """
        Create artificial disconnect presences for users still in voice channels.
        
        For users whose last activity wasn't a disconnect, this creates a presence
        entry ending at the current time. Used when saving or shutting down to
        properly capture ongoing voice sessions.
        """
        right_now = datetime.datetime.now()
        for name, last_activity in list(self.user_last_activity.items()):
            if last_activity.activity_type not in ["disconnect", "afk"]:
                voice_presence = VoicePresence(
                    discord_name = name,
                    timestamp_start = last_activity.timestamp,
                    timestamp_end = right_now,
                    channel_name = last_activity.after_channel_name,
                    present = True
                )
                if name not in self.voice_presences:
                    self.voice_presences[name] = []
                    self.voice_presences[name].append(voice_presence)

    # ------------------------------------------------------------------------
    # Event listeners
    # ------------------------------------------------------------------------

    @commands.Cog.listener()
    async def on_voice_state_update(self,member,before,after):
        """
        Handle voice state changes for users.
        
        Creates VoiceActivity entries and VoicePresence records when users
        connect, disconnect, or change their voice state.
        
        Parameters
        ----------
        member : Member
            The member whose voice state changed.
        before : VoiceState
            The voice state before the change.
        after : VoiceState
            The voice state after the change.
        """

        voice_entry = VoiceActivity(member=member,before=before,after=after)

        if member.name in self.user_last_activity:
            last_activity = self.user_last_activity[member.name]
            voice_presence = VoicePresence.get_presence_from_activities(last_activity, voice_entry)

            if voice_presence.present:
                dictionary = self.voice_presences.get(member.name)
                if not dictionary:
                    self.voice_presences[member.name] = []
                self.voice_presences[member.name].append(voice_presence)
        
        self.user_last_activity[member.name] = voice_entry

    # ------------------------------------------------------------------------
    # Background tasks
    # ------------------------------------------------------------------------

    @tasks.loop(minutes=1)
    async def auto_save_presences(self):
        """
        Automatically save presences every 1 minute.
        
        Creates artificial disconnects for active users, saves all presence data,
        and updates timestamps for users currently in voice channels.
        """
        #TODO dont actually make dcs
        try:
            self.create_artificial_disconnects()  
            self.save_presences()
            for guild in self.bot.guilds:
                for member in guild.members:
                    if member.voice and member.voice.channel and member.name in self.user_last_activity:
                        self.user_last_activity[member.name].timestamp = datetime.datetime.now()
            logger.info(f"Auto-saved presences at {datetime.datetime.now()}")
        except Exception as e:
            logger.error(f"Failed auto-save for presences at {datetime.datetime.now()} : {e}")

    @tasks.loop(count=1)
    async def init_artificial_connects(self):
        """
        Initialize artificial connects once the bot is ready.
        
        Note: This task is currently unused.
        """
        await self.bot.wait_until_ready()
        await self.create_artificial_connects()

    @tasks.loop(seconds=60) # TODO : 60 SECONDS FOR TESTING PURPOSES ONLY!!!
    async def get_daily_presence(self):
        """
        Calculate and report daily presence statistics.
        
        Computes total time spent in voice channels over the last 24 hours
        for each user and sends the results via DM.
        """
        logger.info("Getting daily presences.")
        # A copy of voice_presences, that will sort presences and also add an artifical end to all ongoing presences
        temp_voice_presences = copy.deepcopy(self.voice_presences)


        right_now = datetime.datetime.now()
        cutoff = right_now - datetime.timedelta(hours=24)

        # Creating artifical ends to presences at the moment the daily presence check occurs
        for name, last_activity in list(self.user_last_activity.items()):
            if last_activity.activity_type not in ["disconnect", "afk"]:
                voice_presence = VoicePresence(
                    discord_name = name,
                    timestamp_start = last_activity.timestamp,
                    timestamp_end = right_now,
                    channel_name = last_activity.after_channel_name,
                    present = True
                )
                temp_voice_presences[name].append(voice_presence)
        
        time_spent_dict = {}


        for name in temp_voice_presences:
            daily_presences = [p for p in temp_voice_presences[name] if p.timestamp_end >= cutoff]
            daily_presences.sort(key=lambda p: p.timestamp_start)            
            seconds_spent = sum(presence.total_time for presence in daily_presences)
            time_spent_dict[name] = seconds_spent

        user = await self.bot.fetch_user(264416824777637898)
        await user.send(str(time_spent_dict))


    # ------------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------------

    @commands.command(hidden=True)
    @commands.is_owner()
    async def manual_presences_save(self,ctx):
        """
        Manually trigger a save of all presence data.
        
        Owner-only command to force save presences to disk.
        
        Parameters
        ----------
        ctx : commands.Context
            The command context.
        """
        try:
            self.save_presences()
            await ctx.send(f"👍 Saved {sum(len(p) for p in self.voice_presences.values())} presences.")
        except Exception as e:
            await ctx.send(f"❌ There was an error saving the presences : {e}")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def snapshot(self,ctx):
        """
        Gets the snapshot of current voice activities, presences, along with the ones in memory.
        """
        def _chunks(text, size=1900):
            for i in range(0, len(text), size):
                yield text[i:i+size]

        # Last activities
        lines = ["Last activities:"]
        if not self.user_last_activity:
            lines.append("  (none)")
        else:
            for user, act in self.user_last_activity.items():
                lines.append(f"  {user}: {act}")

        for chunk in _chunks("\n".join(lines)):
            await ctx.send(f"```text\n{chunk}\n```")

        # Presences in memory
        lines = ["Voice presences (in memory):"]
        if not self.voice_presences:
            lines.append("  (none)")
        else:
            for user, pres_list in self.voice_presences.items():
                lines.append(f"{user}:")
                for p in pres_list:
                    lines.append(f"  - {p}")

        for chunk in _chunks("\n".join(lines)):
            await ctx.send(f"```text\n{chunk}\n```")

        # Presences in file
        try:
            if os.path.exists("data/voicePresences.json"):
                with open("data/voicePresences.json", "r", encoding="utf8") as f:
                    stored_presences = json.load(f)
                formatted = json.dumps(stored_presences, indent=2)
            else:
                formatted = "(data/voicePresences.json not found)"
        except Exception as e:
            formatted = f"(error reading file: {e})"

        for chunk in _chunks(formatted):
            await ctx.send(f"```json\n{chunk}\n```")
        

    
    @commands.command() #TODO : DELETE AFTER TESTING
    async def check_presences(self,ctx):
        """
        Display all stored presence data.
        
        Shows detailed information about all presences for all users.
        
        Parameters
        ----------
        ctx : commands.Context
            The command context.
        """
        print("checking presences")
        message = ""
        for presence in self.voice_presences:
            message += f"{presence}:\n"
            for entry in self.voice_presences[presence]:
                message += f"    {entry}\n"
        await ctx.send(message)


# ============================================================================
# Setup
# ============================================================================

async def setup(bot):
    """
    Set up the Activity cog.
    
    Parameters
    ----------
    bot : commands.Bot
        The Discord bot instance.
    """
    try:
        await bot.add_cog(Activity(bot))
    except Exception as e:
        raise e
