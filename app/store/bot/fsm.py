from abc import abstractmethod, ABC

from app.bot.game.models import GameState
db_states = {
    1213: {
        "state": GameState.INACTIVE,
        "data": {}
    }
}

class StateStorage(ABC):
    @abstractmethod
    def get_state(self, chat_id: int):
        pass

    @abstractmethod
    def set_state(self, chat_id: int, state: GameState):
        pass

    @abstractmethod
    def update_data(self, chat_id: int, **kwargs):
        pass

    @abstractmethod
    def get_data(self, chat_id: int):
        pass

    @abstractmethod
    def clear_data(self, chat_id: int):
        pass

class MemoryStorage(StateStorage):
    def get_state(self, chat_id: int):
        query = db_states.get(chat_id)
        if query is None:
            query = self.set_state(chat_id=chat_id, state=GameState.INACTIVE)
        return query.get("state")

    def set_state(self, chat_id: int, state: GameState):
        query = db_states.get(chat_id)
        print(query)
        if query:
            query["state"] = state
        else:
            db_states[chat_id] = {"state": state, "data": {}}
            query = db_states[chat_id]
        return query

    def update_data(self, chat_id: int, **kwargs):
        query = db_states.get(chat_id)
        if query is None:
            query = self.set_state(chat_id, GameState.INACTIVE)

        query["data"] = kwargs


    def get_data(self, chat_id: int):
        query = db_states.get(chat_id)
        if query is None:
            query = self.set_state(chat_id, GameState.INACTIVE)
        return query["data"]

    def clear_data(self, chat_id: int):
        query = db_states.get(chat_id)
        if query is None:
            query = self.set_state(chat_id, GameState.INACTIVE)
        del query["data"]

class FSMContext:
    """Контекст FSM для хранения состояния пользователя/чата"""

    def __init__(self):
        self.storage: StateStorage = MemoryStorage()

    def get_state(self, chat_id: int):
        return  self.storage.get_state(chat_id=chat_id)


    def set_state(self, chat_id: int, state: GameState) -> None:
        self.storage.set_state(chat_id=chat_id, state=state)

    def update_data(self, chat_id: int, **kwargs) -> None:
        self.storage.update_data(chat_id=chat_id)

    def get_data(self, chat_id: int):
        self.storage.get_data(chat_id=chat_id)

    def clear_data(self, chat_id: int) -> None:
        self.storage.clear_data(chat_id=chat_id)
