import typing
from logging import getLogger

from app.store.bot.fsm import FSMContext
from app.store.bot.gamebot import (
    AreReadyFirstRoundPlayersProcessGameBot,
    AreReadyNextRoundPlayersProcessGameBot,
    MainGameBot,
    QuestionDiscussionProcessGameBot,
    VerdictCaptain,
    WaitAnswer,
    WaitingPlayersProcessGameBot,
)
from app.store.tg_api.dataclasses import UpdateABC

if typing.TYPE_CHECKING:
    from app.web.app import Application


class BotManager:
    def __init__(self, app: "Application"):
        self.app = app
        self.fsm = FSMContext()
        self.states_handler = [
            MainGameBot(self.app),
            WaitingPlayersProcessGameBot(self.app),
            AreReadyFirstRoundPlayersProcessGameBot(self.app),
            QuestionDiscussionProcessGameBot(self.app),
            VerdictCaptain(self.app),
            WaitAnswer(self.app),
            AreReadyNextRoundPlayersProcessGameBot(self.app),
        ]
        self.logger = getLogger("handler")
        self._handlers: list | None = None

        self._add_handlers_in_list()

    def _add_handlers_in_list(self):
        if self._handlers is None:
            self._handlers = []
            for state_handler in self.states_handler:
                self._handlers.extend(state_handler.handlers)
        return self._handlers

    # TODO: СДелать Мидлварь для обработки исключений
    async def handle_updates(self, updates: list[UpdateABC]):
        for update in updates:
            for handler in self._handlers:
                if callable(handler):
                    result = await handler(update, self.fsm)
                    if result is not None:
                        break
