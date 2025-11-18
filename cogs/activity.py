import discord
from discord.ext import commands
from discord.member import Member
from discord import VoiceState, member 
from discord.ui import Button, View
from helpers import find_lol_spells
import random
import json
import asyncio
import time, datetime
import logging

logger = logging.getLogger('discord.activity')
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
        self.discord_name = member.global_name
        self.before_channel_name = before.channel.name if before.channel else None
        self.after_channel_name = after.channel.name if after.channel else None
        self.activity_type = self.detect_activity_type(before, after)
        self.timestamp = datetime.datetime.now()

    def detect_activity_type(self, before : VoiceState, after : VoiceState):
        """Determine the activity that occured."""
        if after.afk:
            return "afk"
        if not before.channel and after.channel:
            return "connect"
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

    def __str__(self):
        return(f"Name : {self.discord_name}- PRESENT={self.present}, from {self.timestamp_start} to {self.timestamp_end} ({self.total_time}), in {self.channel_name}")


class Activity(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        self.voice_entries = []
        self.voice_presences = {}



    @commands.Cog.listener()
    async def on_voice_state_update(self,member,before,after):
        voice_entries = []
        voice_entry = VoiceActivity(member=member,before=before,after=after)
        self.voice_entries.append(voice_entry)
        if len(self.voice_entries) > 1:
            last_pos = len(self.voice_entries)
            voice_presence = VoicePresence.get_presence_from_activities(self.voice_entries[last_pos-2],self.voice_entries[last_pos-1])
            if voice_presence.present:
                dictionary = self.voice_presences.get(member.name)
                if not dictionary:
                    self.voice_presences[member.name] = []
                self.voice_presences[member.name].append(voice_presence)
    
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
