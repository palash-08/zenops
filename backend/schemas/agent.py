from typing import List, Optional
from pydantic import BaseModel

class AgentExecuteRequest(BaseModel):
    guild_id: str
    discord_channel_id: str
    prompt: str

class PromptContext(BaseModel):
    system_prompt: str
    cognee_memories: str
    conversation_history: str
    current_request: str
    final_prompt: str
