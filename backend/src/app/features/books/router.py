import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.infrastructure.security import LawyerUser

from .dependencies import BookServiceDep
from .schemas import BookCreateRequest, BookResponse

router = APIRouter(prefix="/books", tags=["Books"])


# ── List ────────────────────────────────────────────────────────────


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="List all books",
    description="Return all books belonging to the authenticated lawyer.",
    responses={
        200: {"description": "List of books"},
        401: {"description": "Not authenticated — missing or invalid bearer token"},
        403: {"description": "Forbidden — only lawyers may access books"},
    },
)
async def get_all_books(
    user: LawyerUser,
    service: BookServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[BookResponse]:
    return await service.get_all_books(user.user_id, limit, offset)


# ── Create ──────────────────────────────────────────────────────────


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Create a book",
    description=(
        "Create a register book. OPEN for the book in current use — at most one "
        "per year. CLOSED to migrate a finished physical book: documents filed "
        "in it must give their Doc. No. and Page No. from the paper register."
    ),
    responses={
        201: {"description": "Book created"},
        400: {
            "description": "Book number already used for that year, or another book for that year is still open"
        },
        401: {"description": "Not authenticated — missing or invalid bearer token"},
        403: {"description": "Forbidden — only lawyers may create books"},
    },
)
async def create_book(
    body: BookCreateRequest,
    user: LawyerUser,
    service: BookServiceDep,
) -> BookResponse:
    return await service.create_book(user.user_id, body)


# ── Get one ─────────────────────────────────────────────────────────


@router.get(
    "/{book_id}",
    status_code=status.HTTP_200_OK,
    summary="Get a book",
    description="Return a single book by ID. Only the owner may access it.",
    responses={
        200: {"description": "Book found"},
        401: {"description": "Not authenticated — missing or invalid bearer token"},
        403: {"description": "Forbidden — only lawyers may access books"},
        404: {"description": "Book not found"},
    },
)
async def get_book(
    book_id: uuid.UUID,
    user: LawyerUser,
    service: BookServiceDep,
) -> BookResponse:
    return await service.get_book(user.user_id, book_id)


@router.post(
    "/{book_id}/close",
    status_code=status.HTTP_200_OK,
    summary="Close a book",
    description=(
        "Mark the register as finished so the next book for its year can be "
        "opened. One-way. Documents can still be filed in a closed book with "
        "explicit Doc. No. and Page No."
    ),
    responses={
        200: {"description": "Book closed"},
        401: {"description": "Not authenticated — missing or invalid bearer token"},
        403: {"description": "Forbidden — only lawyers may close books"},
        404: {"description": "Book not found"},
        409: {"description": "Book is already closed"},
    },
)
async def close_book(
    book_id: uuid.UUID,
    user: LawyerUser,
    service: BookServiceDep,
) -> BookResponse:
    return await service.close_book(user.user_id, book_id)


# ── Delete ──────────────────────────────────────────────────────────


@router.delete(
    "/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a book",
    description=(
        "Delete an empty book. Only the owner may delete, and only while no "
        "document is filed in it — documents, finalized ones especially, are "
        "never removed by deleting their book."
    ),
    responses={
        204: {"description": "Book deleted"},
        401: {"description": "Not authenticated — missing or invalid bearer token"},
        403: {"description": "Forbidden — only lawyers may delete books"},
        404: {"description": "Book not found"},
        409: {"description": "Book still holds documents"},
    },
)
async def delete_book(
    book_id: uuid.UUID,
    user: LawyerUser,
    service: BookServiceDep,
) -> None:
    await service.delete_book(user.user_id, book_id)
