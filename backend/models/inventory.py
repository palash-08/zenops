from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from core.database import Base

class ServerInventory(Base):
    __tablename__ = "server_inventories"

    server_id = Column(UUID(as_uuid=True), ForeignKey("servers.id", ondelete="CASCADE"), primary_key=True)
    
    hostname = Column(String, nullable=True)
    summary = Column(String, nullable=True)
    services = Column(JSONB, nullable=True)
    raw_response = Column(Text, nullable=True)

    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    server = relationship("Server", back_populates="inventory")
