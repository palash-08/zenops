import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from schemas.server import ServerCreate, ServerResponse, ServerExecuteRequest, ServerInventorySchema
from repositories.server_repository import ServerRepository
from services.server_service import ServerService
from services.agent_service import AgentService

router = APIRouter(
    prefix="/servers",
    tags=["Servers"]
)

@router.post("", response_model=ServerResponse)
def create_server(server_in: ServerCreate, db: Session = Depends(get_db)):
    # 1. Instantiate the repository, injecting the database session
    repository = ServerRepository(db)
    
    # 2. Instantiate the service, injecting the repository
    service = ServerService(repository)
    
    # 3. Call the business logic and return the result
    return service.register_server(server_in)

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

