import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from schemas.server import ServerCreate, ServerResponse
from repositories.server_repository import ServerRepository
from services.server_service import ServerService

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
