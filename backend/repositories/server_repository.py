import uuid

from sqlalchemy.orm import Session

from models.server import Server


class ServerRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_server(
        self,
        name: str,
        tailscale_ip: str,
        gateway_port: int,
        gateway_token: str,
        description: str | None = None,
    ) -> Server:
        """Create and persist a new server."""

        server = Server(
            name=name,
            description=description,
            tailscale_ip=tailscale_ip,
            gateway_port=gateway_port,
            gateway_token=gateway_token,
        )

        self.db.add(server)
        self.db.commit()
        self.db.refresh(server)

        return server

    def get_server_by_id(
        self,
        server_id: uuid.UUID,
    ) -> Server | None:
        """Retrieve a server by its UUID."""

        return (
            self.db.query(Server)
            .filter(Server.id == server_id)
            .first()
        )

    def get_server_by_name(
        self,
        name: str,
    ) -> Server | None:
        """Retrieve a server by its name."""

        return (
            self.db.query(Server)
            .filter(Server.name == name)
            .first()
        )

    def list_servers(self) -> list[Server]:
        """Return all registered servers."""

        return self.db.query(Server).all()

    def delete_server(
        self,
        server_id: uuid.UUID,
    ) -> Server | None:
        """Delete a server and return the deleted object."""

        server = self.get_server_by_id(server_id)

        if server is None:
            return None

        self.db.delete(server)
        self.db.commit()

        return server