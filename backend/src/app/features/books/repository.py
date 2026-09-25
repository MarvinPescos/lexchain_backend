import uuid

from sqlalchemy import exists, func, select

from app.infrastructure.database import UserScopeRepository

from .constants import BOOK_OPEN
from .models import Book


class BookRepository(UserScopeRepository[Book]):
    """Repository pattern for Book"""

    def __init__(self, session):
        super().__init__(Book, session)

    # === Custom methods ===

    async def list_for_user(
        self, user_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> list[Book]:
        """Books owned by this user, newest series first."""
        stmt = (
            select(Book)
            .where(Book.user_id == user_id)
            .order_by(Book.series_year.desc(), Book.book_number.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_one_for_update(self, user_id: uuid.UUID, book_id: uuid.UUID) -> Book | None:
        """Fetch an owned book and hold a row lock until the transaction ends."""
        stmt = select(Book).where(Book.user_id == user_id, Book.id == book_id).with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def has_documents(self, book_id: uuid.UUID) -> bool:
        """Whether any document, in any version, is filed in this book."""
        from app.features.documents.models import Document

        result = await self.session.execute(select(exists().where(Document.book_id == book_id)))
        return bool(result.scalar())

    async def get_by_number_and_year(
        self, user_id: uuid.UUID, book_number: int, series_year: int
    ) -> Book | None:
        """Find a book by number and year scoped to the user."""
        stmt = select(Book).where(
            Book.user_id == user_id,
            Book.book_number == book_number,
            Book.series_year == series_year,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_open_book_for_year(self, user_id: uuid.UUID, series_year: int) -> Book | None:
        """The OPEN book for a year, if any (there is at most one)."""
        stmt = select(Book).where(
            Book.user_id == user_id,
            Book.series_year == series_year,
            Book.status == BOOK_OPEN,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def register_stats(
        self, book_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, tuple[int, int | None, int | None]]:
        """(entry_count, last_doc_no, last_page_no) per book, in one query."""
        from app.features.documents.models import Document

        if not book_ids:
            return {}

        result = await self.session.execute(
            select(
                Document.book_id,
                func.count(),
                func.max(Document.doc_no),
                func.max(Document.page_no),
            )
            .where(Document.book_id.in_(book_ids), Document.is_latest)
            .group_by(Document.book_id)
        )
        return {row[0]: (row[1], row[2], row[3]) for row in result.all()}

    async def is_doc_no_taken(self, book_id: uuid.UUID, doc_no: int) -> bool:
        from app.features.documents.models import Document

        result = await self.session.execute(
            select(
                exists().where(
                    Document.book_id == book_id,
                    Document.doc_no == doc_no,
                    Document.is_latest,
                )
            )
        )
        return bool(result.scalar())

    async def count_on_page(self, book_id: uuid.UUID, page_no: int) -> int:
        from app.features.documents.models import Document

        result = await self.session.execute(
            select(func.count()).where(
                Document.book_id == book_id,
                Document.page_no == page_no,
                Document.is_latest,
            )
        )
        return result.scalar() or 0
