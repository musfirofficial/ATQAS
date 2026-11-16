import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import TextBook
from ..schema.textbook import TextBookCreate


async def create_textbook(
    db: AsyncSession,
    textbook_in: TextBookCreate,
    collection_name: str,
    total_pages: int,
) -> TextBook:
    new_textbook = TextBook(**textbook_in.model_dump)

    db.add(new_textbook)  # Store in memory
    await db.commit()  # Commit to the database
    await db.refresh(new_textbook)  # Refresh to get the new data from the database
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
