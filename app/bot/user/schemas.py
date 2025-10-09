from marshmallow import Schema, fields


class UserSchema(Schema):
    username_tg = fields.Str()
    id_tg = fields.Int()


class UserId(Schema):
    username_tg = fields.Str(required=True)


class UserInfo(Schema):
    username = fields.Str()
    total_answers = fields.Int()
    correct_answers = fields.Int()
    incorrect_answers = fields.Int()
