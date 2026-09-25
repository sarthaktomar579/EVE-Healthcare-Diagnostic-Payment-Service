from typing import Optional
from sqlalchemy import String, Text, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin


class WebhookEvent(Base, TimestampMixin):
    """
    Idempotency ledger for incoming payment webhooks.
    Ensures that multiple deliveries of the exact same event_id are processed only once.
    """
    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    booking_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(50), default="PROCESSED", nullable=False
    )
    raw_payload: Mapped[str] = mapped_column(Text, nullable=False)
    response_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_webhook_event_id_status", "event_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<WebhookEvent id={self.id} event_id='{self.event_id}' status='{self.status}'>"
