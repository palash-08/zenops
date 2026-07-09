import discord
import httpx
import traceback
from services.backend_client import BackendClient
from commands.utils import _create_embed


class DeleteConfirmView(discord.ui.View):
    def __init__(self, backend_client: BackendClient, server_id: str, server_name: str, owner_id: int):
        super().__init__(timeout=60.0)
        self.backend = backend_client
        self.server_id = server_id
        self.server_name = server_name
        self.owner_id = owner_id
        self.message = None

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("You didn't initiate this deletion.", ephemeral=True)
            return

        self.stop()
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

        try:
            await self.backend.delete_server(self.server_id)
            embed = _create_embed(
                "Server Deleted",
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

        self.stop()
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
