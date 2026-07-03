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
                payload={"prompt": prompt}
            )
            return response_data
        except OpenClawError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(e)
            )
        finally:
            await client.close()
