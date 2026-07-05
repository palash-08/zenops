import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.database import get_db
from services.binding_service import BindingService

router = APIRouter(prefix="/internal/bindings", tags=["discord_internal"])
guild_router = APIRouter(prefix="/internal/guilds", tags=["discord_internal"])

class BindRequest(BaseModel):
    server_id: uuid.UUID

class SetContextLimitRequest(BaseModel):
    limit: int

class SetGlobalRequest(BaseModel):
    discord_channel_id: str

@router.post("/{channel_id}", status_code=status.HTTP_200_OK)
def bind_channel(channel_id: str, payload: BindRequest, db: Session = Depends(get_db)):
    service = BindingService(db)
    binding = service.bind(channel_id, payload.server_id)
    return {"status": "success", "channel_id": channel_id, "server_id": binding.server_id}

@router.delete("/{channel_id}", status_code=status.HTTP_200_OK)
def unbind_channel(channel_id: str, db: Session = Depends(get_db)):
    service = BindingService(db)
    success = service.unbind(channel_id)
    if not success:
        raise HTTPException(status_code=404, detail="Binding not found")
    return {"status": "success"}

@guild_router.put("/{guild_id}/global", status_code=status.HTTP_200_OK)
def set_global_channel(guild_id: str, payload: SetGlobalRequest, db: Session = Depends(get_db)):
    service = BindingService(db)
    service.set_global(guild_id, payload.discord_channel_id)
    return {"status": "success", "global_channel_id": payload.discord_channel_id}

@router.put("/{channel_id}/context-limit", status_code=status.HTTP_200_OK)
def set_context_limit(channel_id: str, payload: SetContextLimitRequest, db: Session = Depends(get_db)):
    if payload.limit <= 0:
        raise HTTPException(status_code=400, detail="Limit must be a positive integer.")
    service = BindingService(db)
    binding = service.set_context_limit(channel_id, payload.limit)
    if not binding:
        raise HTTPException(status_code=404, detail="Binding not found")
    return {"status": "success", "limit": payload.limit}

@router.delete("/{channel_id}/context", status_code=status.HTTP_200_OK)
def clear_chat_context(channel_id: str, db: Session = Depends(get_db)):
    service = BindingService(db)
    service.clear_chat_context(channel_id)
    return {"status": "success"}

@router.get("/{channel_id}/context-info", status_code=status.HTTP_200_OK)
def get_context_info(channel_id: str, guild_id: str, db: Session = Depends(get_db)):
    service = BindingService(db)
    binding = service.get_binding(channel_id)
    if not binding:
        raise HTTPException(status_code=404, detail="Binding not found")
        
    is_global = service.is_global(guild_id, channel_id)
    message_count = service.get_message_count(channel_id)
    
    return {
        "server_id": str(binding.server_id),
        "server_name": binding.server.name if binding.server else "Unknown",
        "chat_context_limit": binding.chat_context_limit,
        "message_count": message_count,
        "is_global": is_global
    }

