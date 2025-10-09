from marshmallow import Schema, fields

from app.bot.user.schemas import UserSchema


class StateSchema(Schema):
    current_state = fields.Str()


class ChatIdSchema(Schema):
    chat_id = fields.Int()


class PlayerSchema(Schema):
    is_active = fields.Bool()
    is_ready = fields.Bool()
    is_captain = fields.Bool()
    user_tg = fields.Nested(UserSchema, many=False, attribute="user")


class SessionSchema(Schema):
    id = fields.Int(required=False)
    chat_id = fields.Int(required=False)
    status = fields.Str()
    state = fields.Nested(StateSchema, many=False)
    players = fields.Nested(PlayerSchema, many=True)

    experts_score = fields.Method("get_experts_score")
    bot_score = fields.Method("get_bot_score")

    def get_experts_score(self, obj):
        """Вычисляет счет экспертов на основе правильных ответов"""
        if not obj.rounds:
            return 0
        return sum(
            1 for roundw in obj.rounds if roundw.is_correct_answer is True
        )

    def get_bot_score(self, obj):
        """Вычисляет счет бота на основе неправильных ответов"""
        if not obj.rounds:
            return 0
        return sum(
            1 for roundw in obj.rounds if roundw.is_correct_answer is False
        )


class SessionListSchema(Schema):
    active_sessions = fields.Nested(SessionSchema, many=True)
