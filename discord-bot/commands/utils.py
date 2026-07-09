import traceback
import discord
import httpx


def _create_embed(title: str, description: str, color: discord.Color) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=color)


async def handle_backend_errors(interaction, coro, edit: bool = False, followup: bool = False):
    try:
        return await coro
    except httpx.HTTPStatusError as e:
        traceback.print_exc()
        if e.response.status_code == 400:
            try:
                error_detail = e.response.json().get("detail", "Bad Request")
            except Exception:
                error_detail = "Bad Request"
            embed = _create_embed("Routing Error", error_detail, discord.Color.yellow())
        elif e.response.status_code == 404:
            embed = _create_embed("Execution Failed", "Server not found (HTTP 404).", discord.Color.red())
        elif e.response.status_code == 500:
            embed = _create_embed("Execution Failed", "Backend returned an internal server error (HTTP 500).", discord.Color.red())
        elif e.response.status_code == 502:
            embed = _create_embed("Execution Failed", "Backend is unavailable or returning Bad Gateway (HTTP 502).", discord.Color.red())
        else:
            embed = _create_embed("Execution Failed", f"Backend returned an error: HTTP {e.response.status_code}", discord.Color.red())
    except httpx.TimeoutException:
        traceback.print_exc()
        embed = _create_embed("Network Timeout", "The request to the backend timed out.", discord.Color.red())
    except httpx.RequestError as e:
        traceback.print_exc()
        embed = _create_embed("Network Error", f"Failed to communicate with the backend:\n{e}", discord.Color.red())
    except Exception as e:
        traceback.print_exc()
        embed = _create_embed("Unexpected Error", f"An unexpected error occurred:\n{e}", discord.Color.red())

    if edit:
        await interaction.edit_original_response(content=None, embed=embed)
    elif followup:
        await interaction.followup.send(embed=embed)
    else:
        await interaction.response.send_message(embed=embed)
    return None
