import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import TextBook, TextBookStatus


async def create_textbook_record(
    db: AsyncSession,
    title: str,
    total_pages: int,
    collection_name: str,
    grade: int | None = None,
    subject: str | None = None,
    medium: str = "english",
    edition: str | None = None,
    path: str | None = None,
    status: TextBookStatus = TextBookStatus.READY,
) -> TextBook:
    """Inserts a new textbook record into the SQL database."""
    new_textbook = TextBook(
        title=title,
        total_pages=total_pages,
        collection_name=collection_name,
        grade=grade,
        subject=subject,
        medium=medium,
        edition=str(edition) if edition is not None else None,
        path=path,
        status=status,
    )
    db.add(new_textbook)
    await db.commit()
    await db.refresh(new_textbook)
    return new_textbook


async def get_textbooks(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[TextBook]:
    """Retrieve all textbooks registered in the database."""
    stmt = select(TextBook).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_textbook_by_id(
    db: AsyncSession,
    textbook_id: uuid.UUID,
) -> TextBook | None:
    """Retrieve a single textbook by its unique UUID."""
    stmt = select(TextBook).where(TextBook.textbook_id == textbook_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_textbook_by_title(
    db: AsyncSession,
    title: str,
) -> TextBook | None:
    """Retrieve a textbook by its title."""
    stmt = select(TextBook).where(TextBook.title == title)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
