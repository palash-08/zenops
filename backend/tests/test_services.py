import uuid
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

from services.prompt_builder import PromptBuilder
from services.execution_resolver import ExecutionResolver, ExecutionMode, ExecutionTarget


class TestPromptBuilder:
    def test_build_creates_prompt_context(self, mock_server):
        builder = PromptBuilder()
        memories = "Server has Docker installed."
        recent_messages = []
        current_request = "Show me disk usage"

        result = builder.build(mock_server, memories, recent_messages, current_request)

        assert result.final_prompt is not None
        assert "test-server" in result.final_prompt
        assert "Server has Docker installed." in result.final_prompt
        assert "Show me disk usage" in result.final_prompt
        assert result.system_prompt is not None
        assert result.cognee_memories is not None

    def test_build_with_conversation_history(self, mock_server):
        builder = PromptBuilder()
        msg = MagicMock()
        msg.role = "user"
        msg.content = "What is the status?"

        result = builder.build(mock_server, "", [msg], "Check again")

        assert "User:" in result.conversation_history
        assert "What is the status?" in result.conversation_history

    def test_build_without_memories(self, mock_server):
        builder = PromptBuilder()
        result = builder.build(mock_server, "", [], "Hello")
        assert result.cognee_memories.strip() == ""

    def test_build_memories_empty_string(self, mock_server):
        builder = PromptBuilder()
        result = builder.build(mock_server, "  ", [], "Hello")
        assert result.cognee_memories.strip() == ""


class TestExecutionResolver:
    def test_resolve_global(self, mock_db_session):
        binding_service = MagicMock()
        binding_service.is_global = MagicMock(return_value=True)

        resolver = ExecutionResolver(mock_db_session)
        resolver.binding_service = binding_service

        target = resolver.resolve("guild1", "channel1")

        assert target.mode == ExecutionMode.GLOBAL
        assert target.server_id is None

    def test_resolve_bound(self, mock_db_session):
        binding = MagicMock()
        binding.server_id = uuid.uuid4()

        binding_service = MagicMock()
        binding_service.is_global = MagicMock(return_value=False)
        binding_service.get_binding = MagicMock(return_value=binding)

        resolver = ExecutionResolver(mock_db_session)
        resolver.binding_service = binding_service

        target = resolver.resolve("guild1", "channel1")

        assert target.mode == ExecutionMode.BOUND
        assert target.server_id == binding.server_id

    def test_resolve_unbound_single_server(self, mock_db_session):
        server = MagicMock()
        server.id = uuid.uuid4()

        binding_service = MagicMock()
        binding_service.is_global = MagicMock(return_value=False)
        binding_service.get_binding = MagicMock(return_value=None)

        server_repo = MagicMock()
        server_repo.list_servers = MagicMock(return_value=[server])

        resolver = ExecutionResolver(mock_db_session)
        resolver.binding_service = binding_service
        resolver.server_repository = server_repo

        target = resolver.resolve("guild1", "channel1")

        assert target.mode == ExecutionMode.UNBOUND
        assert target.server_id == server.id

    def test_resolve_no_servers(self, mock_db_session):
        binding_service = MagicMock()
        binding_service.is_global = MagicMock(return_value=False)
        binding_service.get_binding = MagicMock(return_value=None)

        server_repo = MagicMock()
        server_repo.list_servers = MagicMock(return_value=[])

        resolver = ExecutionResolver(mock_db_session)
        resolver.binding_service = binding_service
        resolver.server_repository = server_repo

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            resolver.resolve("guild1", "channel1")
        assert exc.value.status_code == 400

    def test_resolve_multiple_servers_no_binding(self, mock_db_session):
        binding_service = MagicMock()
        binding_service.is_global = MagicMock(return_value=False)
        binding_service.get_binding = MagicMock(return_value=None)

        server_repo = MagicMock()
        server_repo.list_servers = MagicMock(return_value=[MagicMock(), MagicMock()])

        resolver = ExecutionResolver(mock_db_session)
        resolver.binding_service = binding_service
        resolver.server_repository = server_repo

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            resolver.resolve("guild1", "channel1")
        assert exc.value.status_code == 400


class TestExecutionMode:
    def test_enum_values(self):
        assert ExecutionMode.BOUND.value == "BOUND"
        assert ExecutionMode.GLOBAL.value == "GLOBAL"
        assert ExecutionMode.UNBOUND.value == "UNBOUND"

    def test_enum_members(self):
        assert ExecutionMode("BOUND") == ExecutionMode.BOUND
        assert ExecutionMode("GLOBAL") == ExecutionMode.GLOBAL
        assert ExecutionMode("UNBOUND") == ExecutionMode.UNBOUND

    def test_enum_inherits_str(self):
        assert isinstance(ExecutionMode.BOUND, str)
        assert isinstance(ExecutionMode.GLOBAL, str)
        assert isinstance(ExecutionMode.UNBOUND, str)


class TestCogneeClient:
    @pytest.mark.asyncio
    async def test_health_success(self):
        from services.cognee_client import CogneeClient

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("services.cognee_client.httpx.AsyncClient", return_value=mock_client):
            client = CogneeClient()
            result = await client.health()

        assert result is True

    @pytest.mark.asyncio
    async def test_recall_returns_list(self):
        from services.cognee_client import CogneeClient

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value=[])
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("services.cognee_client.httpx.AsyncClient", return_value=mock_client):
            client = CogneeClient()
            result = await client.recall("test query", "dataset-1", limit=5)

        assert result == []


class TestOpenClawClient:
    @pytest.mark.asyncio
    async def test_create_response_success(self):
        from services.openclaw_client import OpenClawClient

        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={"output": [{"text": "ok"}]})
        mock_client.post = AsyncMock(return_value=mock_response)

        client = OpenClawClient("https://gateway:443", "token")
        client.client = mock_client

        result = await client.create_response({"model": "default", "input": "hello"})

        assert result == {"output": [{"text": "ok"}]}

    @pytest.mark.asyncio
    async def test_create_response_unauthorized(self):
        from services.openclaw_client import OpenClawClient, OpenClawError
        import httpx

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_client.post = AsyncMock(side_effect=httpx.HTTPStatusError(
            "401", request=MagicMock(), response=mock_response
        ))

        client = OpenClawClient("https://gateway:443", "bad-token")
        client.client = mock_client

        with pytest.raises(OpenClawError, match="Authentication"):
            await client.create_response({"model": "default", "input": "hello"})

    @pytest.mark.asyncio
    async def test_close(self):
        from services.openclaw_client import OpenClawClient

        mock_client = AsyncMock()
        client = OpenClawClient("https://gateway:443", "token")
        client.client = mock_client

        await client.close()
        mock_client.aclose.assert_awaited_once()
