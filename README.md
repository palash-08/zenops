# 🚀 ZenOps

> **A Context-Aware AI DevOps Assistant built with OpenClaw, Cognee, and Discord**

ZenOps is an AI-powered DevOps assistant that enables engineers to manage Linux servers using natural language through Discord.

Unlike traditional AI assistants that lose context between conversations, ZenOps combines **short-term conversational memory** with **long-term semantic infrastructure memory**, allowing it to remember both previous conversations and the state of managed servers.

---

# ✨ Features

- 🤖 Natural language infrastructure management
- 💬 Discord-native interface
- 🖥️ Multi-server management
- 🔗 Channel-to-server binding
- 🧠 Long-term infrastructure memory using Cognee
- 💭 Short-term conversational memory
- 🔍 Infrastructure discovery
- 🔒 Secure communication over Tailscale
- ⚡ OpenClaw-powered command execution

---

# 🎯 Why ZenOps?

Managing multiple VPSs often involves:

- Remembering which server you're connected to
- Switching between SSH sessions
- Repeating context to AI assistants
- Manually rediscovering infrastructure

ZenOps solves this by giving every server an AI agent with persistent memory.

Instead of remembering your infrastructure, **ZenOps remembers it for you.**

---

# 🏗️ Architecture

```
                        Discord

                           │

                           ▼

                FastAPI Backend (ZenOps)

      ┌─────────────────────────────────────┐
      │                                     │
      │  Authentication                     │
      │  Server Registry                    │
      │  Channel Bindings                   │
      │  Prompt Construction                │
      │  Conversation Memory               │
      │  Cognee Integration                 │
      │                                     │
      └───────────────┬─────────────────────┘
                      │
          ┌───────────┴────────────┐
          │                        │
          ▼                        ▼

     OpenClaw Agent          Cognee Memory

          │

          ▼

    Managed Linux VPS
```

---

# 🧠 Memory Architecture

ZenOps intentionally separates memory into two layers.

## Short-Term Memory

Stored in PostgreSQL.

Responsible for:

- Recent conversation history
- Contextual follow-up questions
- Pronoun resolution
- Channel-specific sessions

Example:

```
Install nginx.

Configure it for my React app in xyz directory.

Restart it.
```

The assistant understands what **"it"** refers to.

---

## Long-Term Memory

Powered by Cognee.

Stores semantic knowledge about servers, including:

- Installed software
- Infrastructure discoveries
- Server metadata
- Previous observations

Unlike chat history, this memory persists across future conversations.

---

# 💬 Discord Commands

| Command | Description |
|----------|-------------|
| `/zen ask` | Ask the AI to perform infrastructure tasks or answer questions. |
| `/zen discover` | Discover installed services and infrastructure details on the target VPS and store them in Cognee. |
| `/zen register` | Register a new OpenClaw-enabled VPS. |
| `/zen delete` | Remove a registered VPS. |
| `/zen bind` | Bind a VPS to the current Discord channel for contextual conversations. |
| `/zen unbind` | Remove the server binding from the current Discord channel. |

---

# 🔗 Channel Binding

ZenOps introduces **channel-based server sessions**.

Each Discord channel can be bound to exactly one server.

Once bound:

- every `/zen ask` automatically targets that VPS
- conversations remain isolated per server
- recent chat history is preserved
- Cognee provides long-term infrastructure memory

This enables natural conversations without repeatedly specifying the server.

---

# ⚙️ Technology Stack

## Backend

- FastAPI
- Uvicorn
- SQLAlchemy
- PostgreSQL
- Alembic
- Pydantic
- HTTPX
- python-dotenv

---

## AI & Memory

- OpenClaw
- Cognee SDK
- FastEmbed
- Qwen3 8B (self-hosted)
- Mistral Devstral

---

## Discord Bot

- discord.py
- Slash Commands
- Discord Modals
- Discord Views
- HTTPX

---

## Infrastructure

- Docker
- Docker Compose
- Tailscale
- MagicDNS

---

# 🏆 Cognee Hangover Hackathon

## Infrastructure Used During Development

ZenOps was demonstrated using a distributed architecture consisting of multiple VPSs.

### OpenClaw Layer

- **2 independent OpenClaw instances**
- Each running on its own Linux VPS
- OpenClaw Gateway exposed **only through Tailscale**
- Communication performed via **MagicDNS hostnames**
- HTTP APIs bound exclusively to the Tailscale network (not publicly exposed)

Both OpenClaw instances used the **Mistral Devstral** model for infrastructure reasoning and execution.

---

### Orchestration Layer

A dedicated VPS hosted:

- FastAPI Backend
- Discord Bot
- Cognee SDK

This server acted as the central orchestration layer for all managed infrastructure.

---

### Memory Layer

Cognee was configured to use:

- **Self-hosted Qwen3 8B** running locally
- **FastEmbed** as the embedding model

Cognee stores semantic infrastructure knowledge that can be recalled across conversations.

---

### Scalability

ZenOps is designed to support additional servers without architectural changes.

When a new VPS is registered:

1. It runs an OpenClaw instance.
2. It connects securely over the existing Tailscale network.
3. It registers with the FastAPI backend.
4. Infrastructure discoveries are stored in the shared Cognee knowledge base.
5. Future conversations can leverage the same centralized semantic memory.

This allows every managed server to contribute to a unified infrastructure knowledge graph.

---

# 🔒 Security

ZenOps follows a private-network-first architecture.

- OpenClaw HTTP APIs are **never exposed publicly**.
- Communication occurs only over **Tailscale**.
- Services are bound to Tailscale interfaces.
- MagicDNS is used instead of public IP addresses.
- Infrastructure execution occurs only through registered OpenClaw agents.

---

# 🚀 Project Workflow

```
Discord User

        │

        ▼

/zen ask

        │

        ▼

Resolve Bound Server

        │

        ▼

Retrieve Conversation Context

        │

        ▼

Recall Cognee Memories

        │

        ▼

Build Prompt

        │

        ▼

OpenClaw

        │

        ▼

Execute on VPS

        │

        ▼

Return Response

        │

        ▼

Update Conversation Context

        │

        ▼

Background Cognee Memory Update
```

---

# 🔮 Future Improvements

- Multi-server orchestration
- Infrastructure graph visualization
- Kubernetes support
- Role-based access control
- Autonomous maintenance workflows
- Web dashboard
- Approval workflows for destructive operations

---

# 👨‍💻 Built For

**Cognee Hangover Hackathon**

ZenOps demonstrates how conversational AI, persistent semantic memory, and secure infrastructure execution can be combined to create an intelligent DevOps assistant capable of managing real-world Linux infrastructure.