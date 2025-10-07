import asyncio
from collections.abc import Callable


class Timer:
    def __init__(self, timeout: float, callback: Callable, **kwargs):
        # Время по истечению которого вызывается
        # переданная функция (callback)
        self.timeout = timeout
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
            await asyncio.sleep(self.timeout)
            if not self._cancelled:
                await self.callback(**self.kwargs)
        except asyncio.CancelledError:
            pass

    def start(self):
        self.task = asyncio.create_task(self._run())

    def cancel(self):
        self._cancelled = True
        if self.task and not self.task.done():
            self.task.cancel()

    def is_running(self):
        return self.task and not self.task.done()
