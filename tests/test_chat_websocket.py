"""Tests for WebSocket chat endpoint and connection manager."""

import asyncio
import contextlib
import json
import uuid
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.websocket_manager import WebSocketConnectionManager


class TestWebSocketConnectionManager:
    """Unit tests for WebSocketConnectionManager (no DB required)."""

    @pytest.mark.asyncio
    async def test_connect_adds_connection(self) -> None:
        manager = WebSocketConnectionManager()
        thread_id = uuid.uuid4()
        user_id = uuid.uuid4()
        ws = Mock()
        ws.accept = AsyncMock()

        await manager.connect(ws, thread_id, user_id)

        assert thread_id in manager.thread_connections
        assert ws in manager.thread_connections[thread_id]
        assert manager.connection_meta[ws]["thread_id"] == thread_id
        assert manager.connection_meta[ws]["user_id"] == user_id

    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self) -> None:
        manager = WebSocketConnectionManager()
        thread_id = uuid.uuid4()
        user_id = uuid.uuid4()
        ws = Mock()
        ws.accept = AsyncMock()

        await manager.connect(ws, thread_id, user_id)
        await manager.disconnect(ws)

        assert ws not in manager.connection_meta
        assert (
            thread_id not in manager.thread_connections
            or ws not in manager.thread_connections[thread_id]
        )

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all_connections(self) -> None:
        manager = WebSocketConnectionManager()
        thread_id = uuid.uuid4()
        user_id1 = uuid.uuid4()
        user_id2 = uuid.uuid4()

        ws1 = Mock()
        ws1.accept = AsyncMock()
        ws1.send_text = AsyncMock()
        ws2 = Mock()
        ws2.accept = AsyncMock()
        ws2.send_text = AsyncMock()

        await manager.connect(ws1, thread_id, user_id1)
        await manager.connect(ws2, thread_id, user_id2)

        message_data = {"id": str(uuid.uuid4()), "body": "Hello"}
        await manager.broadcast(thread_id, message_data)

        assert ws1.send_text.called
        assert ws2.send_text.called

        for call in ws1.send_text.call_args_list + ws2.send_text.call_args_list:
            payload = json.loads(call[0][0])
            assert payload["type"] == "message"
            assert payload["data"] == message_data

    @pytest.mark.asyncio
    async def test_broadcast_no_connections_for_thread(self) -> None:
        manager = WebSocketConnectionManager()
        thread_id = uuid.uuid4()
        message_data = {"id": str(uuid.uuid4()), "body": "Hello"}

        await manager.broadcast(thread_id, message_data)

    @pytest.mark.asyncio
    async def test_send_heartbeat(self) -> None:
        manager = WebSocketConnectionManager()
        ws = Mock()
        ws.send_json = AsyncMock()

        await manager.send_heartbeat(ws)

        ws.send_json.assert_called_once()
        call_args = ws.send_json.call_args[0][0]
        assert call_args["type"] == "heartbeat"

    @pytest.mark.asyncio
    async def test_heartbeat_loop_sends_periodic_pings(self) -> None:
        manager = WebSocketConnectionManager()
        thread_id = uuid.uuid4()
        user_id = uuid.uuid4()
        ws = Mock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()

        await manager.connect(ws, thread_id, user_id)

        task = asyncio.create_task(manager.heartbeat_loop(ws, interval=0.01))
        await asyncio.sleep(0.05)
        task.cancel()

        with contextlib.suppress(asyncio.CancelledError):
            await task

        assert ws.send_json.call_count >= 2

    @pytest.mark.asyncio
    async def test_shutdown_cancels_heartbeat_tasks(self) -> None:
        manager = WebSocketConnectionManager()

        task1 = asyncio.create_task(asyncio.sleep(100))
        task2 = asyncio.create_task(asyncio.sleep(100))
        manager._heartbeat_tasks.add(task1)
        manager._heartbeat_tasks.add(task2)

        await manager.shutdown()
        await asyncio.sleep(0)

        assert task1.cancelled()
        assert task2.cancelled()
        assert len(manager._heartbeat_tasks) == 0

    @pytest.mark.asyncio
    async def test_heartbeat_loop_continues_while_connected(self) -> None:
        manager = WebSocketConnectionManager()
        thread_id = uuid.uuid4()
        user_id = uuid.uuid4()
        ws = Mock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()

        await manager.connect(ws, thread_id, user_id)

        task = asyncio.create_task(manager.heartbeat_loop(ws, interval=0.01))
        await asyncio.sleep(0.03)

        assert not task.done()

        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_threads_isolated(self) -> None:
        manager = WebSocketConnectionManager()
        thread1 = uuid.uuid4()
        thread2 = uuid.uuid4()
        user_id = uuid.uuid4()

        ws1 = Mock()
        ws1.accept = AsyncMock()
        ws1.send_text = AsyncMock()
        ws2 = Mock()
        ws2.accept = AsyncMock()
        ws2.send_text = AsyncMock()

        await manager.connect(ws1, thread1, user_id)
        await manager.connect(ws2, thread2, user_id)

        message_data = {"id": str(uuid.uuid4()), "body": "Hello"}
        await manager.broadcast(thread1, message_data)

        ws1.send_text.assert_called_once()
        ws2.send_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_disconnect_removes_thread_if_empty(self) -> None:
        manager = WebSocketConnectionManager()
        thread_id = uuid.uuid4()
        user_id = uuid.uuid4()
        ws = Mock()
        ws.accept = AsyncMock()

        await manager.connect(ws, thread_id, user_id)
        assert thread_id in manager.thread_connections

        await manager.disconnect(ws)

        assert (
            thread_id not in manager.thread_connections
            or len(manager.thread_connections.get(thread_id, set())) == 0
        )
