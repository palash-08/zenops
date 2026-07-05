import uuid
import logging
from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.orm import Session

from core.database import get_db
from schemas.server import ServerCreate, ServerResponse, ServerExecuteRequest, ServerInventorySchema
from repositories.server_repository import ServerRepository
from services.server_service import ServerService
from services.agent_service import AgentService
from services.cognee_client import CogneeClient
from fastapi import APIRouter, Depends, status, Response, BackgroundTasks, HTTPException

logger = logging.getLogger(__name__)

MEMORY_INIT_PROMPT = """Create MEMORY.md if it does not exist, or overwrite it if it already exists.
Use the built-in memory tools (do not simulate memory inside the response).
Store the supplied text below as persistent memory.

# ZenOps Agent

You are the infrastructure agent for this Linux server.

## Identity

Managed By: ZenOps

You are responsible only for this machine.

Never ask:

- Who am I?
- Which server am I managing?

## Responsibilities

- Linux
- Docker
- Docker Compose
- Networking
- Logs
- Infrastructure
- DevOps

Inspect first.

Reason second.

Answer last.

Never guess.

Always require confirmation before destructive operations.

This file will be updated later by /zen discover with hostname, installed services and server role.
"""

router = APIRouter(
    prefix="/servers",
    tags=["Servers"]
)

async def _initialize_server_memory(server_id: uuid.UUID, context: str):
    from core.database import SessionLocal
    db = SessionLocal()
    try:
        agent_service = AgentService(db)
        final_prompt = MEMORY_INIT_PROMPT
        if context and context.strip():
            final_prompt += f"\n\n## Server Context\n\n{context.strip()}"
            
        await agent_service.execute_prompt(server_id, final_prompt)
    except Exception as e:
        logger.error(f"Failed to initialize MEMORY.md for server {server_id}: {e}")
    finally:
        db.close()

@router.post("", response_model=ServerResponse)
async def create_server(server_in: ServerCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # 1. Instantiate the repository, injecting the database session
    repository = ServerRepository(db)
    
    # 2. Instantiate the service, injecting the repository
    service = ServerService(repository)
    
    # 3. Call the business logic and return the result
    new_server = service.register_server(server_in)
    
    # 3.5 Create Cognee dataset
    try:
        cognee = CogneeClient()
        dataset_id = await cognee.create_dataset(f"server_{new_server.id}")
        
        # We need to update the actual database model since new_server is a Pydantic schema
        server_model = repository.get_server_by_id(new_server.id)
        if server_model:
            server_model.cognee_dataset_id = dataset_id
            db.commit()
    except Exception as e:
        logger.error(f"Failed to create Cognee dataset: {e}")
        service.delete_server(new_server.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to provision memory dataset for server: {e}"
        )
    
    # 4. Initialize MEMORY.md on the newly registered server in the background
    background_tasks.add_task(_initialize_server_memory, new_server.id, server_in.context)
        
    return new_server

@router.get("", response_model=list[ServerResponse])
def get_servers(db: Session = Depends(get_db)):
    repository = ServerRepository(db)
    service = ServerService(repository)
    return service.list_servers()

@router.get("/{server_id}", response_model=ServerResponse)
def get_server(server_id: uuid.UUID, db: Session = Depends(get_db)):
    repository = ServerRepository(db)
    service = ServerService(repository)
    return service.get_server(server_id)

@router.post("/{server_id}/execute")
async def execute_server(
    server_id: uuid.UUID,
    request: ServerExecuteRequest,
    db: Session = Depends(get_db)
):
    service = AgentService(db)
    return await service.execute_prompt(server_id, request.prompt)

@router.post("/{server_id}/discover", response_model=ServerInventorySchema)
async def discover_server(
    server_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    service = AgentService(db)
    return await service.run_discovery(server_id)

@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_server(server_id: uuid.UUID, db: Session = Depends(get_db)):
    repository = ServerRepository(db)
    service = ServerService(repository)
    service.delete_server(server_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


