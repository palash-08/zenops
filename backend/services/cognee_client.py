import httpx
import logging
from typing import Any

from core.config import settings

logger = logging.getLogger(__name__)


class CogneeError(Exception):
    """Custom exception for Cognee operations."""
    pass


class CogneeClient:
    def __init__(self):
        if not settings.cognee_api_url or not settings.cognee_api_key:
            logger.warning("Cognee API configuration is missing. Memory features may fail.")
            
        self.api_url = (settings.cognee_api_url or "").rstrip("/")
        self.api_key = settings.cognee_api_key or ""
        self.headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
        }

    async def health(self) -> bool:
        """Check if the Cognee memory backend is accessible."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.api_url}/health", headers=self.headers, timeout=5.0)
                response.raise_for_status()
                return True
            except Exception as e:
                logger.error(f"Cognee health check failed: {e}")
                return False

    async def create_dataset(self, name: str) -> str:
        """Create a Cognee dataset and return its UUID."""
        async with httpx.AsyncClient() as client:
            try:
                payload = {"name": name}
                response = await client.post(
                    f"{self.api_url}/api/v1/datasets", 
                    json=payload,
                    headers=self.headers, 
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                return data.get("id")
            except Exception as e:
                logger.error(f"Cognee create_dataset failed: {e}")
                raise CogneeError(f"Failed to create dataset: {e}")

    async def remember(self, text: str, dataset_id: str, self_improvement: bool = False) -> bool:
        """Store a new memory in Cognee."""
        async with httpx.AsyncClient() as client:
            try:
                # /api/v1/remember accepts multipart/form-data for files
                files = [
                    ("data", ("memory.txt", text.encode("utf-8"), "text/plain"))
                ]
                
                form_data = {
                    "run_in_background": "true",
                    "datasetId": dataset_id
                }
                
                data_tuples = list(form_data.items())

                # For multipart requests, we must omit Content-Type so httpx sets the boundary automatically
                headers = {"X-Api-Key": self.api_key}

                response = await client.post(
                    f"{self.api_url}/api/v1/remember", 
                    files=files,
                    data=data_tuples,
                    headers=headers, 
                    timeout=10.0
                )
                response.raise_for_status()
                
                if self_improvement:
                    await self.improve(dataset_id)
                    
                return True
            except Exception as e:
                logger.error(f"Cognee remember failed: {e}")
                raise CogneeError(f"Failed to store memory: {e}")

    async def recall(self, query: str, dataset_id: str, limit: int = 5) -> list[dict[str, Any]]:
        """Recall relevant memories from Cognee based on query and dataset_id."""
        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "query": query,
                    "datasetIds": [dataset_id],
                    "topK": limit,
                    "searchType": "GRAPH_COMPLETION",
                    "onlyContext": True
                }
                response = await client.post(
                    f"{self.api_url}/api/v1/recall", 
                    json=payload, 
                    headers=self.headers, 
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                # Transform response to standard format for MemoryService
                results = []
                # Handle: graph_context, session_context, graph, session, trace
                
                items = []
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    # check for the specific fields
                    for key in ["graph_context", "session_context", "graph", "session", "trace", "memories", "data"]:
                        if key in data and isinstance(data[key], list):
                            items.extend(data[key])
                            
                for item in items:
                    if isinstance(item, dict):
                        text_val = item.get("text") or item.get("content") or str(item)
                    else:
                        text_val = str(item)
                    results.append({"text": text_val, "metadata": {}})
                
                return results
            except Exception as e:
                logger.error(f"Cognee recall failed: {e}")
                raise CogneeError(f"Failed to recall memory: {e}")

    async def forget(self, memory_id: str, dataset_id: str) -> bool:
        """Remove a memory by its ID."""
        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "dataId": memory_id,
                    "datasetId": dataset_id,
                    "everything": False,
                    "memoryOnly": False
                }
                response = await client.post(
                    f"{self.api_url}/api/v1/forget", 
                    json=payload,
                    headers=self.headers, 
                    timeout=10.0
                )
                response.raise_for_status()
                return True
            except Exception as e:
                logger.error(f"Cognee forget failed: {e}")
                raise CogneeError(f"Failed to forget memory: {e}")

    async def improve(self, dataset_id: str) -> bool:
        """Trigger an improvement/optimization pass in Cognee."""
        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "datasetId": dataset_id,
                    "runInBackground": True
                }
                response = await client.post(
                    f"{self.api_url}/api/v1/improve", 
                    json=payload,
                    headers=self.headers, 
                    timeout=10.0
                )
                response.raise_for_status()
                return True
            except Exception as e:
                logger.error(f"Cognee improve failed: {e}")
                raise CogneeError(f"Failed to trigger improve: {e}")
