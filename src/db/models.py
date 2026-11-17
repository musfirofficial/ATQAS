import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Uuid as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .session import Base

local_tz = datetime.now().astimezone().tzinfo


class MessageRole(str, enum.Enum):
    USER = "user"
    AGENT = "agent"


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    STUDENT = "student"


class TextBookStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    role: Mapped[UserRole] = mapped_column(nullable=False)
    user_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(local_tz)
    )


class TextBook(Base):
    __tablename__ = "textbooks"

    textbook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    status: Mapped[TextBookStatus] = mapped_column(default=TextBookStatus.READY)
    title: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    grade: Mapped[int | None] = mapped_column(Integer, nullable=True)
    subject: Mapped[str | None] = mapped_column(String(100), nullable=True)
    medium: Mapped[str] = mapped_column(String(50), default="english")
    edition: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(local_tz)
    )


class Chats(Base):
    __tablename__ = "chats"

    chat_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(local_tz)
    )

    # relationship
    messages: Mapped[list["Messages"]] = relationship(
        back_populates="chat",
        cascade="all, delete-orphan",
        order_by="Messages.created_at",
    )


class Messages(Base):
    __tablename__ = "messages"

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    chat_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chats.chat_id"), index=True
    )
    role: Mapped[MessageRole] = mapped_column(nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    citations: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(local_tz)
    )

    # relationship
    chat: Mapped["Chats"] = relationship(back_populates="messages")
