import uuid
from typing import TypeVar

from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError

from ..observability.logging_setup import log
from .base import UserOwned
from .base_repository import BaseRepository
from .exceptions import DatabaseError

UserOwnedModel = TypeVar("UserOwnedModel", bound=UserOwned)


class UserScopeRepository(BaseRepository[UserOwnedModel]):
    def _build_conditions(
        self, user_id: uuid.UUID, identifier: uuid.UUID | None = None, **kwargs
    ) -> list:
        conditions = [self.model.user_id == user_id]

        if identifier:
            conditions.append(self.model.id == identifier)

        return conditions

    async def get_one(
        self, user_id: uuid.UUID, identifier: uuid.UUID | None = None, **kwargs
    ) -> UserOwnedModel | None:
        """
        Get a single item owned by this user.

        Args:
            user_id: scope to this user
            identifier: the row's id, when narrowing to one row.
        """
        try:
            conditions = self._build_conditions(
                user_id=user_id,
                identifier=identifier,
                **kwargs,
            )
            result = await self.session.execute(select(self.model).where(and_(*conditions)))

            return result.scalar_one_or_none()

        except SQLAlchemyError as e:
            log.error(
                "database.error",
                model=self.model_name,
                operation="get_one",
                error=str(e),
            )
            raise DatabaseError(f"Failed to get {self.model_name}", original_error=e)

    async def get_many(
        self, user_id: uuid.UUID, limit: int = 100, offset: int = 0, **kwargs
    ) -> list[UserOwnedModel]:
        """Get a page of the items owned by this user."""
        try:
            conditions = self._build_conditions(user_id=user_id, identifier=None, **kwargs)
            result = await self.session.execute(
                select(self.model).where(and_(*conditions)).limit(limit).offset(offset)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            log.error(
                "database.error",
                model=self.model_name,
                operation="get_many",
                error=str(e),
            )
            raise DatabaseError(f"Failed to list {self.model_name}", original_error=e)
