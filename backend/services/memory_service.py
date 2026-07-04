import logging
from datetime import datetime, timezone
from typing import Any

from services.cognee_client import CogneeClient, CogneeError
from models.server import Server

logger = logging.getLogger(__name__)


class MemoryService:
    """
    High-level service that manages all memory operations for the ZenOps backend.
    This service is the ONLY component allowed to use CogneeClient directly.
    """
    
    def __init__(self):
        self.cognee = CogneeClient()
        
    async def recall(self, server: Server, query: str, limit: int = 5) -> str:
        """
        Recall relevant memories for the server. 
        Returns a formatted string of memories, or a fallback message if it fails.
        """
        try:
            if not server.cognee_dataset_id:
                return ""
                
            memories = await self.cognee.recall(
                query=query,
                dataset_id=str(server.cognee_dataset_id),
                limit=limit
            )
            
            if not memories:
                return ""
                
            formatted_memories = []
            for mem in memories:
                text = mem.get("text", "")
                if text:
                    formatted_memories.append(f"- {text}")
                    
            if not formatted_memories:
                return ""
                
            return "\n".join(formatted_memories)
            
        except CogneeError as e:
            logger.warning(f"Failed to recall memories (non-blocking): {e}")
            return "Failed to access memory system."
            
    async def remember_conversation(self, server: Server, prompt: str, response: str):
        """
        Remember a conversation flow.
        Should be executed in the background to avoid blocking execution.
        """
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            hostname = server.inventory.hostname if server.inventory else "Unknown"
            
            text = (
                f"Server ID: {server.id}\n"
                f"Hostname: {hostname}\n"
                f"Memory Type: conversation\n"
                f"Timestamp: {timestamp}\n\n"
                f"User:\n{prompt}\n\nAssistant:\n{response}"
            )
            
            if not server.cognee_dataset_id:
                logger.warning(f"Server {server.id} has no memory dataset initialized.")
                return

            await self.cognee.remember(
                text=text, 
                dataset_id=str(server.cognee_dataset_id),
                self_improvement=False
            )
            logger.info(f"Successfully stored conversation memory for server {server.id}")
            
        except CogneeError as e:
            logger.warning(f"Failed to remember conversation (non-blocking): {e}")
            
    async def remember_discovery(self, server: Server, hostname: str, services: dict[str, Any], summary: str):
        """
        Remember a discovery event.
        Should be executed in the background.
        """
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            active_services = [k for k, v in services.items() if v]
            
            text = (
                f"Server ID: {server.id}\n"
                f"Hostname: {hostname}\n"
                f"Memory Type: discovery\n"
                f"Timestamp: {timestamp}\n\n"
                f"Server hostname is {hostname}. Installed/Running services: {', '.join(active_services)}. Summary: {summary}"
            )
            
            if not server.cognee_dataset_id:
                logger.warning(f"Server {server.id} has no memory dataset initialized.")
                return

            await self.cognee.remember(
                text=text, 
                dataset_id=str(server.cognee_dataset_id),
                self_improvement=True
            )
            logger.info(f"Successfully stored discovery memory for server {server.id}")
            
        except CogneeError as e:
            logger.warning(f"Failed to remember discovery (non-blocking): {e}")
            
    async def forget(self, memory_id: str, server: Server):
        """Forget a specific memory by ID."""
        try:
            if not server.cognee_dataset_id:
                logger.warning(f"Server {server.id} has no memory dataset initialized.")
                return
                
            await self.cognee.forget(memory_id, str(server.cognee_dataset_id))
        except CogneeError as e:
            logger.warning(f"Failed to forget memory (non-blocking): {e}")
