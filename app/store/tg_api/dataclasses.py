import abc
from dataclasses import dataclass
from pprint import pprint
from typing import Optional, Any, Callable


@dataclass
class UserORBotTG:
    first_name: str
    id_: int
    is_bot: bool
    is_premium: Optional[bool] = None
    language_code: Optional[str] = None
    username: Optional[str] = None

    @classmethod
    def from_dict(cls, data):
        if data:
            return cls(
                first_name=data.get("first_name", ""),
                id_=data.get("id"),
                is_bot=data.get("is_bot", False),
                is_premium=data.get("is_premium"),
                language_code=data.get("language_code"),
                username=data.get("username")
            )
        return None


@dataclass
class EntityTG:
    length: int
    offset: int
    type: str

    @classmethod
    def from_dict(cls, data):
        return cls(
            length=data.get("length"),
            offset=data.get("offset"),
            type=data.get("type"),
        )


@dataclass
class ChatTG:
    id_: int
    type: str
    title: Optional[str] = None

    @classmethod
    def from_dict(cls, data):
        return cls(
            id_=data.get("id"),
            title=data.get("title"),
            type=data.get("type"),
        )

class UpdateABC(abc.ABC):
    from_: UserORBotTG
    chat: Optional[ChatTG]

    @abc.abstractmethod
    def from_dict(self, data):
        pass

@dataclass
class CommandTG(UpdateABC):
    text: str
    chat: ChatTG
    from_: UserORBotTG

    @classmethod
    def from_dict(cls, data):
        return cls(
            text=data["text"],
            chat=ChatTG.from_dict(data["chat"]),
            from_=data["from"]
        )



@dataclass
class MessageTG(UpdateABC):
    message_id: int
    date: int
    chat: ChatTG
    from_: Optional[UserORBotTG] = None
    text: Optional[str] = None
    caption: Optional[str] = None
    entities: Optional[list[EntityTG]] = None
    caption_entities: Optional[list[EntityTG]] = None
    photo: Any = None
    document: Any = None
    location: Any = None
    contact: Any = None
    reply_markup: Any = None
    reply_to_message: Optional['MessageTG'] = None
    forward_from: Optional[UserORBotTG] = None
    forward_from_chat: Optional[ChatTG] = None


    @classmethod
    def from_dict(cls, data: dict):
        def create_nested(field: str, factory: Callable):
            if field_data := data.get(field):
                return factory(field_data)
            return None

        def create_list(field: str, factory: Callable):
            if field_data := data.get(field):
                return [factory(item) for item in field_data]
            return None

        return cls(
            message_id=data.get("message_id"),
            date=data.get("date"),
            chat=create_nested("chat", ChatTG.from_dict),
            from_=create_nested("from", UserORBotTG.from_dict),
            text=data.get("text"),
            caption=data.get("caption"),
            entities=create_list("entities", EntityTG.from_dict),
            caption_entities=create_list("caption_entities", EntityTG.from_dict),
            photo=data.get("photo"),
            document=data.get("document"),
            location=data.get("location"),
            contact=data.get("contact"),
            reply_markup=data.get("reply_markup"),
            reply_to_message=create_nested("reply_to_message", MessageTG.from_dict),
            forward_from=create_nested("forward_from", UserORBotTG.from_dict),
            forward_from_chat=create_nested("forward_from_chat", ChatTG.from_dict),
        )

    @property
    def is_command(self):
        if self.entities:
            for entity in self.entities:
                if entity.type == "bot_command":
                    return True
        return False

    def to_command(self) -> Optional[CommandTG]:
        for entity in self.entities:
            if entity.type == "bot_command":
                return CommandTG(
                    text=self.text[entity.offset:entity.length + entity.offset],
                    from_=self.from_,
                    chat=self.chat
                )
        return None

@dataclass
class CallbackTG(UpdateABC):
    id_: str
    from_: UserORBotTG
    message: Optional[MessageTG] = None
    inline_message_id: Optional[str] = None
    chat_instance: Optional[str] = None
    data: Optional[str] = None
    game_short_name: Optional[str] = None

    @property
    def chat(self):
        return self.message.chat

    @classmethod
    def from_dict(cls, data):
        def create_nested(field: str, factory: Callable):
            if field_data := data.get(field):
                return factory(field_data)
            return None

        return cls(
            id_=data.get("id"),
            from_=create_nested("from", UserORBotTG.from_dict),
            message=create_nested("message", MessageTG.from_dict),
            inline_message_id=data.get("inline_message_id"),
            chat_instance=data.get("chat_instance"),
            data=data.get("data"),
            game_short_name=data.get("game_short_name"),
        )

