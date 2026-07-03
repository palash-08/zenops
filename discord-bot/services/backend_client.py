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
