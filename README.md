````markdown
# 🚀 ZenOps

> **A Context-Aware AI DevOps Assistant built with OpenClaw, Cognee, and Discord**

ZenOps is an AI-powered DevOps assistant that enables engineers to manage Linux servers using natural language through Discord.

Unlike traditional AI assistants that lose context between conversations, ZenOps combines short-term conversational memory with long-term semantic infrastructure memory, allowing it to remember both previous conversations and the state of managed servers.

---

# ✨ Features

- 🤖 Natural language infrastructure management
- 💬 Discord-native interface
- 🖥️ Multi-server management
- 🔗 Channel-to-server binding
- 🧠 Long-term infrastructure memory using Cognee
- 💭 Short-term conversational memory
- 🔍 Infrastructure discovery
- ⚡ OpenClaw-powered command execution
- 🔒 Secure communication over Tailscale
- 🚀 Distributed architecture supporting multiple VPSs

---

# 🎯 Why ZenOps?

Managing multiple Linux servers usually means:

- Remembering which server you're connected to
- Switching between SSH sessions
- Repeating context to AI assistants
- Manually rediscovering infrastructure
- Losing previous troubleshooting knowledge

ZenOps solves this by giving every server an AI agent with persistent memory.

Instead of remembering your infrastructure, **ZenOps remembers it for you.**

---

# 🏗️ Architecture

```text
                         Discord
                            │
                            ▼
                     Discord Bot
                            │
                            ▼
                  FastAPI Backend (ZenOps)
          ┌─────────────────────────────────────┐
          │ Authentication                      │
          │ Server Registry                     │
          │ Channel Bindings                    │
          │ Prompt Construction                 │
          │ Conversation Memory                 │
          │ Cognee Integration                  │
          └───────────────┬─────────────────────┘
                          │
              ┌───────────┴────────────┐
              │                        │
              ▼                        ▼
       OpenClaw Gateway          Cognee Memory
              │
              ▼
      Managed Linux VPS
````

---

# 🧠 Memory Architecture

ZenOps intentionally separates memory into two layers.

## Short-Term Memory

Stored in PostgreSQL.

Responsible for:

* Recent conversation history
* Contextual follow-up questions
* Pronoun resolution
* Channel-specific sessions

Example:

```text
Install nginx.

Configure it for my React app.

Restart it.
```

The assistant understands what **"it"** refers to.

## Long-Term Memory

Powered by Cognee.

Stores semantic infrastructure knowledge including:

* Installed software
* Infrastructure discoveries
* Server metadata
* Previous observations
* Configuration history

Unlike chat history, this memory persists across future conversations.

---

# ⚡ Execution Pipeline

For every `/zen ask` request:

1. **ExecutionResolver** determines the target server (bound, global, or explicit).
2. **PromptBuilder** assembles the system prompt using:

   * Server metadata
   * Recent conversation
   * Cognee memories
3. **AgentService** sends the prompt to the appropriate OpenClaw instance.
4. The response is returned to Discord.
5. Conversation history is persisted.
6. Cognee updates long-term memory asynchronously in the background.

---

# 🚀 Quick Start

Clone the repository:

```bash
git clone <repo>
cd zenops
```

## Backend

```bash
cd backend

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp ../.env.example ../.env

# Edit .env with your values

alembic upgrade head

uvicorn main:app --reload
```

## Discord Bot

Open another terminal:

```bash
cd discord-bot

pip install -r requirements.txt

