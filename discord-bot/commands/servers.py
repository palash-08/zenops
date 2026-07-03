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
                embed = discord.Embed(
                    title="Registered ZenOps Servers",
                    description="No servers are currently registered.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            embed = discord.Embed(
                title="Registered ZenOps Servers",
                color=discord.Color.blue()
            )
            
            for server in servers:
                server_id = str(server['id'])
                short_id = server_id.split('-')[0]
                desc = server.get('description') or "No description provided."
                
                embed.add_field(
                    name=f"🌐 {server['name']}",
                    value=f"**ID:** `{short_id}`\n*{desc}*",
                    inline=False
                )
                
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ Failed to fetch servers: {e}")

async def setup(bot):
    await bot.add_cog(ServersCog(bot))
