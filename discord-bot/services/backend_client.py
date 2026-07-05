import httpx
from typing import Any
from core.config import settings

class BackendClient:
    def __init__(self):
        self.base_url = settings.backend_url.rstrip("/")
    
    async def get_servers(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/servers")
            response.raise_for_status()
            return response.json()
            
    async def register_server(self, payload: dict) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self.base_url}/servers", json=payload)
            response.raise_for_status()
            return response.json()
            
    async def execute_prompt(self, server_id: str, prompt: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self.base_url}/servers/{server_id}/execute",
                json={"prompt": prompt}
            )
            response.raise_for_status()
            return response.json()

    async def run_discovery(self, server_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(f"{self.base_url}/servers/{server_id}/discover")
            response.raise_for_status()
            return response.json()

    async def delete_server(self, server_id: str) -> None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(f"{self.base_url}/servers/{server_id}")
            response.raise_for_status()

    async def bind_channel(self, channel_id: str, server_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/internal/bindings/{channel_id}",
                json={"server_id": server_id}
            )
            response.raise_for_status()
            return response.json()

    async def unbind_channel(self, channel_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"{self.base_url}/internal/bindings/{channel_id}")
            response.raise_for_status()
            return response.json()

    async def set_global_channel(self, guild_id: str, channel_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}/internal/guilds/{guild_id}/global",
                json={"discord_channel_id": channel_id}
            )
            response.raise_for_status()
            return response.json()

    async def update_context_limit(self, channel_id: str, limit: int) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}/internal/bindings/{channel_id}/context-limit",
                json={"limit": limit}
            )
            response.raise_for_status()
            return response.json()

    async def clear_chat_context(self, channel_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"{self.base_url}/internal/bindings/{channel_id}/context")
            response.raise_for_status()
            return response.json()

    async def get_context_info(self, channel_id: str, guild_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/internal/bindings/{channel_id}/context-info",
                params={"guild_id": guild_id}
            )
            response.raise_for_status()
            return response.json()

    async def execute_agent_prompt(self, guild_id: str, channel_id: str, prompt: str) -> dict:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self.base_url}/agent/execute",
                json={
                    "guild_id": guild_id,
                    "discord_channel_id": channel_id,
                    "prompt": prompt
                }
            )
            response.raise_for_status()
            return response.json()
