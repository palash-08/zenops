import traceback
import discord
from urllib.parse import urlparse
from services.backend_client import BackendClient
from commands.utils import _create_embed


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

            servers = await self.backend.get_servers()
            new_name = self.server_name.value.strip()

            for s in servers:
                if s["name"].lower() == new_name.lower():
                    embed = _create_embed("Duplicate Server", f"A server with the name '{new_name}' already exists.", discord.Color.yellow())
                    await interaction.followup.send(embed=embed)
                    return

                existing_url = f"https://{s['tailscale_ip']}:{s['gateway_port']}"
                if s["tailscale_ip"] == host and s["gateway_port"] == port:
                    embed = _create_embed("Duplicate Server", f"A server with the Gateway URL `{existing_url}` is already registered.", discord.Color.yellow())
                    await interaction.followup.send(embed=embed)
                    return

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

            embed = discord.Embed(
                title="Server registered successfully.\n\nInitializing server memory in the background...",
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

        except Exception:
            traceback.print_exc()
            embed = _create_embed("Registration Error", "An unexpected error occurred during server registration.", discord.Color.red())
            await interaction.followup.send(embed=embed)
