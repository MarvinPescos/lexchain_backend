from typing import Annotated

from fastapi import Depends

from app.infrastructure.database import DbSession

from .service import BookService


def get_book_service(db: DbSession) -> BookService:
    """Dependency injection (provides BookService with database session)"""
    return BookService(db)


BookServiceDep = Annotated[BookService, Depends(get_book_service)]
