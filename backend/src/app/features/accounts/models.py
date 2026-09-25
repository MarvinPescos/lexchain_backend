import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base, TimestampMixin
from app.shared.constants import ROLE_LAWYER, ROLE_USER

if TYPE_CHECKING:
    from app.features.books import Book


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(f"role IN ('{ROLE_USER}', '{ROLE_LAWYER}')", name="ck_users_role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supabase_user_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    f_name: Mapped[str] = mapped_column(String(255), nullable=False)
    l_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    role: Mapped[str] = mapped_column(
        String(50), default=ROLE_USER, server_default=ROLE_USER, nullable=False
    )
    avatar: Mapped[str] = mapped_column(
        String(50), default="icon1", server_default="icon1", nullable=False
    )

    # === relationship ===
    books: Mapped[list["Book"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"
