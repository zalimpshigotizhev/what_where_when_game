import typing
from collections.abc import Callable

from app.store.timer.timer import Timer

if typing.TYPE_CHECKING:
    from app.web.app import Application


class TimerManager:
    """Тайм менеджер который необходим для бота"""

    def __init__(self, app: "Application"):
        self.app = app
        self.timers: dict[str, dict[str, Timer]] = {}

    def create_timer_key(self, chat_id: int, timer_type: str) -> str:
        return f"{chat_id}_{timer_type}"

    async def default_timeout_action(self, chat_id: int, **kwargs):
        pass

    def start_timer(
        self,
        chat_id: int,
        timeout: float,
        timer_type: str,
        callback: Callable | None,
        **kwargs,
    ):
        """Запуск таймера"""
        # Отменяем предыдущий таймер того же типа
        self.cancel_timer(chat_id=chat_id, timer_type=timer_type)
        created_key = self.create_timer_key(
            chat_id=chat_id, timer_type=timer_type
        )

        # Создаем и запускаем таймер
        self.app.logger.info("Создаем таймер %s", created_key)
        timer = Timer(timeout=timeout, callback=callback, **kwargs)

        if self.timers.get(str(chat_id)) is None:
            self.timers[str(chat_id)] = {}

        self.timers[str(chat_id)][created_key] = timer
        self.app.logger.info("Запускаем таймер %s", created_key)
        timer.start()

        return chat_id

    def cancel_timer(self, chat_id: int, timer_type: str):
        """Отмена таймера"""
        created_key = self.create_timer_key(chat_id, timer_type)
        if str(chat_id) in self.timers:
            curr_chat_timers = self.timers[str(chat_id)]

            if curr_chat_timers.get(created_key) is not None:
                self.app.logger.info("Отменяем таймер %s", created_key)
                curr_chat_timers[created_key].cancel()
                del curr_chat_timers[created_key]
            return True
        return False

    def clean_timers(self, chat_id: int):
        if self.timers.get(str(chat_id)):
            self.app.logger.info("Удаляем все таймеры этого чата %s", chat_id)
            timers_for_chat = self.timers[str(chat_id)]

            for timer in timers_for_chat.values():
                timer.cancel()

            del self.timers[str(chat_id)]

    def has_active_timer(self, chat_id: int, timer_type: str) -> bool:
        """Проверка активного таймера"""
        created_key = self.create_timer_key(chat_id, timer_type)
        chat_id_str = str(chat_id)

        return (
            chat_id_str in self.timers
            and created_key in self.timers[chat_id_str]
            and self.timers[chat_id_str][created_key].is_running()
        )
