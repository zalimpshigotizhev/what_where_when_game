import asyncio
import typing
from collections.abc import Callable

if typing.TYPE_CHECKING:
    from app.web.app import Application


class Timer:
    def __init__(
        self,
        app: "Application",
        timeout: float,
        callback: Callable,
        type_timer,
        **kwargs,
    ):
        # Время по истечению которого вызывается
        # переданная функция (callback)
        self.app = app
        self.timeout = timeout
        self.type_timer = type_timer
        # переданная функция (callback)
        self.callback = callback
        # ожидаемые аргументы для функции
        self.kwargs = kwargs
        # Будет лежать запущенный таймер
        self.task: asyncio.Task | None = None
        # Флаг, благодаря которой можно
        # преждевременно завершить таймер
        self._cancelled = False

    async def _run(self):
        try:
            self.app.logger.info("Начинается ожидание %s", self.type_timer)
            await asyncio.sleep(self.timeout)
            if not self._cancelled:
                self.app.logger.info(
                    "Вызывается переданная функция %s", self.type_timer
                )
                await self.callback(**self.kwargs)
        except asyncio.CancelledError:
            pass

    def start(self):
        self.task = asyncio.create_task(self._run())

    def cancel(self):
        self.app.logger.info("Отмена таймера %s", self.type_timer)
        self._cancelled = True
        if self.task:
            self.task.cancel()

    def is_running(self):
        return self.task and not self.task.done()
