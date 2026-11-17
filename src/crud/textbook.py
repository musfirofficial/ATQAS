import uuid
from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import TextBook
from src.schema.textbook import TextBokCreate


async def create_textbook_record(
    db: AsyncSession, textbook_in: TextBokCreate
) -> TextBook:
    """Inserts a new textbook record into the SQL database."""
    new_textbook = TextBook(**textbook_in.model_dump())
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


async def delete_textbook_by_id(db: AsyncSession, textbook_id: uuid.UUID) -> None:
    stmt = delete(TextBook).where(TextBook.id == textbook_id)
    await db.execute(stmt)
