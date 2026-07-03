from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ServerCreate(BaseModel):
    """Schema used when registering a new server."""

    name: str
    description: str | None = None
    tailscale_ip: str
    gateway_port: int
    gateway_token: str


class ServerResponse(BaseModel):
    """Schema returned to clients."""

    id: UUID
    name: str
    description: str | None = None
    tailscale_ip: str
    gateway_port: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ServerExecuteRequest(BaseModel):
    """Schema used when triggering an execution on the server."""

    prompt: str