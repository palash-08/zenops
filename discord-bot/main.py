import sys
from core.config import settings
from bot import create_bot

def main():
    """
    Main entry point for the application.
    It loads the config and starts the bot.
    """
    if not settings.discord_bot_token:
        print("❌ Error: DISCORD_BOT_TOKEN is missing or empty in the .env file.")
        sys.exit(1)
        
    bot = create_bot()
    print("Starting Discord bot...")
    bot.run(settings.discord_bot_token)

if __name__ == "__main__":
    main()
