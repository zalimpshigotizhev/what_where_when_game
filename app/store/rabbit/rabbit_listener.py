import asyncio
import typing
from asyncio import Future, Task
from logging import getLogger

if typing.TYPE_CHECKING:
    from app.store import Store


class RabbitMQListener:
    def __init__(self, store: "Store") -> None:
        self.store = store
        self.logger = getLogger("rabbit_listener")
        self.is_running = False
        self.listener_task: Task | None = None

    def _done_callback(self, result: Future) -> None:
        if result.exception():
            self.logger.exception(
                "poller stopped with exception", exc_info=result.exception()
            )
        if self.is_running:
            self.start()

    def start(self) -> None:
        self.is_running = True

        self.listener_task = asyncio.create_task(self.listener())
        self.listener_task.add_done_callback(self._done_callback)

    async def stop(self) -> None:
        self.is_running = False

        await self.listener_task

    async def listener(self) -> None:
        while self.is_running:
            await self.store.rabbit.wait_updates_for_game()
