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
        async with httpx.AsyncClient() as client:
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
