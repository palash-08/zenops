import discord
from discord.ext import commands
from discord import app_commands
from services.backend_client import BackendClient

class ServersCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.backend = BackendClient()

    @app_commands.command(name="servers", description="List all registered ZenOps servers")
    async def list_servers(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        try:
            servers = await self.backend.get_servers()
            
            if not servers:
                await interaction.followup.send("No servers are currently registered.")
                return

            response_text = "**Registered ZenOps Servers:**\n\n"
            for server in servers:
                response_text += f"**{server['name']}**\n"
                if server.get('description'):
                    response_text += f"*{server['description']}*\n"
                response_text += f"- **Tailscale IP:** `{server['tailscale_ip']}`\n"
                response_text += f"- **Gateway Port:** `{server['gateway_port']}`\n\n"
                
            await interaction.followup.send(response_text)

        except Exception as e:
            await interaction.followup.send(f"❌ Failed to fetch servers: {e}")

async def setup(bot):
    await bot.add_cog(ServersCog(bot))
