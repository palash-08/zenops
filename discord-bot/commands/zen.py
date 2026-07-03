import discord
from discord.ext import commands
from discord import app_commands
from services.backend_client import BackendClient
from urllib.parse import urlparse
import httpx
import traceback
import io

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
            
            response = await self.backend.register_server(payload)
            
            # 4. Better Success Embed
            embed = discord.Embed(
                title="✅ Server Registered",
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


class ZenGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="zen", description="ZenOps orchestration commands")
        self.backend = BackendClient()

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
            # 1. Fetch all registered servers
            servers = await self.backend.get_servers()
            
            # 2. Check server count
            if len(servers) == 0:
                embed = _create_embed(
                    "No Servers Found",
                    "No servers are currently registered.\nPlease run `/zen register` to add one.",
                    discord.Color.yellow()
                )
                await interaction.followup.send(embed=embed)
                return
                
            if len(servers) > 1:
                desc = "Multiple servers are currently registered.\n\nAutomatic routing is not available yet.\n\nRegistered servers:\n\n"
                for s in servers:
                    desc += f"• {s['name']}\n"
                embed = _create_embed(
                    "Routing Not Implemented",
                    desc,
                    discord.Color.yellow()
                )
                await interaction.followup.send(embed=embed)
                return
                
            # 3. Exactly one server exists
            target_server = servers[0]
            
            # 4. Execute the prompt
            response_data = await self.backend.execute_prompt(
                server_id=target_server["id"],
                prompt=prompt
            )
            
            # 5. Extract assistant output
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
                
            # 6. Display in a Discord embed
            embed = discord.Embed(
                title="🤖 ZenOps",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Executed on:\n{target_server['name']}")
            
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

    @app_commands.command(name="discover", description="Discover infrastructure on a registered server")
    @app_commands.describe(server="The name or UUID of the server (optional if only one exists)")
    async def discover(self, interaction: discord.Interaction, server: str = None):
        await interaction.response.defer()
        
        try:
            # 1. Fetch all registered servers
            servers = await self.backend.get_servers()
            
            if len(servers) == 0:
                embed = _create_embed(
                    "No Servers Found",
                    "No servers are currently registered.\nPlease run `/zen register` to add one.",
                    discord.Color.yellow()
                )
                await interaction.followup.send(embed=embed)
                return
                
            target_server = None
            if len(servers) == 1:
                target_server = servers[0]
            else:
                if not server:
                    embed = _create_embed(
                        "Multiple Servers Found",
                        "Multiple servers are registered. Please specify the server name or UUID.",
                        discord.Color.yellow()
                    )
                    await interaction.followup.send(embed=embed)
                    return
                
                # server lookup logic
                for s in servers:
                    if s["id"] == server or str(s["id"]).startswith(server) or s["name"].lower() == server.lower():
                        target_server = s
                        break
                        
                if not target_server:
                    embed = _create_embed("Server Not Found", f"Server '{server}' not found.", discord.Color.red())
                    await interaction.followup.send(embed=embed)
                    return

            msg = await interaction.followup.send("🔍 Discovering infrastructure...")
            
            inventory_data = await self.backend.run_discovery(target_server["id"])
            
            embed = discord.Embed(
                title="✅ Infrastructure Discovery Complete",
                color=discord.Color.green()
            )
            embed.add_field(name="Server", value=target_server["name"], inline=False)
            
            hostname = inventory_data.get("hostname", "Unknown")
            embed.add_field(name="Hostname", value=hostname, inline=False)
            
            services = inventory_data.get("services", {})
            services_text = "\n".join([f"• {k.capitalize()}" for k, v in services.items() if v])
            if not services_text:
                services_text = "No services detected."
            
            embed.add_field(name="Detected Services", value=services_text, inline=False)
            
            summary = inventory_data.get("summary", "No summary provided.")
            embed.add_field(name="Summary", value=summary, inline=False)
            
            embed.set_footer(text="Infrastructure inventory updated successfully.")
            
            await msg.edit(content=None, embed=embed)
            
        except httpx.HTTPStatusError as e:
            traceback.print_exc()
            if e.response.status_code == 500:
                embed = _create_embed("Execution Failed", "Backend returned an internal server error or invalid JSON (HTTP 500).", discord.Color.red())
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


class ZenCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.tree.add_command(ZenGroup())

async def setup(bot):
    await bot.add_cog(ZenCog(bot))
