import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base

class Server(Base):
    __tablename__ = "servers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    tailscale_ip = Column(String, nullable=False)
    gateway_port = Column(Integer, nullable=False)
    gateway_token = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def gateway_url(self) -> str:
        return f"https://{self.tailscale_ip}:{self.gateway_port}"
