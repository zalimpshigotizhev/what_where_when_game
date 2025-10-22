import asyncio
import typing
from asyncio import Future, Task

from aiohttp import ClientOSError

if typing.TYPE_CHECKING:
    from app.store import Store


class Poller:
    def __init__(self, store: "Store") -> None:
        self.store = store
        self.is_running = False
        self.poll_task: Task | None = None

    def _done_callback(self, result: Future) -> None:
        if result.exception():
            self.store.tg_api.app.logger.exception(
                "poller stopped with exception", exc_info=result.exception()
            )
        if self.is_running:
            self.start()

    def start(self) -> None:
        self.is_running = True

        self.poll_task = asyncio.create_task(self.poll())
        self.poll_task.add_done_callback(self._done_callback)

    async def stop(self) -> None:
        self.is_running = False

        await self.poll_task

    async def poll(self) -> None:
        while self.is_running:
            try:
                await self.store.tg_api.poll()
            except TimeoutError as e:
                self.store.mq_manager.logger.warning(
                    "Poll request timed out, retrying... %s", e
                )
                return
            except ClientOSError as e:
                self.store.mq_manager.logger.warning(
                    "Network error: %s, retrying...", e
                )
                return

            except Exception as e:
                self.store.mq_manager.logger.error(
                    "Unexpected error in poll: %s", e
                )
                return
