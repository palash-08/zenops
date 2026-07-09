# ZenOps

AI-powered DevOps assistant that manages Linux servers via natural language through Discord. Built with FastAPI, OpenClaw, and Cognee.

## Quickstart

```bash
git clone <repo> && cd zenops

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # edit with your values
alembic upgrade head
uvicorn main:app --reload

# Discord Bot (separate terminal)
cd discord-bot
pip install -r ../.venv/lib/python3*/site-packages/  # or create its own venv
python main.py
```

## Project Structure

```
zenops/
├── backend/                         # FastAPI API server
│   ├── core/
│   │   ├── config.py                # env-based settings
│   │   └── database.py              # SQLAlchemy engine + session
│   ├── models/                      # SQLAlchemy ORM models
│   │   ├── server.py                # Server entity
│   │   ├── binding.py               # Channel bindings + conversation messages
│   │   └── inventory.py             # Discovered service inventory
│   ├── schemas/                     # Pydantic request/response schemas
│   ├── repositories/                # Data access layer
│   │   └── server_repository.py
│   ├── services/                    # Business logic
│   │   ├── agent_service.py         # Orchestrates execution pipeline
│   │   ├── server_service.py        # Server CRUD
│   │   ├── binding_service.py       # Channel binding operations
│   │   ├── execution_resolver.py    # Routes requests to bound/global/unbound targets
│   │   ├── prompt_builder.py        # Constructs system prompts with context
│   │   ├── memory_service.py        # Cognee-backed long-term memory (read/write)
│   │   ├── cognee_client.py         # HTTP client for Cognee REST API
│   │   └── openclaw_client.py       # HTTP client for OpenClaw gateway
│   ├── routers/                     # FastAPI route handlers
│   │   ├── server_router.py         # /servers/* CRUD + execute + discover
│   │   ├── discord_binding_router.py# /internal/* bindings, guilds, context
│   │   └── agent_router.py          # /agent/execute orchestrated dispatch
│   ├── tests/
│   │   ├── test_services.py         # Unit tests for PromptBuilder, ExecutionResolver, clients
│   │   └── test_routes.py           # Route integration tests + auth tests
│   ├── alembic/                     # Database migrations
│   ├── main.py                      # FastAPI app entrypoint
│   ├── pyproject.toml               # Project metadata + dev dependencies
│   └── requirements.txt             # Runtime dependencies
├── discord-bot/                     # Discord bot (discord.py)
│   ├── core/config.py               # Bot env settings (token, backend URL)
│   ├── commands/                    # Slash command handlers
│   │   ├── zen.py                   # /zen group (ask, discover, register, bind, ...)
│   │   ├── ask.py                   # /ask command
│   │   ├── servers.py               # /servers list command
│   │   ├── modals.py                # ServerRegisterModal
│   │   ├── views.py                 # DeleteConfirmView
│   │   └── utils.py                 # Shared error handler
│   ├── services/backend_client.py   # Persistent httpx client for backend API
│   ├── bot.py                       # Bot creation + cog loading
│   ├── main.py                      # Entrypoint
│   └── requirements.txt
├── .env.example                     # Required environment variables
├── .gitignore
└── README.md
```

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | -- | PostgreSQL connection string |
| `DISCORD_BOT_TOKEN` | Yes | -- | Discord application token |
| `COGNEE_API_URL` | Yes | -- | Cognee backend base URL |
| `COGNEE_API_KEY` | Yes | -- | Cognee API key |
| `INTERNAL_AUTH_TOKEN` | No | `zenops-internal-secret` | Shared secret for bot-to-backend auth |
| `BACKEND_URL` | No | `http://127.0.0.1:8000` | Bot's backend target |
| `BOT_ACTIVITY_TYPE` | No | `playing` | Discord presence type |
| `BOT_ACTIVITY_TEXT` | No | `Managing your infrastructure` | Discord presence text |

## Development

```bash
# Run tests (from repo root)
source .venv/bin/activate
python -m pytest backend/tests/ -v

# Run backend
uvicorn backend.main:app --reload --port 8000

# Database migrations
cd backend
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Architecture

```
Discord  -->  discord-bot/  -->  FastAPI Backend  -->  OpenClaw Gateway  -->  Linux VPS
                     |                        |
                     |                   +--------+
                     `-- X-Internal-Auth  | Cognee |
                                         +--------+
```

The execution pipeline for a `/zen ask` call:

1. **ExecutionResolver** determines the target (bound channel, global, or unbound fallback)
2. **PromptBuilder** assembles system prompt from server metadata, recent conversation, and Cognee memories
3. **AgentService** sends the prompt to the OpenClaw gateway, persists conversation, and triggers background memory update
4. Cognee memory updates run asynchronously via `BackgroundTasks` (does not block the response)

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| GET | `/servers` | List registered servers |
| POST | `/servers` | Register a new server |
| GET | `/servers/{id}` | Get server details |
| POST | `/servers/{id}/execute` | Execute a prompt on a server |
| POST | `/servers/{id}/discover` | Run infrastructure discovery |
| DELETE | `/servers/{id}` | Remove a server |
| POST | `/agent/execute` | Orchestrated execution (bound/global/unbound resolution) |
| POST | `/internal/bindings/{channel}` | Bind Discord channel to server |
| DELETE | `/internal/bindings/{channel}` | Unbind channel |
| PUT | `/internal/bindings/{channel}/context-limit` | Set context limit |
| DELETE | `/internal/bindings/{channel}/context` | Clear conversation context |
| GET | `/internal/bindings/{channel}/context-info` | Get context metadata |
| PUT | `/internal/guilds/{guild}/global` | Set global management channel |

Internal routes require `X-Internal-Auth` header matching `INTERNAL_AUTH_TOKEN`.

## Discord Commands

| Command | Description |
|---------|-------------|
| `/zen ask <prompt>` | Execute a task via natural language |
| `/zen discover [server]` | Detect installed services on a server |
| `/zen register` | Open modal to register a new VPS |
| `/zen delete [server]` | Remove a server from ZenOps |
| `/zen bind <server>` | Bind channel to a server for context-aware chat |
| `/zen unbind` | Remove channel binding |
| `/zen global` | Set this channel as the global management channel |
| `/zen context info` | View channel binding and message count |
| `/zen context set <limit>` | Set conversation context limit |
| `/zen clearchatcontext` | Clear short-term chat history |
| `/ask <server> <prompt>` | Execute prompt on a specific server (legacy) |
| `/servers` | List all registered servers |
