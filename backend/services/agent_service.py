import uuid
import json
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from repositories.server_repository import ServerRepository
from services.openclaw_client import OpenClawClient, OpenClawError
from models.inventory import ServerInventory

DISCOVERY_PROMPT = (
    "You are running directly on the managed Linux server.\n"
    "Use Linux shell commands ONLY.\n"
    "Determine whether each of the following software packages is installed or currently running:\n"
    "- Docker\n"
    "- Docker Compose\n"
    "- Nginx\n"
    "- Apache\n"
    "- PostgreSQL\n"
    "- MySQL / MariaDB\n"
    "- Redis\n"
    "- Pterodactyl\n"
    "- Wings\n"
    "- Tailscale\n"
    "Also determine the hostname.\n"
    "Rules:\n"
    "- Return true if the software is installed OR running.\n"
    "- Return false otherwise.\n"
    "- Never return version numbers.\n"
    "- Never return explanatory text.\n"
    "- Never return markdown.\n"
    "- Never return code fences.\n"
    "- Never explain your reasoning.\n"
    "- Return ONLY the JSON object.\n"
    "Required schema:\n"
    "{\n"
    "  \"hostname\": \"...\",\n"
    "  \"services\": {\n"
    "    \"docker\": true,\n"
    "    \"docker_compose\": true,\n"
    "    \"nginx\": false,\n"
    "    \"apache\": false,\n"
    "    \"postgresql\": false,\n"
    "    \"mysql\": true,\n"
    "    \"redis\": true,\n"
    "    \"pterodactyl\": false,\n"
    "    \"wings\": false,\n"
    "    \"tailscale\": true\n"
    "  }\n"
    "}\n"
)

DISPLAY_NAMES = {
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "docker_compose": "Docker Compose",
    "tailscale": "Tailscale",
    "pterodactyl": "Pterodactyl",
    "docker": "Docker",
    "nginx": "Nginx",
    "apache": "Apache",
    "redis": "Redis",
    "wings": "Wings"
}


class AgentService:
    def __init__(self, db: Session):
        self.repository = ServerRepository(db)

    async def execute_prompt(self, server_id: uuid.UUID, prompt: str) -> dict:
        server = self.repository.get_server_by_id(server_id)
        
        if not server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Server not found."
            )

        client = OpenClawClient(
            gateway_url=server.gateway_url,
            gateway_token=server.gateway_token
        )
        
        try:
            response_data = await client.create_response(
                payload={
                    "model": "openclaw/default",
                    "input": prompt,
    }
)
            return response_data
        except OpenClawError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(e)
            )
        finally:
            await client.close()

    async def run_discovery(self, server_id: uuid.UUID) -> ServerInventory:
        response_data = await self.execute_prompt(server_id, DISCOVERY_PROMPT)
        
        raw_text = None
        try:
            outputs = response_data.get("output", [])
            for out in outputs:
                if out.get("type") == "message" or out.get("role") == "assistant":
                    for content_item in out.get("content", []):
                        if content_item.get("type") == "output_text":
                            raw_text = content_item.get("text")
                            break
                    if raw_text:
                        break
        except Exception:
            pass

        if not raw_text:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to extract assistant response from payload."
            )
            
        clean_text = raw_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()
            
        try:
            parsed = json.loads(clean_text)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Assistant returned invalid JSON."
            )
            
        if not isinstance(parsed, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="JSON response must be an object."
            )
            
        if not isinstance(parsed.get("hostname"), str):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Validation failed: hostname is missing or not a string."
            )
            
        services = parsed.get("services")
        if not isinstance(services, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Validation failed: services is missing or not a dictionary."
            )
            
        for k, v in services.items():
            if not isinstance(v, bool):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Validation failed: service '{k}' value must be a boolean."
                )
            
        active_services = [DISPLAY_NAMES.get(k, k.replace('_', ' ').title()) for k, v in services.items() if v]
        if active_services:
            if len(active_services) > 1:
                summary = f"Detected {', '.join(active_services[:-1])} and {active_services[-1]}."
            else:
                summary = f"Detected {active_services[0]}."
        else:
            summary = "No recognized services detected."

        # DB Update (Idempotent)
        inventory = self.repository.db.query(ServerInventory).filter(ServerInventory.server_id == server_id).first()
        if not inventory:
            inventory = ServerInventory(server_id=server_id)
            self.repository.db.add(inventory)
            
        inventory.hostname = parsed["hostname"]
        inventory.summary = summary
        inventory.services = services
        inventory.raw_response = raw_text
        
        try:
            self.repository.db.commit()
            self.repository.db.refresh(inventory)
        except Exception:
            self.repository.db.rollback()
            raise
        
        return inventory

