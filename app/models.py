"""
app/models.py — SQLAlchemy ORM models for PixelVault (Supabase / PostgreSQL).

ID strategy:
  • accounts, api_keys, sites, images, image_deployments  → UUID (server default gen_random_uuid())
  • prompts, batches                                       → Integer serial (backward-compat with existing data)
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Association table — image ↔ tag  (kept from original schema)
# ---------------------------------------------------------------------------

image_tags = Table(
    "image_tags",
    Base.metadata,
    Column("image_id", UUID(as_uuid=True), ForeignKey("images.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id",   Integer,            ForeignKey("tags.id",   ondelete="CASCADE"), primary_key=True),
)


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------

class Account(Base):
    __tablename__ = "accounts"

    id:                 Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email:              Mapped[str]              = mapped_column(Text, nullable=False, unique=True)
    name:               Mapped[str]              = mapped_column(Text, nullable=False)
    plan:               Mapped[str]              = mapped_column(String(50), nullable=False, default="free")
    role:               Mapped[str]              = mapped_column(String(20), nullable=False, default="user")
    generations_used:   Mapped[int]              = mapped_column(Integer, nullable=False, default=0)
    generations_limit:  Mapped[int]              = mapped_column(Integer, nullable=False, default=3)
    sync_limit:         Mapped[int]              = mapped_column(Integer, nullable=False, default=50)
    stripe_customer_id: Mapped[Optional[str]]    = mapped_column(Text)
    freemius_user_id:   Mapped[Optional[int]]    = mapped_column(Integer, unique=True)
    freemius_plan_id:   Mapped[Optional[str]]    = mapped_column(Text)
    license_key:        Mapped[Optional[str]]    = mapped_column(Text)
    plan_expires_at:    Mapped[Optional[datetime]] = mapped_column(default=None)
    created_at:         Mapped[datetime]         = mapped_column(default=_utcnow)

    api_keys:    Mapped[list["ApiKey"]]          = relationship(back_populates="account", cascade="all, delete-orphan")
    sites:       Mapped[list["Site"]]            = relationship(back_populates="account", cascade="all, delete-orphan")
    batches:     Mapped[list["Batch"]]           = relationship(back_populates="account")
    images:      Mapped[list["Image"]]           = relationship(back_populates="account")
    deployments: Mapped[list["ImageDeployment"]] = relationship(back_populates="account", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# ApiKey
# ---------------------------------------------------------------------------

class ApiKey(Base):
    __tablename__ = "api_keys"

    id:         Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    key_hash:   Mapped[str]           = mapped_column(Text, nullable=False, unique=True)
    name:       Mapped[str]           = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime]      = mapped_column(default=_utcnow)
    last_used:  Mapped[Optional[datetime]] = mapped_column(default=None)

    account: Mapped["Account"]        = relationship(back_populates="api_keys")
    sites:   Mapped[list["Site"]]     = relationship(back_populates="api_key")


# ---------------------------------------------------------------------------
# Site
# ---------------------------------------------------------------------------

class Site(Base):
    __tablename__ = "sites"

    id:                Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id:        Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"))
    name:              Mapped[str]                 = mapped_column(Text, nullable=False)
    url:               Mapped[str]                 = mapped_column(Text, nullable=False)
    api_key_id:        Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("api_keys.id", ondelete="SET NULL"))
    industry:          Mapped[Optional[str]]       = mapped_column(Text)
    business_type:     Mapped[Optional[str]]       = mapped_column(Text)
    location:          Mapped[Optional[str]]       = mapped_column(Text)
    mood_tags:         Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))
    style_prefix:      Mapped[Optional[str]]       = mapped_column(Text)
    negative_keywords: Mapped[Optional[str]]       = mapped_column(Text)
    serve_from:        Mapped[str]                 = mapped_column(String(20), nullable=False, default="cdn")
    created_at:        Mapped[datetime]            = mapped_column(default=_utcnow)

    account:     Mapped[Optional["Account"]]        = relationship(back_populates="sites")
    api_key:     Mapped[Optional["ApiKey"]]          = relationship(back_populates="sites")
    deployments: Mapped[list["ImageDeployment"]] = relationship(back_populates="site", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

class Prompt(Base):
    __tablename__ = "prompts"

    id:          Mapped[int]           = mapped_column(Integer, primary_key=True)
    industry:    Mapped[str]           = mapped_column(String(50), nullable=False, index=True)
    name:        Mapped[str]           = mapped_column(String(200), nullable=False)
    prompt_text: Mapped[str]           = mapped_column(Text, nullable=False)
    use_case:    Mapped[Optional[str]] = mapped_column(String(500))
    ratios:      Mapped[Optional[str]] = mapped_column(String(100))
    created_at:  Mapped[datetime]      = mapped_column(default=_utcnow)

    images:  Mapped[list["Image"]] = relationship(back_populates="prompt")
    batches: Mapped[list["Batch"]] = relationship(back_populates="prompt")

    __table_args__ = (UniqueConstraint("name", name="uq_prompts_name"),)


# ---------------------------------------------------------------------------
# Batch
# ---------------------------------------------------------------------------

class Batch(Base):
    __tablename__ = "batches"

    id:           Mapped[int]                  = mapped_column(Integer, primary_key=True)
    prompt_id:    Mapped[int]                  = mapped_column(ForeignKey("prompts.id", ondelete="RESTRICT"), nullable=False)
    account_id:   Mapped[Optional[uuid.UUID]]  = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"))
    image_count:  Mapped[int]                  = mapped_column(Integer, nullable=False, default=1)
    ratio:        Mapped[str]                  = mapped_column(String(10), nullable=False)
    status:       Mapped[str]                  = mapped_column(String(20), nullable=False, default="pending")
    model_used:   Mapped[Optional[str]]        = mapped_column(Text)
    created_at:   Mapped[datetime]             = mapped_column(default=_utcnow)
    completed_at: Mapped[Optional[datetime]]   = mapped_column(default=None)

    prompt:  Mapped["Prompt"]          = relationship(back_populates="batches")
    account: Mapped[Optional["Account"]] = relationship(back_populates="batches")
    images:  Mapped[list["Image"]]     = relationship(back_populates="batch")


# ---------------------------------------------------------------------------
# Image
# ---------------------------------------------------------------------------

class Image(Base):
    __tablename__ = "images"

    id:               Mapped[uuid.UUID]          = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_name:   Mapped[Optional[str]]      = mapped_column(Text, unique=True)
    filename:         Mapped[str]                = mapped_column(String(300), nullable=False)
    filepath:         Mapped[str]                = mapped_column(String(500), nullable=False)
    storage_key_web:  Mapped[Optional[str]]      = mapped_column(Text)
    cdn_url:          Mapped[Optional[str]]      = mapped_column(Text)
    industry:         Mapped[str]                = mapped_column(String(50), nullable=False, index=True)
    style:            Mapped[str]                = mapped_column(String(50), nullable=False, index=True)
    ratio:            Mapped[str]                = mapped_column(String(10), nullable=False)
    width:            Mapped[Optional[int]]      = mapped_column(Integer)
    height:           Mapped[Optional[int]]      = mapped_column(Integer)
    file_size:        Mapped[Optional[int]]      = mapped_column(Integer)
    prompt_id:        Mapped[int]                = mapped_column(ForeignKey("prompts.id", ondelete="RESTRICT"), nullable=False)
    batch_id:         Mapped[int]                = mapped_column(ForeignKey("batches.id", ondelete="RESTRICT"), nullable=False)
    account_id:       Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"))
    model_used:       Mapped[Optional[str]]      = mapped_column(Text)
    router_reason:    Mapped[Optional[str]]      = mapped_column(Text)
    cost_actual:      Mapped[Optional[float]]    = mapped_column(Float)
    status:           Mapped[str]                = mapped_column(String(20), nullable=False, default="pending")
    quality_score:    Mapped[Optional[float]]    = mapped_column(Float)
    usage_count:      Mapped[int]                = mapped_column(Integer, nullable=False, default=0)
    last_accessed:    Mapped[Optional[datetime]] = mapped_column(default=None)
    is_official:      Mapped[bool]               = mapped_column(Boolean, nullable=False, default=False)
    is_community:     Mapped[bool]               = mapped_column(Boolean, nullable=False, default=False)
    description:      Mapped[Optional[str]]      = mapped_column(Text)
    community_status: Mapped[Optional[str]]      = mapped_column(String(20), default=None)
    community_votes:  Mapped[int]                = mapped_column(Integer, nullable=False, default=0)
    submitted_at:     Mapped[Optional[datetime]] = mapped_column(default=None)
    created_at:       Mapped[datetime]           = mapped_column(default=_utcnow)

    prompt:      Mapped["Prompt"]                        = relationship(back_populates="images")
    batch:       Mapped["Batch"]                         = relationship(back_populates="images")
    account:     Mapped[Optional["Account"]]             = relationship(back_populates="images")
    tags:        Mapped[list["Tag"]]                     = relationship(secondary=image_tags, back_populates="images")
    deployments: Mapped[list["ImageDeployment"]]         = relationship(back_populates="image", cascade="all, delete-orphan")
    votes:       Mapped[list["CommunityVote"]]           = relationship(back_populates="image", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# CommunityVote
# ---------------------------------------------------------------------------

class CommunityVote(Base):
    __tablename__ = "community_votes"

    id:         Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    image_id:   Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), ForeignKey("images.id", ondelete="CASCADE"), nullable=False)
    account_id: Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime]   = mapped_column(default=_utcnow)

    image:   Mapped["Image"]   = relationship(back_populates="votes")
    account: Mapped["Account"] = relationship()

    __table_args__ = (UniqueConstraint("image_id", "account_id", name="uq_community_vote"),)


# ---------------------------------------------------------------------------
# Tag  (unchanged from original)
# ---------------------------------------------------------------------------

class Tag(Base):
    __tablename__ = "tags"

    id:       Mapped[int]           = mapped_column(Integer, primary_key=True)
    name:     Mapped[str]           = mapped_column(String(100), nullable=False, unique=True, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    images:   Mapped[list["Image"]] = relationship(secondary=image_tags, back_populates="tags")


# ---------------------------------------------------------------------------
# ImageDeployment
# ---------------------------------------------------------------------------

class ImageDeployment(Base):
    __tablename__ = "image_deployments"

    id:             Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    image_id:       Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("images.id", ondelete="CASCADE"), nullable=False)
    account_id:     Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"))
    site_id:        Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), nullable=False)
    local_filename: Mapped[Optional[str]]   = mapped_column(Text)
    local_path:     Mapped[Optional[str]]   = mapped_column(Text)
    post_id:        Mapped[Optional[int]]   = mapped_column(Integer)
    post_title:     Mapped[Optional[str]]   = mapped_column(Text)
    post_keywords:  Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))
    serve_from:     Mapped[str]             = mapped_column(String(20), nullable=False, default="cdn")
    inserted_at:    Mapped[datetime]        = mapped_column(default=_utcnow)
    is_active:      Mapped[bool]            = mapped_column(Boolean, nullable=False, default=True)

    image:   Mapped["Image"]   = relationship(back_populates="deployments")
    account: Mapped["Account"] = relationship(back_populates="deployments")
    site:    Mapped["Site"]    = relationship(back_populates="deployments")


# ---------------------------------------------------------------------------
# ApiLog
# ---------------------------------------------------------------------------

class ApiLog(Base):
    __tablename__ = "api_logs"

    id:               Mapped[int]                 = mapped_column(Integer, primary_key=True)
    account_id:       Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"))
    endpoint:         Mapped[str]                 = mapped_column(Text, nullable=False)
    method:           Mapped[str]                 = mapped_column(String(10), nullable=False)
    status_code:      Mapped[Optional[int]]       = mapped_column(Integer)
    response_time_ms: Mapped[Optional[int]]       = mapped_column(Integer)
    ip_address:       Mapped[Optional[str]]       = mapped_column(Text)
    user_agent:       Mapped[Optional[str]]       = mapped_column(Text)
    error_message:    Mapped[Optional[str]]       = mapped_column(Text)
    created_at:       Mapped[datetime]            = mapped_column(default=_utcnow)
