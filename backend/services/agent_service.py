import uuid
import json
import logging
import asyncio
from fastapi import HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from repositories.server_repository import ServerRepository
from services.openclaw_client import OpenClawClient, OpenClawError
from services.memory_service import MemoryService
from models.inventory import ServerInventory
from services.execution_resolver import ExecutionResolver
from services.prompt_builder import PromptBuilder
from services.binding_service import BindingService

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
        self.db = db
        self.repository = ServerRepository(db)
        self.memory_service = MemoryService()
        self.execution_resolver = ExecutionResolver(db)
        self.binding_service = BindingService(db)
        self.prompt_builder = PromptBuilder()

    async def orchestrate_execution(self, guild_id: str, discord_channel_id: str, prompt: str, background_tasks: BackgroundTasks) -> dict:
        # 1. Resolve Target
        target = self.execution_resolver.resolve(guild_id, discord_channel_id)
        
        if target.mode == "GLOBAL":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Global orchestration has not yet been implemented."
            )
            
        server_id = target.server_id
        server = self.repository.get_server_by_id(server_id)
        if not server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Server not found."
            )
            
        # 2. Load Context (if BOUND)
        recent_messages = []
        memories = ""
        if target.mode == "BOUND":
            recent_messages = self.binding_service.get_recent_messages(discord_channel_id)
            # 3. Load Memories
            memories = await self.memory_service.recall(server, prompt)
        
        # 4. Build Prompt
        prompt_context = self.prompt_builder.build(server, memories, recent_messages, prompt)
        
        # 5. Execute
        client = OpenClawClient(
            gateway_url=server.gateway_url,
            gateway_token=server.gateway_token
        )
        try:
            response_data = await client.create_response(
                payload={
                    "model": "openclaw/default",
                    "input": prompt_context.final_prompt,
                }
            )
            
            try:
                response_text = self._extract_output_text(response_data)
                
                # 6. Persist Conversation (if BOUND)
                if target.mode == "BOUND":
                    try:
                        self.binding_service.append_message(discord_channel_id, server_id, "user", prompt)
                        self.binding_service.append_message(discord_channel_id, server_id, "assistant", response_text)
                    except Exception as e:
                        logger.error(f"Failed to persist conversation message: {e}")
                    
                    # 7. Trigger Background Memory
                    background_tasks.add_task(self.memory_service.remember_conversation, server, prompt, response_text)
            except Exception as e:
                logger.warning(f"Could not extract text for conversation memory: {e}")
                
            # 8. Return Response
            return response_data
        except OpenClawError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(e)
            )
        finally:
            await client.close()

    async def execute_prompt(self, server_id: uuid.UUID, prompt: str) -> dict:
        server = self.repository.get_server_by_id(server_id)
        
        if not server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Server not found."
            )

        memories = await self.memory_service.recall(server, prompt)
        
        prompt_context = self.prompt_builder.build(server, memories, [], prompt)

        client = OpenClawClient(
            gateway_url=server.gateway_url,
            gateway_token=server.gateway_token
        )
        
        try:
            response_data = await client.create_response(
                payload={
                    "model": "openclaw/default",
                    "input": prompt_context.final_prompt,
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

