from unittest.mock import MagicMock, AsyncMock
import pytest


@pytest.fixture
def mock_server():
    server = MagicMock()
    server.id = MagicMock()
    server.id.__str__ = MagicMock(return_value="550e8400-e29b-41d4-a716-446655440000")
    server.name = "test-server"
    server.description = "Test server"
    server.tailscale_ip = "100.100.100.100"
    server.gateway_port = 443
    server.gateway_token = "test-token"
    server.gateway_url = "https://100.100.100.100:443"
    server.cognee_dataset_id = MagicMock()
    server.cognee_dataset_id.__str__ = MagicMock(return_value="660e8400-e29b-41d4-a716-446655440000")
    server.inventory = MagicMock()
    server.inventory.hostname = "test-host"
    return server


@pytest.fixture
def mock_db_session():
    session = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()
    session.add = MagicMock()
    session.execute = MagicMock()
    session.query = MagicMock()
    return session


@pytest.fixture
def mock_memory_service():
    memory = AsyncMock()
    memory.recall = AsyncMock(return_value="")
    memory.remember_conversation = AsyncMock()
    memory.remember_discovery = AsyncMock()
    return memory
