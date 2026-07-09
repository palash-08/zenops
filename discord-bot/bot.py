import discord
from discord.ext import commands
from core.config import settings

def _get_activity(activity_type: str, activity_text: str):
    activity_type = activity_type.lower().strip()
    if activity_type == "watching":
        return discord.Activity(type=discord.ActivityType.watching, name=activity_text)
    elif activity_type == "listening":
        return discord.Activity(type=discord.ActivityType.listening, name=activity_text)
    elif activity_type == "competing":
        return discord.Activity(type=discord.ActivityType.competing, name=activity_text)
    else:
        return discord.Game(name=activity_text)

def create_bot() -> commands.Bot:
    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def setup_hook():
        await bot.load_extension("commands.servers")
        await bot.load_extension("commands.ask")
        await bot.load_extension("commands.zen")

        try:
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} slash command(s)")
        except Exception as e:
            print(f"Failed to sync commands: {e}")

    @bot.event
    async def on_ready():
        activity = _get_activity(settings.bot_activity_type, settings.bot_activity_text)
        await bot.change_presence(activity=activity)
        print(f"Logged in as {bot.user}")

    return bot
