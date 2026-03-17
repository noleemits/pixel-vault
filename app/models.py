from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Text, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

image_tags = Table(
    "image_tags",
    Base.metadata,
    Column("image_id", Integer, ForeignKey("images.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)

class Prompt(Base):
    __tablename__ = "prompts"
    id: Mapped[int] = mapped_column(primary_key=True)
    industry: Mapped[str] = mapped_column(String(50), index=True)
    name: Mapped[str] = mapped_column(String(200))
    prompt_text: Mapped[str] = mapped_column(Text)
    use_case: Mapped[str] = mapped_column(String(500), default="")
    ratios: Mapped[str] = mapped_column(String(100), default="")
    kontext_variations: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    images: Mapped[list["Image"]] = relationship(back_populates="prompt")
    batches: Mapped[list["Batch"]] = relationship(back_populates="prompt")

class Batch(Base):
    __tablename__ = "batches"
    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    prompt_id: Mapped[int] = mapped_column(ForeignKey("prompts.id"))
    image_count: Mapped[int] = mapped_column(Integer, default=4)
    ratio: Mapped[str] = mapped_column(String(10), default="16:9")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(default=None)
    prompt: Mapped["Prompt"] = relationship(back_populates="batches")
    images: Mapped[list["Image"]] = relationship(back_populates="batch")

class Image(Base):
    __tablename__ = "images"
    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(300), unique=True)
    filepath: Mapped[str] = mapped_column(String(500))
    industry: Mapped[str] = mapped_column(String(50), index=True)
    style: Mapped[str] = mapped_column(String(50), index=True)
    ratio: Mapped[str] = mapped_column(String(10))
    prompt_id: Mapped[int] = mapped_column(ForeignKey("prompts.id"))
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    quality_score: Mapped[int | None] = mapped_column(Integer, default=None)
    fal_request_id: Mapped[str | None] = mapped_column(String(200), default=None)
    width: Mapped[int | None] = mapped_column(Integer, default=None)
    height: Mapped[int | None] = mapped_column(Integer, default=None)
    file_size: Mapped[int | None] = mapped_column(Integer, default=None)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    prompt: Mapped["Prompt"] = relationship(back_populates="images")
    batch: Mapped["Batch"] = relationship(back_populates="images")
    tags: Mapped[list["Tag"]] = relationship(secondary=image_tags, back_populates="images")

class Tag(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    images: Mapped[list["Image"]] = relationship(secondary=image_tags, back_populates="tags")
