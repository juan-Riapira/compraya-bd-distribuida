"""Difusión de eventos en vivo hacia los navegadores conectados (Server-Sent Events)."""
import asyncio
import json
from collections import defaultdict


class Broadcaster:
    def __init__(self) -> None:
        self._queues: dict[str, set[asyncio.Queue]] = defaultdict(set)

    def subscribe(self, run_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=2000)
        self._queues[run_id].add(queue)
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue) -> None:
        self._queues[run_id].discard(queue)

    async def publish(self, run_id: str, event: str, data: dict) -> None:
        message = f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"
        for queue in list(self._queues[run_id]):
            if queue.full():
                continue  # un navegador lento no frena la simulación
            queue.put_nowait(message)
