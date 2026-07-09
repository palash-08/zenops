import discord
from discord.ext import commands
from discord import app_commands
import io

from services.backend_client import BackendClient
from commands.modals import ServerRegisterModal
from commands.views import DeleteConfirmView
from commands.utils import _create_embed, handle_backend_errors

DISPLAY_NAMES = {
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "docker_compose": "Docker Compose",
    "tailscale": "Tailscale",
    "pterodactyl": "Pterodactyl",
    "docker": "Docker",
    "nginx": "Nginx",
    "apache": "Apache",
    "redis": "Redis",
    "wings": "Wings"
}

class ZenGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="zen", description="ZenOps orchestration commands")
        self.backend = BackendClient()

    def _resolve_server(self, servers: list, server_arg: str = None, for_routing: bool = False):
        if len(servers) == 0:
            return None, _create_embed(
                "No Servers Found",
                "No servers are currently registered.\nPlease run `/zen register` to add one.",
                discord.Color.yellow()
            )

        if len(servers) == 1:
            return servers[0], None

        if not server_arg:
            if for_routing:
                desc = "Multiple servers are currently registered.\n\nAutomatic routing is not available yet.\n\nRegistered servers:\n\n"
                for s in servers:
                    desc += f"* {s['name']}\n"
                return None, _create_embed("Routing Not Implemented", desc, discord.Color.yellow())
            else:
                return None, _create_embed(
                    "Multiple Servers Found",
                    "Multiple servers are registered. Please specify the server name or UUID.",
                    discord.Color.yellow()
                )

        exact_matches = [s for s in servers if s["id"] == server_arg or s["name"].lower() == server_arg.lower()]
        if len(exact_matches) == 1:
            return exact_matches[0], None

        prefix_matches = [s for s in servers if str(s["id"]).startswith(server_arg) or s["name"].lower().startswith(server_arg.lower())]
        if len(prefix_matches) == 1:
            return prefix_matches[0], None
        elif len(prefix_matches) > 1:
            if for_routing:
                desc = "Multiple servers matched your query.\n\nAutomatic routing is not available yet.\n\nMatched servers:\n\n"
                for s in prefix_matches:
                    desc += f"* {s['name']}\n"
                return None, _create_embed("Routing Not Implemented", desc, discord.Color.yellow())
            else:
                return None, _create_embed(
                    "Multiple Servers Found",
                    "Multiple servers matched your query. Please be more specific with the server name or UUID.",
                    discord.Color.yellow()
                )

        return None, _create_embed("Server Not Found", f"Server '{server_arg}' not found.", discord.Color.red())

    @app_commands.command(name="register", description="Guide the user through registering a new VPS")
    async def register(self, interaction: discord.Interaction):
        modal = ServerRegisterModal(self.backend)
        await interaction.response.send_modal(modal)

    @app_commands.command(name="ask", description="Execute a natural language prompt on ZenOps")
    @app_commands.describe(prompt="The natural language instruction to execute")
    async def ask(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer()

        guild_id = str(interaction.guild_id) if interaction.guild_id else "0"
        channel_id = str(interaction.channel_id)

        response_data = await handle_backend_errors(
            interaction, self.backend.execute_agent_prompt(guild_id=guild_id, channel_id=channel_id, prompt=prompt), followup=True
        )
        if response_data is None:
            return

        assistant_text = "No text returned."
        try:
            for out in response_data.get("output", []):
                if out.get("type") == "message" or out.get("role") == "assistant":
                    for content_item in out.get("content", []):
                        if content_item.get("type") == "output_text":
                            assistant_text = content_item.get("text", "No text returned.")
                            break
                    break
        except Exception:
            pass

        embed = discord.Embed(color=discord.Color.blue())
        if len(assistant_text) > 2000:
            embed.description = "The response was too long to display and has been attached as a file."
            file_bytes = io.BytesIO(assistant_text.encode("utf-8"))
            discord_file = discord.File(file_bytes, filename="response.txt")
            await interaction.followup.send(embed=embed, file=discord_file)
        else:
            embed.description = assistant_text
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="discover", description="Discover infrastructure on a registered server")
    @app_commands.describe(server="The name or UUID of the server (optional if only one exists)")
    async def discover(self, interaction: discord.Interaction, server: str = None):
        await interaction.response.defer()

        servers = await handle_backend_errors(interaction, self.backend.get_servers(), followup=True)
        if servers is None:
            return

        target_server, error_embed = self._resolve_server(servers, server, for_routing=False)
        if error_embed:
            await interaction.edit_original_response(embed=error_embed)
            return

        await interaction.edit_original_response(content="Searching for infrastructure...")

        inventory_data = await handle_backend_errors(interaction, self.backend.run_discovery(target_server["id"]), edit=True)
        if inventory_data is None:
            return

        embed = discord.Embed(title="Infrastructure Discovery Complete", color=discord.Color.green())
        embed.add_field(name="Server", value=target_server["name"], inline=False)
        embed.add_field(name="Hostname", value=inventory_data.get("hostname", "Unknown"), inline=False)

        services = inventory_data.get("services", {})
        services_text = "\n".join([f"* {DISPLAY_NAMES.get(k, k.replace('_', ' ').title())}" for k, v in services.items() if v])
        embed.add_field(name="Detected Services", value=services_text or "No services detected.", inline=False)
        embed.add_field(name="Summary", value=inventory_data.get("summary", "No summary provided."), inline=False)
        embed.set_footer(text="Infrastructure inventory updated successfully.")

        await interaction.edit_original_response(content=None, embed=embed)

    @app_commands.command(name="delete", description="Remove a server from ZenOps")
    @app_commands.describe(server="The name or UUID of the server (optional if only one exists)")
    async def delete(self, interaction: discord.Interaction, server: str = None):
        await interaction.response.defer()

        servers = await handle_backend_errors(interaction, self.backend.get_servers(), followup=True)
        if servers is None:
            return

        target_server, error_embed = self._resolve_server(servers, server, for_routing=False)
        if error_embed:
            await interaction.edit_original_response(embed=error_embed)
            return

        embed = _create_embed(
            "Confirm Server Deletion",
            "This only removes the server from ZenOps.\nThe remote VPS, OpenClaw and Tailscale will NOT be modified.",
            discord.Color.red()
        )
        embed.add_field(name="Server Name", value=target_server["name"], inline=False)
        embed.add_field(name="Server UUID", value=f"`{target_server['id']}`", inline=False)

        view = DeleteConfirmView(self.backend, target_server["id"], target_server["name"], interaction.user.id)
        msg = await interaction.edit_original_response(embed=embed, view=view)
        view.message = msg

    @app_commands.command(name="bind", description="Bind this channel to a server")
    @app_commands.describe(server="The name or UUID of the server")
    async def bind(self, interaction: discord.Interaction, server: str):
        await interaction.response.defer()

        servers = await handle_backend_errors(interaction, self.backend.get_servers(), followup=True)
        if servers is None:
            return

        target_server, error_embed = self._resolve_server(servers, server, for_routing=False)
        if error_embed:
            await interaction.edit_original_response(embed=error_embed)
            return

        result = await handle_backend_errors(interaction, self.backend.bind_channel(str(interaction.channel_id), target_server["id"]), edit=True)
        if result is None:
            return

        embed = _create_embed("Channel Bound", f"This channel is now bound to {target_server['name']}.", discord.Color.green())
        await interaction.edit_original_response(embed=embed)

    @app_commands.command(name="unbind", description="Unbind this channel")
    async def unbind(self, interaction: discord.Interaction):
        await interaction.response.defer()

        result = await handle_backend_errors(interaction, self.backend.unbind_channel(str(interaction.channel_id)), edit=True)
        if result is None:
            return

        embed = _create_embed("Channel Unbound", "This channel is no longer bound to any server.", discord.Color.green())
        await interaction.edit_original_response(embed=embed)

    @app_commands.command(name="global", description="Mark this channel as global")
    async def global_channel(self, interaction: discord.Interaction):
        await interaction.response.defer()

        guild_id = str(interaction.guild_id) if interaction.guild_id else "0"
        result = await handle_backend_errors(interaction, self.backend.set_global_channel(guild_id, str(interaction.channel_id)), edit=True)
        if result is None:
            return

        embed = _create_embed("Global Channel Set", "This channel is now the global management channel.", discord.Color.green())
        await interaction.edit_original_response(embed=embed)

    context_group = app_commands.Group(name="context", description="Manage context limits")

    @context_group.command(name="info", description="View context information")
    async def context_info(self, interaction: discord.Interaction):
        await interaction.response.defer()

        guild_id = str(interaction.guild_id) if interaction.guild_id else "0"
        info = await handle_backend_errors(interaction, self.backend.get_context_info(str(interaction.channel_id), guild_id), edit=True)
        if info is None:
            return

        embed = _create_embed("Context Information", "", discord.Color.blue())
        embed.add_field(name="Bound Server", value=info["server_name"], inline=False)
        embed.add_field(name="Context Limit", value=str(info["chat_context_limit"]), inline=False)
        embed.add_field(name="Stored Messages", value=str(info["message_count"]), inline=False)
        embed.add_field(name="Is Global", value="Yes" if info["is_global"] else "No", inline=False)
        await interaction.edit_original_response(embed=embed)

    @context_group.command(name="set", description="Set context limit")
    @app_commands.describe(limit="The new message context limit")
    async def context_set(self, interaction: discord.Interaction, limit: int):
        await interaction.response.defer()
        if limit <= 0:
            embed = _create_embed("Invalid Limit", "Limit must be a positive integer.", discord.Color.red())
            await interaction.edit_original_response(embed=embed)
            return

        result = await handle_backend_errors(interaction, self.backend.update_context_limit(str(interaction.channel_id), limit), edit=True)
        if result is None:
            return

        embed = _create_embed("Context Limit Updated", f"The context limit is now {limit}.", discord.Color.green())
        await interaction.edit_original_response(embed=embed)

    @app_commands.command(name="clearchatcontext", description="Clear short-term context for this channel")
    async def clearchatcontext(self, interaction: discord.Interaction):
        await interaction.response.defer()

        result = await handle_backend_errors(interaction, self.backend.clear_chat_context(str(interaction.channel_id)), edit=True)
        if result is None:
            return

        embed = _create_embed("Context Cleared", "Short-term chat context has been cleared. (Cognee memory and bindings are untouched).", discord.Color.green())
        await interaction.edit_original_response(embed=embed)

class ZenCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.zen_group = ZenGroup()
        self.bot.tree.add_command(self.zen_group)

    async def cog_unload(self):
        await self.zen_group.backend.close()

async def setup(bot):
    await bot.add_cog(ZenCog(bot))
