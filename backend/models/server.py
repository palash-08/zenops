import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base

class Server(Base):
    __tablename__ = "servers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    tailscale_ip = Column(String, nullable=False)
    gateway_port = Column(Integer, nullable=False)
    gateway_token = Column(String, nullable=False)
    cognee_dataset_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    inventory = relationship(
        "ServerInventory",
        back_populates="server",
        uselist=False,
        cascade="all, delete-orphan"
    )

    @property
    def gateway_url(self) -> str:
        return f"https://{self.tailscale_ip}:{self.gateway_port}"
