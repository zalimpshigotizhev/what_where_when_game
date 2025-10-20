import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.quiz.models import AnswerModel, QuestionModel, ThemeModel


@pytest.fixture
def id_tg():
    return 123


@pytest.fixture
def username_tg():
    return "courvuisier"


@pytest.fixture
def chat_id():
    return 1


@pytest.fixture
def session_id():
    return 1


@pytest.fixture
async def active_game_session(
    store,
    session_id,
    chat_id,
):
    from app.bot.game.models import StatusSession

    return await store.game_session.create_session(
        chat_id=chat_id, status=StatusSession.PROCESSING
    )


@pytest.fixture
async def active_player(
    active_game_session,
    store,
    db_sessionmaker,
    id_tg,
    username_tg,
):
    return await store.players.create_player(
        session_id=active_game_session.id,
        id_tg=id_tg,
        username_tg=username_tg,
        is_active=True,
        is_captain=True,
        is_ready=False,
    )


@pytest.fixture
async def is_active_players(
    active_game_session,
    store,
    db_sessionmaker,
    id_tg,
    username_tg,
):
    players = []
    players.append(
        await store.players.create_player(
            session_id=active_game_session.id,
            id_tg=id_tg,
            username_tg=username_tg,
            is_active=True,
            is_captain=True,
            is_ready=True,
        )
    )
    for _ in range(5):
        players.append(
            await store.players.create_player(
                session_id=active_game_session.id,
                id_tg=id_tg,
                username_tg=username_tg,
                is_active=True,
                is_captain=False,
                is_ready=True,
            )
        )
    return players


@pytest.fixture
async def question(
    store,
):
    from app.quiz.models import AnswerModel

    theme = await store.quizzes.create_theme(title="ThemeTitle")
    return await store.quizzes.create_question(
        title="QuestTilte",
        theme_id=theme.id,
        true_answer=AnswerModel(
            title="AnswerTitle", description="AnswerDescription"
        ),
    )


@pytest.fixture
async def active_round(store, question, active_game_session):
    new_round = await store.rounds.create_round(
        session_id=active_game_session.id,
        question_id=question.id,
        is_active=True,
        answer_player_id=None,
        is_correct_answer=None,
    )
    await store.game_session.set_current_round(
        session_id=active_game_session.id, round_id=new_round.id
    )
    return new_round


@pytest.fixture
async def theme_1(
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> ThemeModel:
    new_theme = ThemeModel(title="web-development")

    async with db_sessionmaker() as session:
        session.add(new_theme)
        await session.commit()

    return new_theme


@pytest.fixture
async def theme_2(
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> ThemeModel:
    new_theme = ThemeModel(title="backend")

    async with db_sessionmaker() as session:
        session.add(new_theme)
        await session.commit()

    return new_theme


@pytest.fixture
async def question_1(
    db_sessionmaker: async_sessionmaker[AsyncSession], theme_1: ThemeModel
) -> QuestionModel:
    question = QuestionModel(
        title="how are you?",
        theme_id=theme_1.id,
        true_answer=AnswerModel(title="well", description="leww"),
    )

    async with db_sessionmaker() as session:
        session.add(question)
        await session.commit()

    return question


@pytest.fixture
async def question_2(db_sessionmaker, theme_1: ThemeModel) -> QuestionModel:
    question = QuestionModel(
        title="are you doing fine?",
        theme_id=theme_1.id,
        true_answer=AnswerModel(title="yep", description="pey"),
    )

    async with db_sessionmaker() as session:
        session.add(question)
        await session.commit()

    return question
