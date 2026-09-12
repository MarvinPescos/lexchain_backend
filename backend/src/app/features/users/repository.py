from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import BaseRepository

from .models import User


# TODO Switch to based or make a custom repo for it
class UserRepository(BaseRepository[User]):
    """Repository pattern for user data access"""

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    # ======Custom Methods======

    async def get_by_supabase_id(self, supabase_user_id: str) -> User | None:
        """Get user by supabase user id"""

        result = await self.session.execute(
            select(User).where(User.supabase_user_id == supabase_user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def count_by_role(self, role: str) -> int:
        """Count users by role."""
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count()).select_from(self.model).where(self.model.role == role)
        )
        return result.scalar() or 0

    # AdminService.set_user_active. count_by_role counts deactivated accounts
    async def count_active_by_role(self, role: str) -> int:
        """Count active users holding `role`."""
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count())
            .select_from(self.model)
            .where(self.model.role == role, self.model.is_active.is_(True))
        )
        return result.scalar() or 0

    async def sync_from_supabase(
        self, supabase_user_id: str, email: str, **additional_data
    ) -> User:
        user = await self.get_by_supabase_id(supabase_user_id)
        if user:
            return await self.update(user, email=email, **additional_data)
        return await self.create(
            supabase_user_id=supabase_user_id,
            email=email,
            role="user",
            **additional_data,
        )
