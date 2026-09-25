from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import TimestampMixin, UserOwned

from .constants import BOOK_OPEN

if TYPE_CHECKING:
    from app.features.accounts import User

UQ_BOOK_NUMBER = "uq_book_user_number_year"
UQ_BOOK_ONE_OPEN = "uq_book_one_open_per_year"


class Book(UserOwned, TimestampMixin):
    __tablename__ = "books"
    __table_args__ = (
        UniqueConstraint("user_id", "book_number", "series_year", name=UQ_BOOK_NUMBER),
        Index(
            UQ_BOOK_ONE_OPEN,
            "user_id",
            "series_year",
            unique=True,
            postgresql_where=text(f"status = '{BOOK_OPEN}'"),
        ),
    )

    book_number: Mapped[int] = mapped_column(Integer, nullable=False)
    series_year: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=BOOK_OPEN, server_default=BOOK_OPEN
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # === relationship ===
    user: Mapped["User"] = relationship(back_populates="books")
