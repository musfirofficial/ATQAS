from typing import Any
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TextBookBase(BaseModel):
    title: str = Field(
        min_length=2, max_length=255, description="Title of the textbook"
    )
    edition: int | str | None = Field(
        default=None, description="Year or edition of syllabus"
    )
    grade: int | None = Field(default=None, description="Grade of textbook")
    subject: str | None = Field(default=None, description="Subject of textbook")
    medium: str = Field(default="english", description="Language medium")
    path: str | None = Field(default=None, description="Optional source file or path")


class TextBookDatasetCreate(TextBookBase):
    """Single input schema for ingesting an extracted textbook dataset."""
    pages: list[dict] = Field(..., description="Pre-extracted page dicts")

    @model_validator(mode="before")
    @classmethod
    def flatten_metadata(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # If wrapped inside 'metadata', pull fields up to top level
            meta = data.get("metadata")
            if isinstance(meta, dict):
                for k, v in meta.items():
                    if k not in data or data[k] is None:
                        data[k] = v
            # If 'document_name' is provided instead of 'title', map it
            if "title" not in data and "document_name" in data:
                data["title"] = data["document_name"]
            elif "title" not in data and isinstance(meta, dict) and "document_name" in meta:
                data["title"] = meta["document_name"]
        return data


# Backward compatibility alias
TextBookCreate = TextBookDatasetCreate


class TextBookResponse(TextBookBase):
    textbook_id: UUID
    status: str
    total_pages: int
    collection_name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
