import abc
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class UserORBotTG:
    first_name: str
    id_: int
    is_bot: bool
    is_premium: bool | None = None
    language_code: str | None = None
    username: str | None = None

    @classmethod
    def from_dict(cls, data):
        if data:
            return cls(
                first_name=data.get("first_name", ""),
                id_=data.get("id"),
                is_bot=data.get("is_bot", False),
                is_premium=data.get("is_premium"),
                language_code=data.get("language_code"),
                username=data.get("username"),
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
    title: str | None = None

    @classmethod
    def from_dict(cls, data):
        return cls(
            id_=data.get("id"),
            title=data.get("title"),
            type=data.get("type"),
        )


class UpdateABC(abc.ABC):
    from_: UserORBotTG
    chat: ChatTG | None

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
            from_=data["from"],
        )


@dataclass
class MessageTG(UpdateABC):
    message_id: int
    date: int
    chat: ChatTG
    from_: UserORBotTG | None = None
    text: str | None = None
    caption: str | None = None
    entities: list[EntityTG] | None = None
    caption_entities: list[EntityTG] | None = None
    photo: Any = None
    document: Any = None
    location: Any = None
    contact: Any = None
    reply_markup: Any = None
    reply_to_message: type["MessageTG"] | None = None
    forward_from: UserORBotTG | None = None
    forward_from_chat: ChatTG | None = None

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
            caption_entities=create_list(
                "caption_entities", EntityTG.from_dict
            ),
            photo=data.get("photo"),
            document=data.get("document"),
            location=data.get("location"),
            contact=data.get("contact"),
            reply_markup=data.get("reply_markup"),
            reply_to_message=create_nested(
                "reply_to_message", MessageTG.from_dict
            ),
            forward_from=create_nested("forward_from", UserORBotTG.from_dict),
            forward_from_chat=create_nested(
                "forward_from_chat", ChatTG.from_dict
            ),
        )

    @property
    def is_command(self):
        if self.entities:
            for entity in self.entities:
                if entity.type == "bot_command":
                    return True
        return False

    def to_command(self) -> CommandTG | None:
        for entity in self.entities:
            if entity.type == "bot_command":
                return CommandTG(
                    text=self.text[
                        entity.offset : entity.length + entity.offset
                    ],
                    from_=self.from_,
                    chat=self.chat,
                )
        return None


@dataclass
class CallbackTG(UpdateABC):
    id_: str
    from_: UserORBotTG
    message: MessageTG | None = None
    inline_message_id: str | None = None
    chat_instance: str | None = None
    data: str | None = None
    game_short_name: str | None = None

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
