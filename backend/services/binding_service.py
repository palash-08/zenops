import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from models.binding import ChannelBinding, GuildSettings, ConversationMessage
from models.server import Server

class BindingService:
    def __init__(self, db: Session):
        self.db = db

    def bind(self, discord_channel_id: str, server_id: uuid.UUID) -> ChannelBinding:
        # Check if already bound, update if so, else create
        binding = self.db.query(ChannelBinding).filter(ChannelBinding.discord_channel_id == discord_channel_id).first()
        if binding:
            binding.server_id = server_id
        else:
            binding = ChannelBinding(discord_channel_id=discord_channel_id, server_id=server_id)
            self.db.add(binding)
        self.db.commit()
        self.db.refresh(binding)
        return binding

    def unbind(self, discord_channel_id: str) -> bool:
        binding = self.db.query(ChannelBinding).filter(ChannelBinding.discord_channel_id == discord_channel_id).first()
        if not binding:
            return False
            
        # Delete binding
        self.db.delete(binding)
        # Delete short term messages for channel
        self.db.execute(delete(ConversationMessage).where(ConversationMessage.discord_channel_id == discord_channel_id))
        self.db.commit()
        return True

    def get_bound_server(self, discord_channel_id: str) -> Optional[Server]:
        binding = self.db.query(ChannelBinding).filter(ChannelBinding.discord_channel_id == discord_channel_id).first()
        if binding:
            return binding.server
        return None
        
    def get_binding(self, discord_channel_id: str) -> Optional[ChannelBinding]:
        return self.db.query(ChannelBinding).filter(ChannelBinding.discord_channel_id == discord_channel_id).first()

    def set_context_limit(self, discord_channel_id: str, limit: int) -> Optional[ChannelBinding]:
        binding = self.db.query(ChannelBinding).filter(ChannelBinding.discord_channel_id == discord_channel_id).first()
        if not binding:
            return None
            
        binding.chat_context_limit = limit
        self.db.commit()
        self.db.refresh(binding)
        
        # Enforce new limit
        self._enforce_limit(discord_channel_id, limit)
        return binding

    def get_context_limit(self, discord_channel_id: str) -> int:
        binding = self.db.query(ChannelBinding).filter(ChannelBinding.discord_channel_id == discord_channel_id).first()
        return binding.chat_context_limit if binding else 20

    def clear_chat_context(self, discord_channel_id: str) -> None:
        self.db.execute(delete(ConversationMessage).where(ConversationMessage.discord_channel_id == discord_channel_id))
        self.db.commit()

    def is_global(self, guild_id: str, discord_channel_id: str) -> bool:
        setting = self.db.query(GuildSettings).filter(GuildSettings.guild_id == guild_id).first()
        if setting and setting.global_channel_id == discord_channel_id:
            return True
        return False
        
    def get_message_count(self, discord_channel_id: str) -> int:
        return self.db.query(ConversationMessage).filter(ConversationMessage.discord_channel_id == discord_channel_id).count()

    def set_global(self, guild_id: str, discord_channel_id: str) -> GuildSettings:
        setting = self.db.query(GuildSettings).filter(GuildSettings.guild_id == guild_id).first()
        if setting:
            setting.global_channel_id = discord_channel_id
        else:
            setting = GuildSettings(guild_id=guild_id, global_channel_id=discord_channel_id)
            self.db.add(setting)
        self.db.commit()
        self.db.refresh(setting)
        return setting

    def append_message(self, discord_channel_id: str, server_id: uuid.UUID, role: str, content: str) -> ConversationMessage:
        msg = ConversationMessage(
            discord_channel_id=discord_channel_id,
            server_id=server_id,
            role=role,
            content=content
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        
        limit = self.get_context_limit(discord_channel_id)
        self._enforce_limit(discord_channel_id, limit)
        return msg

    def get_recent_messages(self, discord_channel_id: str) -> List[ConversationMessage]:
        return self.db.query(ConversationMessage)\
            .filter(ConversationMessage.discord_channel_id == discord_channel_id)\
            .order_by(ConversationMessage.created_at.asc())\
            .all()
            
    def _enforce_limit(self, discord_channel_id: str, limit: int):
        if limit <= 0:
            self.db.execute(delete(ConversationMessage).where(ConversationMessage.discord_channel_id == discord_channel_id))
            self.db.commit()
            return
            
        messages = self.db.query(ConversationMessage.id)\
            .filter(ConversationMessage.discord_channel_id == discord_channel_id)\
            .order_by(ConversationMessage.created_at.desc())\
            .all()
            
        if len(messages) > limit:
            ids_to_delete = [m[0] for m in messages[limit:]]
            self.db.execute(delete(ConversationMessage).where(ConversationMessage.id.in_(ids_to_delete)))
            self.db.commit()

