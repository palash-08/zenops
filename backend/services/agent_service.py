import uuid
import json
import logging
import asyncio
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from repositories.server_repository import ServerRepository
from services.openclaw_client import OpenClawClient, OpenClawError
from services.memory_service import MemoryService
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

REQUIRED_SERVICES = list(DISPLAY_NAMES.keys())

logger = logging.getLogger(__name__)

class AgentService:
    def __init__(self, db: Session):
        self.repository = ServerRepository(db)
        self.memory_service = MemoryService()

    async def execute_prompt(self, server_id: uuid.UUID, prompt: str) -> dict:
        server = self.repository.get_server_by_id(server_id)
        
        if not server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Server not found."
            )

        memories = await self.memory_service.recall(server, prompt)
        
        augmented_prompt = (
            "You are ZenOps, an AI-powered DevOps assistant managing a live Linux server.\n\n"
            "CRITICAL OPERATING RULES - HOW TO USE MEMORY VS. LIVE COMMANDS:\n"
            "1. Live server state is ALWAYS your primary source of truth.\n"
            "2. Use MEMORY ONLY for: previous discoveries, historical observations, user preferences, saved notes, UUIDs, infrastructure inventory, and long-term context.\n"
            "3. If a question concerns ANYTHING that can change over time (e.g., 'Is Docker running?', 'Is Tailscale installed?', 'What is CPU usage?'), you MUST verify it using Linux shell commands before answering.\n"
            "4. If both memory and live inspection are useful:\n"
            "   - Recall the memory.\n"
            "   - Verify it against the live server using shell commands.\n"
            "   - Prefer the live information if they disagree.\n"
            "   - Inform the user that the memory was outdated if necessary.\n"
            "5. NEVER answer operational or state-based questions solely from memory.\n"
            "6. Whenever shell commands are available, ALWAYS prefer verification over assumptions.\n\n"
            "####################################\n"
            "SERVER MEMORY\n"
            "####################################\n\n"
            "Relevant previous observations:\n\n"
            f"{memories}\n\n"
            "####################################\n"
            "CURRENT REQUEST\n"
            "####################################\n\n"
            f"{prompt}"
        )

        client = OpenClawClient(
            gateway_url=server.gateway_url,
            gateway_token=server.gateway_token
        )
        
        try:
            response_data = await client.create_response(
                payload={
                    "model": "openclaw/default",
                    "input": augmented_prompt,
                }
            )
            
            try:
                response_text = self._extract_output_text(response_data)
                asyncio.create_task(self.memory_service.remember_conversation(server, prompt, response_text))
            except Exception as e:
                logger.warning(f"Could not extract text for conversation memory: {e}")
                
            return response_data
        except OpenClawError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(e)
            )
        finally:
            await client.close()

    def _extract_output_text(self, response_data: dict) -> str:
        try:
            for message in response_data.get("output", []):
                if message.get("type") == "message" or message.get("role") == "assistant":
                    for content in message.get("content", []):
                        if content.get("type") == "output_text" and content.get("text"):
                            return content["text"]
        except Exception as e:
            logger.error(f"Error extracting output text: {e}")
            
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to extract assistant response from payload."
        )

    async def run_discovery(self, server_id: uuid.UUID) -> ServerInventory:
        response_data = await self.execute_prompt(server_id, DISCOVERY_PROMPT)
        
        raw_text = self._extract_output_text(response_data)
        logger.debug(f"Raw discovery response for server {server_id}:\n{raw_text}")
            
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
            logger.debug(f"Parsed JSON for server {server_id}: {parsed}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed for server {server_id}: {e}\nCleaned text: {clean_text}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Invalid JSON returned by assistant."
            )
            
        if not isinstance(parsed, dict):
            logger.error(f"Parsed JSON is not a dictionary for server {server_id}. Type: {type(parsed)}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="JSON response must be an object."
            )
            
        hostname = parsed.get("hostname")
        if not isinstance(hostname, str):
            logger.error(f"Validation failed: hostname missing or not a string for server {server_id}.")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Validation failed: hostname missing."
            )
            
        services = parsed.get("services")
        if not isinstance(services, dict):
            logger.error(f"Validation failed: services missing or not a dictionary for server {server_id}.")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Validation failed: services missing."
            )
            
        normalized_services = {}
        for k in REQUIRED_SERVICES:
            val = services.get(k, False)
            if isinstance(val, bool):
                normalized_services[k] = val
            elif isinstance(val, int) and val in (0, 1):
                normalized_services[k] = bool(val)
            elif isinstance(val, str):
                v_lower = val.strip().lower()
                if v_lower in ("true", "yes", "1"):
                    normalized_services[k] = True
                elif v_lower in ("false", "no", "0"):
                    normalized_services[k] = False
                else:
                    logger.warning(f"Unrecognized boolean value '{val}' for service '{k}' on server {server_id}. Defaulting to False.")
                    normalized_services[k] = False
            else:
                logger.warning(f"Unrecognized type {type(val)} for service '{k}' on server {server_id}. Defaulting to False.")
                normalized_services[k] = False
            
        active_services = [DISPLAY_NAMES.get(k, k.replace('_', ' ').title()) for k, v in normalized_services.items() if v]
        if active_services:
            if len(active_services) > 1:
                summary = f"Detected {', '.join(active_services[:-1])} and {active_services[-1]}."
            else:
                summary = f"Detected {active_services[0]}."
        else:
            summary = "No recognized services detected."

        inventory = self.repository.upsert_inventory(
            server_id=server_id,
            hostname=hostname,
            summary=summary,
            services=normalized_services,
            raw_response=raw_text
        )
        
        server = self.repository.get_server_by_id(server_id)
        if server:
            asyncio.create_task(
                self.memory_service.remember_discovery(
                    server=server,
                    hostname=hostname,
                    services=normalized_services,
                    summary=summary
                )
            )
        
        return inventory