python main.py
```

---

# 📁 Project Structure

```text
zenops/
├── backend/
│   ├── core/
│   │   ├── config.py
│   │   └── database.py
│   ├── models/
│   │   ├── server.py
│   │   ├── binding.py
│   │   └── inventory.py
│   ├── schemas/
│   ├── repositories/
│   ├── services/
│   │   ├── agent_service.py
│   │   ├── server_service.py
│   │   ├── binding_service.py
│   │   ├── execution_resolver.py
│   │   ├── prompt_builder.py
│   │   ├── memory_service.py
│   │   ├── cognee_client.py
│   │   └── openclaw_client.py
│   ├── routers/
│   ├── tests/
│   ├── alembic/
│   ├── main.py
│   └── requirements.txt
│
├── discord-bot/
│   ├── commands/
│   ├── services/
│   ├── bot.py
│   ├── main.py
│   └── requirements.txt
│
├── .env.example
├── README.md
└── .gitignore
```

---

# ⚙️ Configuration

| Variable            | Required | Default                      | Description                  |
| ------------------- | -------- | ---------------------------- | ---------------------------- |
| DATABASE_URL        | ✅        | —                            | PostgreSQL connection string |
| DISCORD_BOT_TOKEN   | ✅        | —                            | Discord bot token            |
| COGNEE_API_URL      | ✅        | —                            | Cognee backend URL           |
| COGNEE_API_KEY      | ✅        | —                            | Cognee API key               |
| INTERNAL_AUTH_TOKEN | No       | zenops-internal-secret       | Internal bot authentication  |
| BACKEND_URL         | No       | http://127.0.0.1:8000        | Backend URL                  |
| BOT_ACTIVITY_TYPE   | No       | playing                      | Discord activity type        |
| BOT_ACTIVITY_TEXT   | No       | Managing your infrastructure | Discord activity             |

---

# 💬 Discord Commands

| Command                 | Description                                         |
| ----------------------- | --------------------------------------------------- |
| `/zen ask`              | Execute infrastructure tasks using natural language |
| `/zen discover`         | Discover installed services and infrastructure      |
| `/zen register`         | Register a new OpenClaw-enabled VPS                 |
| `/zen delete`           | Remove a registered VPS                             |
| `/zen bind`             | Bind the current channel to a server                |
| `/zen unbind`           | Remove the current channel binding                  |
| `/zen global`           | Set this channel as the global management channel   |
| `/zen context info`     | View context information                            |
| `/zen context set`      | Set conversation history limit                      |
| `/zen clearchatcontext` | Clear conversation history                          |
| `/ask`                  | Execute on a specific server (legacy)               |
| `/servers`              | List registered servers                             |

---

# 🌐 REST API

| Method | Endpoint                                     | Description                   |
| ------ | -------------------------------------------- | ----------------------------- |
| GET    | `/`                                          | Health check                  |
| GET    | `/servers`                                   | List servers                  |
| POST   | `/servers`                                   | Register server               |
| GET    | `/servers/{id}`                              | Server details                |
| POST   | `/servers/{id}/execute`                      | Execute prompt                |
| POST   | `/servers/{id}/discover`                     | Infrastructure discovery      |
| DELETE | `/servers/{id}`                              | Remove server                 |
| POST   | `/agent/execute`                             | Orchestrated execution        |
| POST   | `/internal/bindings/{channel}`               | Bind Discord channel          |
| DELETE | `/internal/bindings/{channel}`               | Remove binding                |
| PUT    | `/internal/bindings/{channel}/context-limit` | Set context limit             |
| DELETE | `/internal/bindings/{channel}/context`       | Clear conversation context    |
| GET    | `/internal/bindings/{channel}/context-info`  | Context metadata              |
| PUT    | `/internal/guilds/{guild}/global`            | Set global management channel |

> Internal endpoints require the `X-Internal-Auth` header.

---

# ⚙️ Technology Stack

## Backend

* FastAPI
* SQLAlchemy
* PostgreSQL
* Alembic
* Pydantic
* HTTPX

## AI & Memory

* OpenClaw
* Cognee
* FastEmbed
* Self-hosted Qwen3 8B
* Mistral Devstral

## Discord

* discord.py
* Slash Commands
* Discord Modals
* Discord Views

## Infrastructure

* Docker
* Docker Compose
* Tailscale
* MagicDNS

---

# 🧪 Development

Run tests:

```bash
source .venv/bin/activate

pytest backend/tests -v
```

Run backend:

```bash
uvicorn backend.main:app --reload --port 8000
```

Database migrations:

```bash
cd backend

alembic revision --autogenerate -m "description"
alembic upgrade head
```

---

# 🏆 Cognee Hangover Hackathon

ZenOps was demonstrated using a distributed architecture consisting of:

* A dedicated FastAPI orchestration server
* Discord bot
* Multiple Linux VPSs
* Two independent OpenClaw instances
* Self-hosted Qwen3 8B
* Cognee semantic memory
* FastEmbed embeddings
* Private networking via Tailscale

When a new VPS is registered:

1. It runs an OpenClaw instance.
2. It joins the private Tailscale network.
3. It registers with the FastAPI backend.
4. Infrastructure discoveries are stored in Cognee.
5. Future conversations benefit from shared semantic infrastructure knowledge.

This enables every managed server to contribute to a unified infrastructure knowledge graph.

---

# 🔒 Security

ZenOps follows a private-network-first architecture.

* OpenClaw APIs are never publicly exposed.
* Communication occurs exclusively over Tailscale.
* Services bind only to Tailscale interfaces.
* MagicDNS replaces public IP addresses.
* Infrastructure execution is performed only through registered OpenClaw agents.

---

# 🔮 Future Improvements

* Multi-server orchestration
* Kubernetes support
* Infrastructure graph visualization
* Role-based access control
* Approval workflows for destructive operations
* Autonomous maintenance workflows
* Web dashboard

---

# 👨‍💻 Built For

**Cognee Hangover Hackathon**

ZenOps demonstrates how conversational AI, persistent semantic memory, and secure infrastructure execution can be combined to create an intelligent DevOps assistant capable of managing real-world Linux infrastructure.

```
```
