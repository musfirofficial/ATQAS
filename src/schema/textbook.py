from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.db.models import TextBookStatus


class TextBookBase(BaseModel):
    status: TextBookStatus = Field(
        default=TextBookStatus.READY, description="Embedding status of textbook"
    )
    title: str = Field(
        min_length=2, max_length=255, description="Title of the textbook"
    )
    grade: int | None = Field(default=None, description="Grade of textbook")
    subject: str | None = Field(default=None, description="Subject of textbook")
    medium: str = Field(default="english", description="Language medium")
    edition: int | str | None = Field(
        default=None, description="Year or edition of syllabus"
    )


class TextBokCreate(TextBookBase):
    pass


class TextBookResponse(TextBookBase):
    textbook_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
