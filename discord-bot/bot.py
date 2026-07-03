import discord
from discord.ext import commands

def create_bot() -> commands.Bot:
    """
    Creates and configures the Discord Bot instance.
    We isolate this logic so main.py just has to call it.
    """
    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def setup_hook():
        """
        setup_hook runs before the bot starts accepting events.
        We load our command modules (cogs) here.
        """
        await bot.load_extension("commands.servers")
        
        # Sync the slash commands with Discord
        try:
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} slash command(s)")
        except Exception as e:
            print(f"❌ Failed to sync commands: {e}")

    @bot.event
    async def on_ready():
        print(f"✅ Logged in as {bot.user}")

    return bot
