import discord
from discord.ext import commands
from discord import app_commands
from services.backend_client import BackendClient
from urllib.parse import urlparse
import httpx
import traceback
import io

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

def _create_embed(title: str, description: str, color: discord.Color) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=color)

class ServerRegisterModal(discord.ui.Modal, title='Register New VPS'):
    server_name = discord.ui.TextInput(
        label='Friendly Server Name',
        placeholder='e.g., Ubuntu Production',
        required=True
    )
    
    gateway_url = discord.ui.TextInput(
        label='Gateway URL',
        placeholder='e.g., https://10.x.y.z:443',
        required=True
    )
    
    gateway_token = discord.ui.TextInput(
        label='Gateway Token',
        placeholder='Bearer Token',
        required=True
    )
    
    description = discord.ui.TextInput(
        label='Optional Description',
        style=discord.TextStyle.paragraph,
        required=False
    )
    
    server_context = discord.ui.TextInput(
        label='Server Context',
        placeholder="Describe this server's purpose or anything the agent should always remember...",
        style=discord.TextStyle.paragraph,
        required=False
    )

    def __init__(self, backend_client: BackendClient):
        super().__init__()
        self.backend = backend_client

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        try:
            # 1. Gateway URL Validation
            url_str = self.gateway_url.value.strip()
            if not url_str.startswith(('http://', 'https://')):
                embed = _create_embed("Invalid URL", "The Gateway URL must start with http:// or https://", discord.Color.yellow())
                await interaction.followup.send(embed=embed)
                return
                
            parsed_url = urlparse(url_str)
            if not parsed_url.hostname:
                embed = _create_embed("Invalid URL", "The Gateway URL is malformed or missing a hostname.", discord.Color.yellow())
                await interaction.followup.send(embed=embed)
                return
                
            host = parsed_url.hostname
            port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
            
            # 2. Duplicate Detection
            servers = await self.backend.get_servers()
            new_name = self.server_name.value.strip()
            
            for s in servers:
                if s["name"].lower() == new_name.lower():
                    embed = _create_embed("Duplicate Server", f"A server with the name '{new_name}' already exists.", discord.Color.yellow())
                    await interaction.followup.send(embed=embed)
                    return
                    
                existing_url = f"https://{s['tailscale_ip']}:{s['gateway_port']}"
                expected_new_url = f"{parsed_url.scheme}://{host}:{port}"
                # Comparing core network identity
                if s["tailscale_ip"] == host and s["gateway_port"] == port:
                    embed = _create_embed("Duplicate Server", f"A server with the Gateway URL `{expected_new_url}` is already registered.", discord.Color.yellow())
                    await interaction.followup.send(embed=embed)
                    return

            # 3. Registration
            payload = {
                "name": new_name,
                "description": self.description.value.strip() if self.description.value else None,
                "tailscale_ip": host,
                "gateway_port": port,
                "gateway_token": self.gateway_token.value.strip()
            }
            
            context_val = self.server_context.value.strip()
            if context_val:
                payload["context"] = context_val
            
            response = await self.backend.register_server(payload)
            
            # 4. Better Success Embed
            embed = discord.Embed(
                title="✅ Server registered successfully.\n\nInitializing server memory in the background...",
                color=discord.Color.green()
            )
            embed.add_field(name="Name", value=response["name"], inline=False)
            if response.get("description"):
                embed.add_field(name="Description", value=response["description"], inline=False)
            
            final_url = f"https://{response['tailscale_ip']}:{response['gateway_port']}"
            embed.add_field(name="Gateway URL", value=final_url, inline=False)
            embed.add_field(name="Server UUID", value=f"`{response['id']}`", inline=False)
            
            embed.set_footer(text="Next step: /zen discover")
            await interaction.followup.send(embed=embed)
            
        except httpx.HTTPStatusError as e:
            traceback.print_exc()
            if e.response.status_code == 500:
                embed = _create_embed("Execution Failed", "Backend returned an internal server error (HTTP 500).", discord.Color.red())
            elif e.response.status_code == 502:
                embed = _create_embed("Execution Failed", "Backend is unavailable or returning Bad Gateway (HTTP 502).", discord.Color.red())
            else:
                embed = _create_embed("Execution Failed", f"Backend returned an error: HTTP {e.response.status_code}", discord.Color.red())
            await interaction.followup.send(embed=embed)
            
        except httpx.TimeoutException:
            traceback.print_exc()
            embed = _create_embed("Network Timeout", "The request to the backend timed out.", discord.Color.red())
            await interaction.followup.send(embed=embed)
            
        except httpx.RequestError as e:
            traceback.print_exc()
            embed = _create_embed("Network Error", f"Failed to communicate with the backend:\n{e}", discord.Color.red())
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            traceback.print_exc()
            embed = _create_embed("Unexpected Error", f"An unexpected error occurred:\n{e}", discord.Color.red())
            await interaction.followup.send(embed=embed)


