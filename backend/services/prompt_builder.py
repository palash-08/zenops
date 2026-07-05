from typing import List
from models.binding import ConversationMessage
from models.server import Server
from schemas.agent import PromptContext

class PromptBuilder:
    def build(self, server: Server, memories: str, recent_messages: List[ConversationMessage], current_request: str) -> PromptContext:
        server_info = f"Server Name: {server.name}\n"
        if server.description:
            server_info += f"Description: {server.description}\n"
            
        system_prompt = (
            "You are ZenOps, an AI-powered DevOps assistant managing a live Linux server.\n\n"
            "####################################\n"
            "SERVER METADATA\n"
            "####################################\n\n"
            f"{server_info}\n"
            "CRITICAL OPERATING RULES - HOW TO USE MEMORY VS. LIVE COMMANDS:\n"
            "1. Live server state is ALWAYS your primary source of truth.\n"
            "2. Use MEMORY ONLY for: previous discoveries, historical observations, user preferences, saved notes, UUIDs, infrastructure inventory, and long-term context.\n"
            "3. If a question concerns ANYTHING that can change over time (e.g., 'Is Docker running?', 'Is Tailscale installed?', 'What is CPU usage?'), you MUST verify it using Linux shell commands before answering.\n"
            "4. If both memory and live inspection are useful:\n"
            "   - Recall the memory.\n"
            "   - Verify it against the live server using shell commands.\n"
            "   - Prefer the live information if they disagree.\n"
            "   - Inform the user that the memory was outdated if necessary.\n"
            "5. NEVER answer operational or state-based questions solely from memory.\n"
            "6. Whenever shell commands are available, ALWAYS prefer verification over assumptions.\n"
        )
        
        memories_section = ""
        if memories and memories.strip():
            memories_section = f"####################################\nSERVER MEMORY\n####################################\n\nRelevant previous observations:\n\n{memories}\n\n"
            
        history_section = ""
        if recent_messages:
            history_section = "####################################\nRECENT CONVERSATION\n####################################\n\n"
            for msg in recent_messages:
                # msg.role is either 'user' or 'assistant'
                role_capitalized = msg.role.capitalize()
                history_section += f"{role_capitalized}:\n{msg.content}\n\n"
                
        current_section = f"####################################\nCURRENT REQUEST\n####################################\n\n{current_request}"
        
        final_prompt = f"{system_prompt}\n{memories_section}{history_section}{current_section}"
        
        return PromptContext(
            system_prompt=system_prompt,
            cognee_memories=memories_section,
            conversation_history=history_section,
            current_request=current_section,
            final_prompt=final_prompt
        )
