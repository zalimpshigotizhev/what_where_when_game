from sqlalchemy import select

from app.base.base_accessor import BaseAccessor
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
