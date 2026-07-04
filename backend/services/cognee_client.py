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
        self.client = httpx.AsyncClient(headers=self.headers, timeout=10.0)

    async def close(self):
        """Close the underlying HTTP client."""
        await self.client.aclose()

    async def health(self) -> bool:
        """Check if the Cognee memory backend is accessible."""
        try:
            response = await self.client.get(f"{self.api_url}/health", timeout=5.0)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Cognee health check failed: {e}")
            return False

    async def create_dataset(self, name: str) -> str:
        """Create a Cognee dataset and return its UUID."""
        try:
            payload = {"name": name}
            response = await self.client.post(
                f"{self.api_url}/api/v1/datasets", 
                json=payload
            )
            
            if response.status_code == 409:
                # Dataset already exists, retrieve its ID
                get_resp = await self.client.get(
                    f"{self.api_url}/api/v1/datasets"
                )
                get_resp.raise_for_status()
                datasets = get_resp.json()
                for ds in datasets:
                    if isinstance(ds, dict) and ds.get("name") == name:
                        return ds.get("id")
                raise CogneeError(f"Dataset {name} returned 409 but could not be found.")

            response.raise_for_status()
            data = response.json()
            return data.get("id")
        except Exception as e:
            logger.error(f"Cognee create_dataset failed: {e}")
            raise CogneeError(f"Failed to create dataset: {e}")

    async def remember(self, text: str, dataset_id: str, self_improvement: bool = False) -> bool:
      try:
        files = [
            ("data", ("memory.txt", text.encode("utf-8"), "text/plain"))
        ]

        form_data = {
            "run_in_background": "true",
            "datasetId": dataset_id,
        }

        headers = {
            "X-Api-Key": self.api_key,
        }

        logger.info("=== Cognee Remember Request ===")
        logger.info("URL: %s/api/v1/remember", self.api_url)
        logger.info("Dataset ID: %s", dataset_id)
        logger.info("Text length: %d", len(text))

        response = await self.client.post(
            f"{self.api_url}/api/v1/remember",
            files=files,
            data=form_data,
            headers=headers,
        )

        logger.info("=== Cognee Remember Response ===")
        logger.info("Status: %s", response.status_code)
        logger.info("Body: %s", response.text)

        response.raise_for_status()

        if self_improvement:
            await self.improve(dataset_id)

        return True
      except Exception:
        logger.exception("Cognee remember failed")
        raise

    async def recall(self, query: str, dataset_id: str, limit: int = 5) -> list[dict[str, Any]]:
        """Recall relevant memories from Cognee based on query and dataset_id."""
        try:
            payload = {
                "query": query,
                "datasetIds": [dataset_id],
                "topK": limit,
                "searchType": "GRAPH_COMPLETION",
                "onlyContext": True
            }
            response = await self.client.post(
                f"{self.api_url}/api/v1/recall", 
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            
            # Transform response to standard format for MemoryService
            results = []
            
            if not isinstance(data, list):
                logger.error(f"Cognee API did not return a list for recall. Response type: {type(data)}")
                return []
                        
            for item in data:
                if isinstance(item, dict):
                    source = item.get("source")
                    text_val = ""
                    
                    if source in ("graph_context", "session_context"):
                        text_val = item.get("content", "")
                    elif source == "graph":
                        text_val = item.get("text", "")
                    elif source == "session":
                        text_val = item.get("answer", "")
                    elif source == "trace":
                        text_val = item.get("memory_context", "")
                    else:
                        continue
                        
                    if text_val:
                        results.append({"text": str(text_val), "metadata": {}})
            
            return results
        except Exception as e:
            logger.error(f"Cognee recall failed: {e}")
            raise CogneeError(f"Failed to recall memory: {e}")

    async def forget(self, memory_id: str, dataset_id: str) -> bool:
        """Remove a memory by its ID."""
        try:
            payload = {
                "dataId": memory_id,
                "datasetId": dataset_id,
                "everything": False,
                "memoryOnly": False
            }
            response = await self.client.post(
                f"{self.api_url}/api/v1/forget", 
                json=payload
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Cognee forget failed: {e}")
            raise CogneeError(f"Failed to forget memory: {e}")

    async def improve(self, dataset_id: str) -> bool:
        """Trigger an improvement/optimization pass in Cognee."""
        try:
            payload = {
                "datasetId": dataset_id,
                "runInBackground": True
            }
            response = await self.client.post(
                f"{self.api_url}/api/v1/improve", 
                json=payload
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Cognee improve failed: {e}")
            raise CogneeError(f"Failed to trigger improve: {e}")
