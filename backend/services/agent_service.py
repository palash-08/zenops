import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from repositories.server_repository import ServerRepository
from services.openclaw_client import OpenClawClient, OpenClawError


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

    async def run_discovery(self, server_id: uuid.UUID) -> dict:
        import json
        from models.inventory import ServerInventory
        
        prompt = (
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
            "    \"nginx\": true\n"
            "  }\n"
            "}\n"
            "Requirements:\n"
            "- Return JSON only.\n"
            "- No markdown.\n"
            "- No explanations.\n"
            "- No additional text."
        )
        
        response_data = await self.execute_prompt(server_id, prompt)
        
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
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to extract assistant response from payload."
            )
            
        # Attempt to strip markdown if LLM accidentally added it
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
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Assistant returned invalid JSON."
            )
            
        if not all(k in parsed for k in ("hostname", "summary", "services")):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="JSON missing required keys (hostname, summary, services)."
            )
            
        # DB Update (Idempotent)
        inventory = self.repository.db.query(ServerInventory).filter(ServerInventory.server_id == server_id).first()
        if not inventory:
            inventory = ServerInventory(server_id=server_id)
            self.repository.db.add(inventory)
            
        inventory.hostname = parsed["hostname"]
        inventory.summary = parsed["summary"]
        inventory.services = parsed["services"]
        inventory.raw_response = raw_text
        
        self.repository.db.commit()
        self.repository.db.refresh(inventory)
        
        return {
            "server_id": inventory.server_id,
            "hostname": inventory.hostname,
            "summary": inventory.summary,
            "services": inventory.services,
            "updated_at": inventory.updated_at
        }
