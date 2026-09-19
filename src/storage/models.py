"""SQLAlchemy ORM models for water meter history and snapshots."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarative class for historical storage models."""


class ReadingModel(Base):
    """Historical meter reading record and associated snapshot telemetry."""

    __tablename__ = "readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    meters_json: Mapped[str] = mapped_column(Text, nullable=False)
    digital_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    analog_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str] = mapped_column(String(500), default="")
    frame_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    frame_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    frame_blob: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    flow_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence_scores_json: Mapped[str | None] = mapped_column(Text, nullable=True)
