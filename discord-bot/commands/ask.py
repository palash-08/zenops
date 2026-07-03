import discord
from discord.ext import commands
from discord import app_commands
import httpx
from services.backend_client import BackendClient

class AskCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.backend = BackendClient()

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
                await interaction.edit_original_response(content=f"❌ Server '{server}' not found.")
                return

            # 2. Execute the prompt
            response_data = await self.backend.execute_prompt(
                server_id=target_server["id"],
                prompt=prompt
            )
            
            # 3. Extract assistant's final text
            # OpenResponses schema: {"output": [{"role": "assistant", "content": [{"type": "output_text", "text": "..."}]}]}
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
            # Ensure it fits within Discord's 2000 character limit
            if len(assistant_text) > 1990:
                assistant_text = assistant_text[:1990] + "..."
                
            await interaction.edit_original_response(content=assistant_text)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 502:
                await interaction.edit_original_response(content="❌ Gateway unavailable or unreachable (HTTP 502).")
            elif e.response.status_code == 404:
                await interaction.edit_original_response(content="❌ Server not found on backend (HTTP 404).")
            else:
                await interaction.edit_original_response(content=f"❌ Backend returned an error: HTTP {e.response.status_code}")
        except httpx.TimeoutException:
            await interaction.edit_original_response(content="❌ Request timed out. The backend or provider took too long to respond.")
        except httpx.RequestError as e:
            await interaction.edit_original_response(content=f"❌ Failed to communicate with the backend: {e}")
        except Exception as e:
            await interaction.edit_original_response(content=f"❌ An unexpected error occurred: {e}")

async def setup(bot):
    await bot.add_cog(AskCog(bot))
