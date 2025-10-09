import re
from functools import wraps
from typing import Any

from app.bot.game.models import GameState
from app.store.fsm.fsm import FSMContext
from app.store.tg_api.dataclasses import (
    CallbackTG,
    CommandTG,
    MessageTG,
    UpdateABC,
)


class Filter:
    """Базовый класс для фильтров"""

    def __call__(self, update: UpdateABC, context: FSMContext) -> bool:
        return self.check(update, context)

    def check(self, update: UpdateABC, context: FSMContext) -> bool:
        raise NotImplementedError


class TypeFilter(Filter):
    def __init__(self, expected_type: type[UpdateABC]):
        self.expected_type = expected_type

    def check(self, update: UpdateABC, context: FSMContext) -> bool:
        return isinstance(update, self.expected_type)


class StateFilter(Filter):
    def __init__(self, expected_state: GameState):
        self.expected_state = expected_state

    def check(self, update: UpdateABC, context: GameState | None) -> bool:
        return context == self.expected_state


class TextFilter(Filter):
    def __init__(self, text: str):
        self.text = text

    def check(self, update: UpdateABC, context: FSMContext) -> bool:
        return (
            isinstance(update, MessageTG)
            or isinstance(update, CommandTG)
            and update.text == self.text
        )


class CallbackDataFilter(Filter):
    def __init__(self, callback_data: str):
        self.callback_data = callback_data

    def check(self, update: UpdateABC, context: FSMContext) -> bool:
        return (
            isinstance(update, CallbackTG) and update.data == self.callback_data
        )


def filtered_handler(*filters: Filter):
    """Улучшенный декоратор для хендлеров"""

    def decorator(func: callable):
        @wraps(func)
        async def wrapper(self, update: UpdateABC, context: FSMContext) -> Any:
            # Проверяем все фильтры
            for filter_obj in filters:
                if not filter_obj(update, context):
                    return None

            return await func(self, update, context)

        return wrapper

    return decorator


def escape_markdown(text):
    """Функция для избежания конфликтов в MarkdownV2"""
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)
