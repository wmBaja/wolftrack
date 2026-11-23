import asyncio
from types import SimpleNamespace

from src.core.ws_manager import ConnectionManager


class FakeWebSocket:
    def __init__(self):
        self.messages = []

    async def accept(self):
        pass

    async def send_json(self, message):
        self.messages.append(message)


def test_subscriptions_are_per_connection_and_disconnect_preserves_other_clients():
    async def exercise():
        manager = ConnectionManager()
        first = FakeWebSocket()
        second = FakeWebSocket()
        await manager.connect(first)
        await manager.connect(second)
        manager.subscribe(first, ["Vehicle.speed"], 10)
        manager.subscribe(second, ["Engine.rpm"], 20)

        assert manager.subscribed_signals == {"Vehicle.speed", "Engine.rpm"}
        await manager.broadcast_json({
            "type": "live_batch",
            "signals": {
                "Vehicle.speed": {"values": [1]},
                "Engine.rpm": {"values": [2]},
            },
            "dropped_batches": 0,
        })

        assert first.messages[0]["signals"] == {"Vehicle.speed": {"values": [1]}}
        assert second.messages[0]["signals"] == {"Engine.rpm": {"values": [2]}}

        manager.disconnect(first)
        assert manager.subscribed_signals == {"Engine.rpm"}

    asyncio.run(exercise())
