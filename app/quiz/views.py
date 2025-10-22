from aiohttp_apispec import querystring_schema, request_schema, response_schema

from app.quiz.models import AnswerModel
from app.quiz.schemes import (
    ListQuestionSchema,
    QuestionSchema,
    ThemeIdSchema,
    ThemeListSchema,
    ThemeSchema,
)
from app.web.app import View
from app.web.middlewares import HTTP_ERROR_CODES
from app.web.utils import error_json_response, json_response


class ThemeAddView(View):
    @request_schema(ThemeSchema)
    @response_schema(ThemeSchema)
    async def post(self):
        title = self.data["title"]
        is_exist = await self.store.quizzes.get_theme_by_title(title)
        if not is_exist:
            theme = await self.store.quizzes.create_theme(title=title)
        else:
            return error_json_response(
                http_status=409, status=HTTP_ERROR_CODES[409]
            )

        return json_response(data=ThemeSchema().dump(theme))


class ThemeListView(View):
    @response_schema(ThemeListSchema)
    async def get(self):
        themes = await self.store.quizzes.list_themes()
        result = [{"id": theme.id, "title": theme.title} for theme in themes]
        return json_response(data={"themes": result})


class QuestionAddView(View):
    @request_schema(QuestionSchema)
    @response_schema(QuestionSchema)
    async def post(self):
        title = self.data["title"]
        theme_id = self.data["theme_id"]
        true_answer = AnswerModel(
            title=self.data["true_answer"]["title"],
            description=self.data["true_answer"]["description"],
        )

        store = self.request.app.store
        is_exists_theme = await store.quizzes.get_theme_by_id(theme_id)
        if not is_exists_theme:
            return error_json_response(
                http_status=404, status=HTTP_ERROR_CODES[404]
            )

        store = self.request.app.store
        is_exists_question = await store.quizzes.get_question_by_title(title)
        if is_exists_question:
            return error_json_response(
                http_status=409, status=HTTP_ERROR_CODES[409]
            )

        question = await self.store.quizzes.create_question(
            title=title, true_answer=true_answer, theme_id=theme_id
        )

        dict_quest = {
            "id": question.id,
            "title": question.title,
            "theme_id": question.theme_id,
            "true_answer": {
                "title": true_answer.title,
                "description": true_answer.description,
            },
        }
        return json_response(data=dict_quest)


class QuestionListView(View):
    @querystring_schema(ThemeIdSchema)
    @response_schema(ListQuestionSchema)
    async def get(self):
        theme_id = self.request.query.get("theme_id")
        if theme_id is not None:
            try:
                theme_id = int(theme_id)
            except ValueError:
                return json_response(
                    status=400, data={"error": "theme_id must be integer"}
                )

        questions = await self.store.quizzes.list_questions(theme_id=theme_id)

        return json_response(
            data={
                "questions": [
                    QuestionSchema().dump(question) for question in questions
                ]
            }
        )
