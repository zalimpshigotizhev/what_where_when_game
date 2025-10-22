from sqlalchemy import Integer, func, select

from app.base.base_accessor import BaseAccessor
from app.bot.game.models import PlayerModel, RoundModel
from app.bot.user.models import UserModel


class UserAccessor(BaseAccessor):
    async def get_or_create(self, username_tg: str, id_tg: int) -> UserModel:
        """Создает или возвращает User.
        Есть ли уже такой user проверяется через
        tg_id, потому что он не меняется у пользователя.

        ТАКЖЕ ПРОВЕРЯЕТ ПОМЕНЯЛИСЬ ЛИ ДАННЫЕ username_tg
        В НАШЕЙ БД И У ПОЛЬЗОВАТЕЛЯ. ОБНОВЛЯЕТ ДАННЫЕ.

        :param username_tg: Telegram username
        :param id_tg: Telegram id
        :return: UserModel
        """
        async with await self.app.database.get_session() as session:
            stmt = select(UserModel).filter_by(id_tg=id_tg)
            result = await session.execute(stmt)
            instance: UserModel = result.scalars().one_or_none()

            if instance is not None:
                if instance.username_tg != username_tg:
                    instance.username_tg = username_tg
                    await session.commit()
                return instance

            new_user = UserModel(username_tg=username_tg, id_tg=id_tg)
            session.add(new_user)
            await session.commit()
            return new_user

    async def get_player_stats_by_username(self, username_tg: str) -> dict:
        """Возвращает полную статистику игрока по username

        :param username_tg: username пользователя в Telegram
        :return: Словарь со статистикой
        """
        async with await self.app.database.get_session() as session:
            stmt = (
                select(
                    func.count(RoundModel.id).label("total_answers"),
                    func.sum(
                        func.cast(RoundModel.is_correct_answer, Integer)
                    ).label("correct_answers"),
                )
                .select_from(RoundModel)
                .join(
                    PlayerModel, RoundModel.answer_player_id == PlayerModel.id
                )
                .join(UserModel, PlayerModel.user_id == UserModel.id)
                .where(UserModel.username_tg == username_tg)
            )

            result = await session.execute(stmt)
            stats = result.first()

            total_answers = stats.total_answers or 0
            correct_answers = stats.correct_answers or 0

            return {
                "username": username_tg,
                "total_answers": total_answers,
                "correct_answers": correct_answers,
                "incorrect_answers": total_answers - correct_answers,
            }
