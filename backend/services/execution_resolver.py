import uuid
from typing import Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from repositories.server_repository import ServerRepository
from services.binding_service import BindingService

@dataclass
class ExecutionTarget:
    mode: str  # "BOUND", "GLOBAL", or "UNBOUND"
    server_id: Optional[uuid.UUID] = None

class ExecutionResolver:
    def __init__(self, db: Session):
        self.db = db
        self.binding_service = BindingService(db)
        self.server_repository = ServerRepository(db)

    def resolve(self, guild_id: str, channel_id: str) -> ExecutionTarget:
        # 1. Check Global
        if self.binding_service.is_global(guild_id, channel_id):
            return ExecutionTarget(mode="GLOBAL")
            
        # 2. Check Bound
        binding = self.binding_service.get_binding(channel_id)
        if binding:
            return ExecutionTarget(mode="BOUND", server_id=binding.server_id)
            
        # 3. Fallback to Unbound Legacy Routing
        servers = self.server_repository.list_servers()
        if not servers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No registered servers found. Please register a server first."
            )
            
        if len(servers) == 1:
            return ExecutionTarget(mode="UNBOUND", server_id=servers[0].id)
            
        # len(servers) > 1
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Multiple servers found. Please bind this channel using `/zen bind` or explicitly specify a server."
        )
