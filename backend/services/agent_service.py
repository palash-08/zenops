import uuid
import json
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from repositories.server_repository import ServerRepository
from services.openclaw_client import OpenClawClient, OpenClawError
from models.inventory import ServerInventory

DISCOVERY_PROMPT = (
    "You are running directly on the managed Linux server.\n"
    "Inspect this machine.\n"
    "Identify the major infrastructure software that is installed or actively running.\n"
    "Return ONLY valid JSON.\n"
    "Example:\n"
    "{\n"
    "  \"hostname\": \"instance-20250711-1158\",\n"
    "  \"summary\": \"Ubuntu production server running Docker, Nginx and Pterodactyl.\",\n"
    "  \"services\": {\n"
    "    \"docker\": true,\n"
    "    \"nginx\": true,\n"
    "    \"postgresql\": true,\n"
    "    \"redis\": true,\n"
    "    \"pterodactyl\": true\n"
    "  }\n"
    "}\n"
    "Requirements:\n"
    "- Return JSON only.\n"
    "- No markdown.\n"
    "- No explanations.\n"
    "- No additional text."
)


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
            
        try:
            parsed = json.loads(raw_text)
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
            
        if not isinstance(parsed.get("summary"), str):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Validation failed: summary is missing or not a string."
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
            
        # DB Update (Idempotent)
        inventory = self.repository.db.query(ServerInventory).filter(ServerInventory.server_id == server_id).first()
        if not inventory:
            inventory = ServerInventory(server_id=server_id)
            self.repository.db.add(inventory)
            
        inventory.hostname = parsed["hostname"]
        inventory.summary = parsed["summary"]
        inventory.services = services
        inventory.raw_response = raw_text
        
        self.repository.db.commit()
        self.repository.db.refresh(inventory)
        
        return inventory

