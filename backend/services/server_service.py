import uuid
from fastapi import HTTPException, status
from repositories.server_repository import ServerRepository
from schemas.server import ServerCreate, ServerResponse

class ServerService:
    def __init__(self, repository: ServerRepository):
        self.repository = repository

    def register_server(self, server_in: ServerCreate) -> ServerResponse:
        # 1. Check if a server with the exact same name already exists
        existing_server = self.repository.get_server_by_name(server_in.name)
        if existing_server:
            # 2. Raise an error if it does, stopping the process
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Server with name '{server_in.name}' already exists."
            )

        # 3. Ask the repository to create and save the new server to the database
        new_server = self.repository.create_server(
            name=server_in.name,
            description=server_in.description,
            tailscale_ip=server_in.tailscale_ip,
            gateway_port=server_in.gateway_port,
            gateway_token=server_in.gateway_token
        )

        # 4. Convert the database (ORM) model into our Pydantic response schema
        return ServerResponse.model_validate(new_server)

    def get_server(self, server_id: uuid.UUID) -> ServerResponse:
        # Fetch the server from the repository
        server = self.repository.get_server_by_id(server_id)
        if not server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Server not found."
            )
        return ServerResponse.model_validate(server)

    def list_servers(self) -> list[ServerResponse]:
        # Fetch all servers from the repository
        servers = self.repository.list_servers()
        # Convert all ORM models to Pydantic schemas before returning
        return [ServerResponse.model_validate(server) for server in servers]

    def delete_server(self, server_id: uuid.UUID) -> None:
        deleted_server = self.repository.delete_server(server_id)
        if deleted_server is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Server not found."
            )
