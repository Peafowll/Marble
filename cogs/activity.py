from discord.ext import commands, tasks
from discord.member import Member
from discord import VoiceState
import json
import datetime
import logging
import os
import copy
import asyncio

#TODO : better display for weekly hours
#TODO : separate logger


# Logger and constants
logger = logging.getLogger('discord.activity')

from config import (
    MARBLE_CHANNEL_ID,
    OWNER_USER_ID,
    YKTP_GUILD_ID,
    MAX_DAYS_OF_VOICE_ACTIVITY_SAVED
)

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
        self.before_channel_name = before.channel.name if (before and before.channel) else None
        self.after_channel_name = after.channel.name if (after and after.channel) else None
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
        self.day_count = 1
        
        # Locks to prevent race conditions
        self.data_lock = asyncio.Lock()   # Protects BOTH voice_presences and user_last_activity
        self.file_lock = asyncio.Lock()   # Protects file I/O operations

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
        await self.load_presences()
        await self.create_artificial_connects()
        if not self.auto_save_presences.is_running():
            self.auto_save_presences.start()
        if not self.get_daily_presence.is_running():
            self.get_daily_presence.start()
        if not self.daily_cleanup.is_running():
            self.daily_cleanup.start()

    def cog_unload(self):
        """
        Called when the cog is unloaded.
        
        Stops background tasks and triggers final save.
        """
        # Cancel all background tasks first
        if self.auto_save_presences.is_running():
            self.auto_save_presences.cancel()
        if self.get_daily_presence.is_running():
            self.get_daily_presence.cancel()
        if self.daily_cleanup.is_running():
            self.daily_cleanup.cancel()
        
        # Schedule final save synchronously
        # Note: cog_unload can't be async, so we use asyncio.create_task
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._final_save())
            else:
                loop.run_until_complete(self._final_save())
        except Exception as e:
            logger.error(f"Failed to perform final save on unload: {e}")
    
    async def _final_save(self):
        """Perform final save with proper locking."""
        try:
            async with self.data_lock:
                snapshot = self.build_snapshot_with_artificial_disconnects()
            async with self.file_lock:
                await self.save_presences(presences_override=snapshot)
            logger.info("Final save completed on cog unload")
        except Exception as e:
            logger.error(f"Error during final save: {e}")

    # ------------------------------------------------------------------------
    # Data persistence methods
    # ------------------------------------------------------------------------

    async def save_presences(self, presences_override=None):
        """Save presences to disk. Should be called with file_lock held."""
        data = {}

        source = presences_override if presences_override else self.voice_presences

        for username, presences in source.items():
            data[username] = [p.to_dict() for p in presences]

        # Use asyncio.to_thread for blocking I/O
        def _write_file():
            os.makedirs("data", exist_ok=True)
            with open("data/voicePresences.json", "w", encoding="utf8") as f:
                json.dump(data, f, indent=4)
        
        await asyncio.to_thread(_write_file)

        if not presences_override:
            await self.cleanup_presences()

    async def load_presences(self):
        """
        Load voice presences from JSON file.
        
        Reads presence data from data/voicePresences.json and deserializes
        it into VoicePresence objects.
        """
        if not os.path.exists("data/voicePresences.json"):
                return
        try:
            def _read_file():
                with open("data/voicePresences.json","r",encoding="utf8") as f:
                    return json.load(f)
            
            data = await asyncio.to_thread(_read_file)
            
            async with self.data_lock:
                self.voice_presences = {
                    username: [VoicePresence.from_dict(p) for p in presences]
                    for username, presences in data.items()
                }
        except Exception as e:
            logger.error(f"Error loading presences : {e}")

    async def cleanup_presences(self):
        """
        Clean up old presences and stale user data.
        
        Removes presences older than MAX_DAYS_SAVED (100 days) and cleans up
        user_last_activity entries for users who haven't been active recently.
        Should be called with data_lock held.
        """
        cutoff = datetime.datetime.now() - datetime.timedelta(days=MAX_DAYS_OF_VOICE_ACTIVITY_SAVED)
        for username in list(self.voice_presences.keys()):
            self.voice_presences[username] = [
                presence for presence in self.voice_presences[username]
                if presence.timestamp_end is None or presence.timestamp_end > cutoff
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

    def build_snapshot_with_artificial_disconnects(self):
        """
        Returns a presence dictionary identical to self.voice_presences,
        but with artificial disconnects appended for users still in voice.
        """
        snapshot = copy.deepcopy(self.voice_presences)
        now = datetime.datetime.now()

        for name, last_activity in self.user_last_activity.items():
            if last_activity.activity_type not in ["disconnect", "afk"]:
                presence = VoicePresence(
                    discord_name=name,
                    timestamp_start=last_activity.timestamp,
                    timestamp_end=now,
                    channel_name=last_activity.after_channel_name,
                    present=True
                )
                snapshot.setdefault(name, []).append(presence)

        return snapshot

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

        async with self.data_lock:
            for guild in self.bot.guilds:
                if guild.id == YKTP_GUILD_ID or guild.id == 932887674413535262:
                    for member in guild.members:
                        if member.voice and member.voice.channel:
                            voice_entry = VoiceActivity(
                            member=member,
                            before=None,
                            after=member.voice
                            )
                            self.user_last_activity[member.name] = voice_entry
                            logger.info(f"Created artifical connect for {member.name} in {member.voice.channel.name}")

    # ------------------------------------------------------------------------
    # Helper functions
    # ------------------------------------------------------------------------
    def get_total_time(self, user_name, since):
        """Calculate total time in voice channels since a given timestamp."""
        now = datetime.datetime.now()
        total = 0
        for p in self.voice_presences.get(user_name, []):
            overlap_start = max(p.timestamp_start, since)
            overlap_end = min(p.timestamp_end, now)
            if overlap_end > overlap_start:
                total += (overlap_end - overlap_start).total_seconds()
        return total

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
        try:
            voice_entry = VoiceActivity(member=member,before=before,after=after)

            # Single lock for both dictionaries - prevents deadlocks
            async with self.data_lock:
                if member.name in self.user_last_activity:
                    last_activity = self.user_last_activity[member.name]
                    voice_presence = VoicePresence.get_presence_from_activities(last_activity, voice_entry)

                    if voice_presence.present:
                        if member.name not in self.voice_presences:
                            self.voice_presences[member.name] = []
                        self.voice_presences[member.name].append(voice_presence)
                
                self.user_last_activity[member.name] = voice_entry
        except Exception as e:
            logger.exception(f"Failed to track voice update for {member.name}")

    # ------------------------------------------------------------------------
    # Background tasks
    # ------------------------------------------------------------------------

    @tasks.loop(minutes=1)
    async def auto_save_presences(self):
        """
        Automatically save presences every 1 minute.
        """

        try:
            # Lock data while creating snapshot
            async with self.data_lock:
                snapshot = self.build_snapshot_with_artificial_disconnects()
            
            # Lock file I/O separately to minimize lock duration
            async with self.file_lock:
                await self.save_presences(presences_override=snapshot)
            logger.info(f"Auto-save completed at {datetime.datetime.now()}")
        except Exception as e:
            logger.error(f"Auto-save failed at {datetime.datetime.now()} : {e}")

    @tasks.loop(count=1)
    async def init_artificial_connects(self):
        """
        Initialize artificial connects once the bot is ready.
        
        Note: This task is currently unused.
        """
        await self.bot.wait_until_ready()
        await self.create_artificial_connects()


    
    @tasks.loop(time=datetime.time(hour=22, minute=5, tzinfo=datetime.timezone.utc))
    async def get_daily_presence(self):
        """
        Calculate and report daily presence statistics.
        
        Runs daily at 00:05 UTC. Computes total time spent in voice channels 
        over the last 24 hours. On Sundays (UTC), also computes and posts 
        weekly summary covering the previous 7 calendar days.
        """
        logger.info("Running daily presence calculation at 00:05 UTC.")

        right_now = datetime.datetime.now()
        cutoff = right_now - datetime.timedelta(hours=24)

        # Lock data while calculating daily stats
        async with self.data_lock:
            names = set(self.voice_presences.keys()) | set(self.user_last_activity.keys())
            time_spent_dict = {}

            for name in names:
                base = self.get_total_time(name, cutoff)
                ongoing = 0
                last_activity = self.user_last_activity.get(name)
                if last_activity and last_activity.activity_type not in ["disconnect", "afk", "mute", "deaf"]:
                    ongoing = (right_now - last_activity.timestamp).total_seconds()
                time_spent_dict[name] = base + ongoing


        today = datetime.datetime.now().date().isoformat()


        # Lock file I/O for daily presences
        async with self.file_lock:
            daily = {}
            if os.path.exists("data/dailyPresences.json"):
                try:
                    def _read():
                        with open("data/dailyPresences.json", "r", encoding="utf8") as f:
                            return json.load(f)
                    daily = await asyncio.to_thread(_read)
                except Exception as e:
                    logger.error(f"Failed reading dailyPresences.json: {e}")
                    daily = {}

            daily[today] = {user: round(seconds, 2) for user, seconds in time_spent_dict.items()}

            def _write():
                os.makedirs("data", exist_ok=True)
                with open("data/dailyPresences.json", "w", encoding="utf8") as f:
                    json.dump(daily, f, indent=2)
            
            try:
                await asyncio.to_thread(_write)
            except Exception as e:
                logger.error(f"Failed writing dailyPresences.json: {e}")


        
        if right_now.weekday() == 7:
            last_seven_days = [(datetime.date.today() - datetime.timedelta(days=i)).isoformat() for i in range(7)]
            weekly_seconds = {}
            for day in last_seven_days:
                day_data = daily.get(day, {})
                for user, seconds in day_data.items():
                    weekly_seconds[user] = weekly_seconds.get(user, 0) + seconds
            sorted_weekly = dict(sorted(weekly_seconds.items(), key=lambda x: x[1], reverse=True))

            message = "# This week's voice chat presences!\n"
            for person in sorted_weekly.keys():
                hours = sorted_weekly[person] / 3600
                message+= f"{str(person)} - {hours:.2f} hours.\n"

            channel = await self.bot.fetch_channel(MARBLE_CHANNEL_ID)
            await channel.send(message)
        owner = await self.bot.fetch_user(OWNER_USER_ID)
        await owner.send(f"Daily activity : {str(time_spent_dict)}")

    @tasks.loop(hours=24)
    async def daily_cleanup(self):
        async with self.data_lock:
            await self.cleanup_presences()
        async with self.file_lock:
            await self.save_presences()
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
            async with self.file_lock:
                await self.save_presences()
            async with self.data_lock:
                count = sum(len(p) for p in self.voice_presences.values())
            await ctx.send(f"👍 Saved {count} presences.")
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