class DeleteConfirmView(discord.ui.View):
    def __init__(self, backend_client: BackendClient, server_id: str, server_name: str, owner_id: int):
        super().__init__(timeout=60.0)
        self.backend = backend_client
        self.server_id = server_id
        self.server_name = server_name
        self.owner_id = owner_id
        self.message = None

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger, emoji="🗑")
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("You didn't initiate this deletion.", ephemeral=True)
            return
            
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        
        try:
            await self.backend.delete_server(self.server_id)
            embed = _create_embed(
                "✅ Server Deleted",
                "The server has been removed from ZenOps successfully.",
                discord.Color.green()
            )
            await interaction.edit_original_response(embed=embed, view=None)
        except httpx.HTTPStatusError as e:
            traceback.print_exc()
            if e.response.status_code == 404:
                embed = _create_embed("Execution Failed", "Server not found (HTTP 404).", discord.Color.red())
            elif e.response.status_code == 500:
                embed = _create_embed("Execution Failed", "Backend returned an internal server error (HTTP 500).", discord.Color.red())
            else:
                embed = _create_embed("Execution Failed", f"Backend returned an error: HTTP {e.response.status_code}", discord.Color.red())
            await interaction.edit_original_response(embed=embed, view=None)
        except httpx.TimeoutException:
            traceback.print_exc()
            embed = _create_embed("Network Timeout", "The request to the backend timed out.", discord.Color.red())
            await interaction.edit_original_response(embed=embed, view=None)
        except Exception as e:
            traceback.print_exc()
            embed = _create_embed("Unexpected Error", f"An unexpected error occurred:\n{e}", discord.Color.red())
            await interaction.edit_original_response(embed=embed, view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("You didn't initiate this deletion.", ephemeral=True)
            return
            
        embed = _create_embed("Deletion Cancelled", "Deletion cancelled.", discord.Color.greyple())
        await interaction.response.edit_message(embed=embed, view=None)

    async def on_timeout(self):
        if self.message:
            try:
                embed = self.message.embeds[0]
                embed.set_footer(text="Deletion request expired.")
                await self.message.edit(embed=embed, view=None)
            except Exception:
                pass

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
                    desc += f"• {s['name']}\n"
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
                    desc += f"• {s['name']}\n"
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
        # We cannot defer here because we are sending a modal
        modal = ServerRegisterModal(self.backend)
        await interaction.response.send_modal(modal)

    @app_commands.command(name="ask", description="Execute a natural language prompt on ZenOps")
    @app_commands.describe(prompt="The natural language instruction to execute")
    async def ask(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer()
        
        try:
            guild_id = str(interaction.guild_id) if interaction.guild_id else "0"
            channel_id = str(interaction.channel_id)
            
            # 1. Execute the prompt via the backend orchestrator
            response_data = await self.backend.execute_agent_prompt(
                guild_id=guild_id,
                channel_id=channel_id,
                prompt=prompt
            )
            
            # 2. Extract assistant output
            assistant_text = "No text returned."
            try:
                outputs = response_data.get("output", [])
                for out in outputs:
                    if out.get("type") == "message" or out.get("role") == "assistant":
                        for content_item in out.get("content", []):
                            if content_item.get("type") == "output_text":
                                assistant_text = content_item.get("text", "No text returned.")
                                break
                        break
            except Exception:
                pass
                
            # 3. Display in a Discord embed
            embed = discord.Embed(
                title="🤖 ZenOps",
                color=discord.Color.blue()
            )
            
            if len(assistant_text) > 2000:
                embed.description = "The response was too long to display and has been attached as a file."
                file_bytes = io.BytesIO(assistant_text.encode("utf-8"))
                discord_file = discord.File(file_bytes, filename="response.txt")
                
                await interaction.followup.send(embed=embed, file=discord_file)
            else:
                embed.description = assistant_text
                await interaction.followup.send(embed=embed)
                
        except httpx.HTTPStatusError as e:
            traceback.print_exc()
            if e.response.status_code == 400:
                error_detail = "Bad Request"
                try:
                    error_detail = e.response.json().get("detail", error_detail)
                except:
                    pass
                embed = _create_embed("Routing Error", error_detail, discord.Color.yellow())
            elif e.response.status_code == 500:
                embed = _create_embed("Execution Failed", "Backend returned an internal server error (HTTP 500).", discord.Color.red())
            elif e.response.status_code == 502:
                embed = _create_embed("Execution Failed", "Gateway is unavailable, or the assistant returned an invalid/malformed response (HTTP 502).", discord.Color.red())
            else:
                embed = _create_embed("Execution Failed", f"Backend returned an error: HTTP {e.response.status_code}", discord.Color.red())
            await interaction.followup.send(embed=embed)
            
        except httpx.TimeoutException:
            traceback.print_exc()
            embed = _create_embed("Network Timeout", "The request to the backend timed out.", discord.Color.red())
            await interaction.followup.send(embed=embed)
            
        except httpx.RequestError as e:
            traceback.print_exc()
            embed = _create_embed("Network Error", f"Failed to communicate with the backend:\n{e}", discord.Color.red())
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            traceback.print_exc()
            embed = _create_embed("Unexpected Error", f"An unexpected error occurred:\n{e}", discord.Color.red())
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="discover", description="Discover infrastructure on a registered server")
    @app_commands.describe(server="The name or UUID of the server (optional if only one exists)")
    async def discover(self, interaction: discord.Interaction, server: str = None):
        await interaction.response.defer()
        
        try:
            # 1. Fetch all registered servers
            servers = await self.backend.get_servers()
            
            target_server, error_embed = self._resolve_server(servers, server, for_routing=False)
            if error_embed:
                await interaction.edit_original_response(embed=error_embed)
                return

            await interaction.edit_original_response(content="🔍 Discovering infrastructure...")
            
            inventory_data = await self.backend.run_discovery(target_server["id"])
            
            embed = discord.Embed(
                title="✅ Infrastructure Discovery Complete",
                color=discord.Color.green()
            )
            embed.add_field(name="Server", value=target_server["name"], inline=False)
            
            hostname = inventory_data.get("hostname", "Unknown")
            embed.add_field(name="Hostname", value=hostname, inline=False)
            
            services = inventory_data.get("services", {})
            services_text = "\n".join([f"• {DISPLAY_NAMES.get(k, k.replace('_', ' ').title())}" for k, v in services.items() if v])
            if not services_text:
                services_text = "No services detected."
            
            embed.add_field(name="Detected Services", value=services_text, inline=False)
            
            summary = inventory_data.get("summary", "No summary provided.")
            embed.add_field(name="Summary", value=summary, inline=False)
            
            embed.set_footer(text="Infrastructure inventory updated successfully.")
            
            await interaction.edit_original_response(content=None, embed=embed)
            
        except httpx.HTTPStatusError as e:
            traceback.print_exc()
            if e.response.status_code == 500:
                embed = _create_embed("Execution Failed", "Backend returned an internal server error (HTTP 500).", discord.Color.red())
            elif e.response.status_code == 502:
                embed = _create_embed("Execution Failed", "Gateway is unavailable, or the assistant returned an invalid/malformed response (HTTP 502).", discord.Color.red())
            else:
                embed = _create_embed("Execution Failed", f"Backend returned an error: HTTP {e.response.status_code}", discord.Color.red())
            await interaction.edit_original_response(content=None, embed=embed)
            
        except httpx.TimeoutException:
            traceback.print_exc()
            embed = _create_embed("Network Timeout", "The request to the backend timed out.", discord.Color.red())
            await interaction.edit_original_response(content=None, embed=embed)
            
        except httpx.RequestError as e:
            traceback.print_exc()
            embed = _create_embed("Network Error", f"Failed to communicate with the backend:\n{e}", discord.Color.red())
            await interaction.edit_original_response(content=None, embed=embed)
            
        except Exception as e:
            traceback.print_exc()
            embed = _create_embed("Unexpected Error", f"An unexpected error occurred:\n{e}", discord.Color.red())
            await interaction.edit_original_response(content=None, embed=embed)

    @app_commands.command(name="delete", description="Remove a server from ZenOps")
    @app_commands.describe(server="The name or UUID of the server (optional if only one exists)")
    async def delete(self, interaction: discord.Interaction, server: str = None):
        await interaction.response.defer()
        
        try:
            servers = await self.backend.get_servers()
            
            target_server, error_embed = self._resolve_server(servers, server, for_routing=False)
            if error_embed:
                await interaction.edit_original_response(embed=error_embed)
                return
                
            embed = _create_embed(
                "⚠ Confirm Server Deletion",
                "This only removes the server from ZenOps.\nThe remote VPS, OpenClaw and Tailscale will NOT be modified.",
                discord.Color.red()
            )
            embed.add_field(name="Server Name", value=target_server["name"], inline=False)
            embed.add_field(name="Server UUID", value=f"`{target_server['id']}`", inline=False)
            
            view = DeleteConfirmView(self.backend, target_server["id"], target_server["name"], interaction.user.id)
            msg = await interaction.edit_original_response(embed=embed, view=view)
            view.message = msg
            
        except httpx.HTTPStatusError as e:
            traceback.print_exc()
            if e.response.status_code == 500:
                embed = _create_embed("Execution Failed", "Backend returned an internal server error (HTTP 500).", discord.Color.red())
            elif e.response.status_code == 502:
                embed = _create_embed("Execution Failed", "Gateway is unavailable, or the assistant returned an invalid/malformed response (HTTP 502).", discord.Color.red())
            else:
                embed = _create_embed("Execution Failed", f"Backend returned an error: HTTP {e.response.status_code}", discord.Color.red())
            await interaction.edit_original_response(content=None, embed=embed)
        except httpx.TimeoutException:
            traceback.print_exc()
            embed = _create_embed("Network Timeout", "The request to the backend timed out.", discord.Color.red())
            await interaction.edit_original_response(content=None, embed=embed)
        except httpx.RequestError as e:
            traceback.print_exc()
            embed = _create_embed("Network Error", f"Failed to communicate with the backend:\n{e}", discord.Color.red())
            await interaction.edit_original_response(content=None, embed=embed)
        except Exception as e:
            traceback.print_exc()
            embed = _create_embed("Unexpected Error", f"An unexpected error occurred:\n{e}", discord.Color.red())
            await interaction.edit_original_response(content=None, embed=embed)

    @app_commands.command(name="bind", description="Bind this channel to a server")
    @app_commands.describe(server="The name or UUID of the server")
    async def bind(self, interaction: discord.Interaction, server: str):
        await interaction.response.defer()
        try:
            servers = await self.backend.get_servers()
            target_server, error_embed = self._resolve_server(servers, server, for_routing=False)
            if error_embed:
                await interaction.edit_original_response(embed=error_embed)
                return
                
            await self.backend.bind_channel(str(interaction.channel_id), target_server["id"])
            embed = _create_embed("✅ Channel Bound", f"This channel is now bound to {target_server['name']}.", discord.Color.green())
            await interaction.edit_original_response(embed=embed)
        except Exception as e:
            traceback.print_exc()
            embed = _create_embed("Error", f"Failed to bind channel:\n{e}", discord.Color.red())
            await interaction.edit_original_response(embed=embed)

    @app_commands.command(name="unbind", description="Unbind this channel")
    async def unbind(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            await self.backend.unbind_channel(str(interaction.channel_id))
            embed = _create_embed("✅ Channel Unbound", "This channel is no longer bound to any server.", discord.Color.green())
            await interaction.edit_original_response(embed=embed)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                embed = _create_embed("Not Bound", "This channel is not currently bound.", discord.Color.yellow())
                await interaction.edit_original_response(embed=embed)
            else:
                embed = _create_embed("Error", f"Failed to unbind channel:\n{e}", discord.Color.red())
                await interaction.edit_original_response(embed=embed)
        except Exception as e:
            traceback.print_exc()
            embed = _create_embed("Error", f"Failed to unbind channel:\n{e}", discord.Color.red())
            await interaction.edit_original_response(embed=embed)

    @app_commands.command(name="global", description="Mark this channel as global")
    async def global_channel(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            guild_id = str(interaction.guild_id) if interaction.guild_id else "0"
            await self.backend.set_global_channel(guild_id, str(interaction.channel_id))
            embed = _create_embed("✅ Global Channel Set", "This channel is now the global management channel.", discord.Color.green())
            await interaction.edit_original_response(embed=embed)
        except Exception as e:
            traceback.print_exc()
            embed = _create_embed("Error", f"Failed to set global channel:\n{e}", discord.Color.red())
            await interaction.edit_original_response(embed=embed)

    context_group = app_commands.Group(name="context", description="Manage context limits")

    @context_group.command(name="info", description="View context information")
    async def context_info(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            guild_id = str(interaction.guild_id) if interaction.guild_id else "0"
            info = await self.backend.get_context_info(str(interaction.channel_id), guild_id)
            embed = _create_embed("ℹ️ Context Information", "", discord.Color.blue())
            embed.add_field(name="Bound Server", value=info["server_name"], inline=False)
            embed.add_field(name="Context Limit", value=str(info["chat_context_limit"]), inline=False)
            embed.add_field(name="Stored Messages", value=str(info["message_count"]), inline=False)
            embed.add_field(name="Is Global", value="Yes" if info["is_global"] else "No", inline=False)
            await interaction.edit_original_response(embed=embed)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                embed = _create_embed("Not Bound", "This channel is not currently bound to any server.", discord.Color.yellow())
                await interaction.edit_original_response(embed=embed)
            else:
                embed = _create_embed("Error", f"Failed to retrieve context info:\n{e}", discord.Color.red())
                await interaction.edit_original_response(embed=embed)
        except Exception as e:
            traceback.print_exc()
            embed = _create_embed("Error", f"Failed to retrieve context info:\n{e}", discord.Color.red())
            await interaction.edit_original_response(embed=embed)

    @context_group.command(name="set", description="Set context limit")
    @app_commands.describe(limit="The new message context limit")
    async def context_set(self, interaction: discord.Interaction, limit: int):
        await interaction.response.defer()
        if limit <= 0:
            embed = _create_embed("Invalid Limit", "Limit must be a positive integer.", discord.Color.red())
            await interaction.edit_original_response(embed=embed)
            return
            
        try:
            await self.backend.update_context_limit(str(interaction.channel_id), limit)
            embed = _create_embed("✅ Context Limit Updated", f"The context limit is now {limit}.", discord.Color.green())
            await interaction.edit_original_response(embed=embed)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                embed = _create_embed("Not Bound", "This channel is not currently bound.", discord.Color.yellow())
                await interaction.edit_original_response(embed=embed)
            else:
                embed = _create_embed("Error", f"Failed to update context limit:\n{e}", discord.Color.red())
                await interaction.edit_original_response(embed=embed)
        except Exception as e:
            traceback.print_exc()
            embed = _create_embed("Error", f"Failed to update context limit:\n{e}", discord.Color.red())
            await interaction.edit_original_response(embed=embed)

    @app_commands.command(name="clearchatcontext", description="Clear short-term context for this channel")
    async def clearchatcontext(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            await self.backend.clear_chat_context(str(interaction.channel_id))
            embed = _create_embed("✅ Context Cleared", "Short-term chat context has been cleared. (Cognee memory and bindings are untouched).", discord.Color.green())
            await interaction.edit_original_response(embed=embed)
        except Exception as e:
            traceback.print_exc()
            embed = _create_embed("Error", f"Failed to clear context:\n{e}", discord.Color.red())
            await interaction.edit_original_response(embed=embed)

class ZenCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.tree.add_command(ZenGroup())

async def setup(bot):
    await bot.add_cog(ZenCog(bot))
