from collections.abc import Callable

from app.store.timer.timer import Timer


class TimerManager:
    """Тайм менеджер который необходим для бота"""

    def __init__(self, app):
        self.app = app
        self.timers: dict[str, Timer] = {}

    def create_timer_key(self, chat_id: int, timer_type: str) -> str:
        return f"{chat_id}_{timer_type}"

    async def default_timeout_action(self, chat_id: int, **kwargs):
        pass

    def start_timer(
        self,
        chat_id: int,
        timeout: float,
        timer_type: str = "default",
        callback: Callable | None = None,
        **kwargs,
    ):
        """Запуск таймера"""
        # Отменяем предыдущий таймер того же типа
        self.cancel_timer(chat_id, timer_type)

        # Создаем callback если не передан
        if callback is None:
            callback = self.default_timeout_action

        # Создаем и запускаем таймер
        timer = Timer(timeout=timeout, callback=callback, **kwargs)
        timer_key = self.create_timer_key(
            chat_id=chat_id,
            timer_type=timer_type,
        )
        self.timers[timer_key] = timer
        timer.start()

        return timer_key

    def cancel_timer(self, chat_id: int, timer_type: str = "default"):
        """Отмена таймера"""
        timer_key = self.create_timer_key(
            chat_id=chat_id,
            timer_type=timer_type,
        )
        if timer_key in self.timers:
            self.timers[timer_key].cancel()
            del self.timers[timer_key]
            return True
        return False

    def has_active_timer(
        self, user_id: int, timer_type: str = "default"
    ) -> bool:
        """Проверка активного таймера"""
        timer_key = self.create_timer_key(user_id, timer_type)
        return timer_key in self.timers and self.timers[timer_key].is_running()
