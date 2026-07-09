import httpx
from typing import Any
from core.config import settings

class BackendClient:
    def __init__(self):
        self.base_url = settings.backend_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=30.0)
        self._internal_headers = {"X-Internal-Auth": settings.internal_auth_token}

    async def close(self):
        await self._client.aclose()

    async def _request(self, method: str, path: str, internal: bool = False, **kwargs) -> Any:
        url = f"{self.base_url}{path}"
        if internal:
            headers = kwargs.pop("headers", {})
            headers.update(self._internal_headers)
            kwargs["headers"] = headers
        response = await self._client.request(method, url, **kwargs)
        response.raise_for_status()
        if response.status_code == 204:
            return None
        return response.json()

    async def get_servers(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/servers")

    async def register_server(self, payload: dict) -> dict[str, Any]:
        return await self._request("POST", "/servers", json=payload)

    async def execute_prompt(self, server_id: str, prompt: str) -> dict[str, Any]:
        return await self._request("POST", f"/servers/{server_id}/execute", json={"prompt": prompt}, timeout=httpx.Timeout(300.0))

    async def run_discovery(self, server_id: str) -> dict[str, Any]:
        return await self._request("POST", f"/servers/{server_id}/discover", timeout=httpx.Timeout(300.0))

    async def delete_server(self, server_id: str) -> None:
        await self._request("DELETE", f"/servers/{server_id}")

    async def bind_channel(self, channel_id: str, server_id: str) -> dict:
        return await self._request("POST", f"/internal/bindings/{channel_id}", internal=True, json={"server_id": server_id})

    async def unbind_channel(self, channel_id: str) -> dict:
        return await self._request("DELETE", f"/internal/bindings/{channel_id}", internal=True)

    async def set_global_channel(self, guild_id: str, channel_id: str) -> dict:
        return await self._request("PUT", f"/internal/guilds/{guild_id}/global", internal=True, json={"discord_channel_id": channel_id})

    async def update_context_limit(self, channel_id: str, limit: int) -> dict:
        return await self._request("PUT", f"/internal/bindings/{channel_id}/context-limit", internal=True, json={"limit": limit})

    async def clear_chat_context(self, channel_id: str) -> dict:
        return await self._request("DELETE", f"/internal/bindings/{channel_id}/context", internal=True)

    async def get_context_info(self, channel_id: str, guild_id: str) -> dict:
        return await self._request("GET", f"/internal/bindings/{channel_id}/context-info", internal=True, params={"guild_id": guild_id})

    async def execute_agent_prompt(self, guild_id: str, channel_id: str, prompt: str) -> dict:
        return await self._request("POST", "/agent/execute", json={"guild_id": guild_id, "discord_channel_id": channel_id, "prompt": prompt}, timeout=httpx.Timeout(300.0))
