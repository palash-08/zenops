import discord
from discord.ext import commands
from discord import app_commands
import httpx
import io
from services.backend_client import BackendClient

class AskCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.backend = BackendClient()

    async def cog_unload(self):
        await self.backend.close()

    def _create_error_embed(self, message: str) -> discord.Embed:
        return discord.Embed(
            title="Execution Failed",
            description=message,
            color=discord.Color.red()
        )

    @app_commands.command(name="ask", description="Send a prompt to a ZenOps server")
    @app_commands.describe(
        server="The name or UUID of the server",
        prompt="The natural language instruction to execute"
    )
    async def ask(self, interaction: discord.Interaction, server: str, prompt: str):
        await interaction.response.defer()
        
        try:
            # 1. Look up the server
            servers = await self.backend.get_servers()
            
            target_server = None
            for s in servers:
                if s["id"] == server or str(s["id"]).startswith(server) or s["name"].lower() == server.lower():
                    target_server = s
                    break
                    
            if not target_server:
                await interaction.edit_original_response(
                    embed=self._create_error_embed(f"❌ Server '{server}' not found.")
                )
                return

            # 2. Execute the prompt
            response_data = await self.backend.execute_prompt(
                server_id=target_server["id"],
                prompt=prompt
            )
            
            # 3. Extract assistant's final text
            assistant_text = "No text returned."
            try:
                outputs = response_data.get("output", [])
                if outputs:
                    content_list = outputs[0].get("content", [])
                    if content_list:
                        assistant_text = content_list[0].get("text", "No text returned.")
            except Exception:
                pass
            
            # 4. Display the response
            embed = discord.Embed(color=discord.Color.green())
            embed.set_footer(text=f"Server: {target_server['name']}")
            
            if len(assistant_text) > 2000:
                embed.description = "The response was too long to display and has been attached as a file."
                file_bytes = io.BytesIO(assistant_text.encode("utf-8"))
                discord_file = discord.File(file_bytes, filename="response.txt")
                
                # edit_original_response with attachments requires `attachments=[...]`
                await interaction.edit_original_response(embed=embed, attachments=[discord_file])
            else:
                embed.description = assistant_text
                await interaction.edit_original_response(embed=embed)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 502:
                msg = "❌ Gateway unavailable or unreachable (HTTP 502)."
            elif e.response.status_code == 404:
                msg = "❌ Server not found on backend (HTTP 404)."
            else:
                msg = f"❌ Backend returned an error: HTTP {e.response.status_code}"
            await interaction.edit_original_response(embed=self._create_error_embed(msg))
            
        except httpx.TimeoutException:
            msg = "❌ Request timed out. The backend or provider took too long to respond."
            await interaction.edit_original_response(embed=self._create_error_embed(msg))
            
        except httpx.RequestError as e:
            msg = f"❌ Failed to communicate with the backend: {e}"
            await interaction.edit_original_response(embed=self._create_error_embed(msg))
            
        except Exception as e:
            msg = f"❌ An unexpected error occurred: {e}"
            await interaction.edit_original_response(embed=self._create_error_embed(msg))

async def setup(bot):
    await bot.add_cog(AskCog(bot))
