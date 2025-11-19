import discord
from discord.ext import commands, tasks
from discord.member import Member
from discord import VoiceState
import json
import datetime
import logging
import os

logger = logging.getLogger('discord.activity')

MAX_DAYS_SAVED = 100

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
        """Determine the activity that occured."""
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
        return cls(
            discord_name=data["discord_name"],
            timestamp_start=datetime.datetime.fromisoformat(data["timestamp_start"]),
            timestamp_end=datetime.datetime.fromisoformat(data["timestamp_end"]),
            channel_name=data["channel_name"],
            present=data["present"]
        )

    def __str__(self):
        return(f"Name : {self.discord_name}- PRESENT={self.present}, from {self.timestamp_start} to {self.timestamp_end} ({self.total_time}), in {self.channel_name}")

class Activity(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        self.voice_presences = {}
        self.user_last_activity = {}
        self._artificial_connects_created = False

    def cog_unload(self):
        self.create_artificial_disconnects()
        self.save_presences()
        self.auto_save_presences.cancel()

    async def cog_load(self):
        self.load_presences()
        self.auto_save_presences.start()

    def cleanup_presences(self):
        """
        Cleans up presences older than a week,
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

    def save_presences(self):
        data = {
            username: [p.to_dict() for p in presences]
            for username, presences in self.voice_presences.items()
        }
        os.makedirs("data", exist_ok=True)
        with open("data/voicePresences.json", "w", encoding="utf8") as f:
            json.dump(data, f, indent=4)
        self.cleanup_presences()

    def load_presences(self):
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

    async def create_artificial_connects(self):
        """
        Helper function for creating artifical connects when the bot starts.
        Helps to track people that might have been online while the bot was offline.
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

    @tasks.loop(minutes=10)
    async def auto_save_presences(self):
        """
        Tries to save the presences to json every 10 minutes.
        """
        try:
            self.save_presences()
            logger.info(f"Auto-saved presences at {datetime.datetime.now()}")
        except Exception as e:
            logger.error(f"Failed auto-save for presences at {datetime.datetime.now()} : {e}")

    @tasks.loop(count=1)
    async def init_artificial_connects(self):
        await self.bot.wait_until_ready()
        await self.create_artificial_connects()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.create_artificial_connects()

    @commands.Cog.listener()
    async def on_voice_state_update(self,member,before,after):

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

    @commands.command(hidden=True)
    @commands.is_owner()
    async def manual_presences_save(self,ctx):
        try:
            self.save_presences()
            await ctx.send(f"👍 Saved {sum(len(p) for p in self.voice_presences.values())} presences.")
        except Exception as e:
            await ctx.send(f"❌ There was an error saving the presences : {e}")

    @commands.command()
    async def check_presences(self,ctx):
        print("checking presences")
        message = ""
        for presence in self.voice_presences:
            message += f"{presence}:\n"
            for entry in self.voice_presences[presence]:
                message += f"    {entry}\n"
        await ctx.send(message)

async def setup(bot):
    try:
        await bot.add_cog(Activity(bot))
    except Exception as e:
        raise e
