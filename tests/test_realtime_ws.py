from __future__ import annotations

import pytest

from api.realtime import state


class FakeWebSocket:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    async def accept(self) -> None:
        return None

    async def send_json(self, payload: dict[str, object]) -> None:
        self.messages.append(payload)


async def test_realtime_manager_broadcasts_burst() -> None:
    websocket = FakeWebSocket()
    await state.manager.connect(websocket)  # type: ignore[arg-type]

    try:
        for index in range(1000):
            await state.manager.broadcast(
                {
                    "type": "measurement.processed",
                    "sequence": index,
                    "equipment_id": "CMM-001",
                    "process_name": "line-1",
                }
            )

        assert len(websocket.messages) == 1000
        assert websocket.messages[0]["type"] == "measurement.processed"
        assert websocket.messages[-1]["sequence"] == 999
    finally:
        await state.manager.disconnect(websocket)  # type: ignore[arg-type]
