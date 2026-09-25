import enum
import uuid
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Numeric, ForeignKey, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


def generate_transaction_reference() -> str:
    """Generates unique payment transaction reference like TXN-EVE-XXXXXXXX"""
    return f"TXN-EVE-{uuid.uuid4().hex[:12].upper()}"


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    transaction_reference: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, default=generate_transaction_reference, nullable=False
    )
    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status_enum", native_enum=False),
        default=PaymentStatus.PENDING,
        index=True,
        nullable=False,
    )
    payment_method: Mapped[str] = mapped_column(String(50), default="SIMULATED", nullable=False)
    failure_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship
    booking: Mapped["Booking"] = relationship("Booking", back_populates="payments")

    def __repr__(self) -> str:
        return f"<Payment id={self.id} ref='{self.transaction_reference}' status='{self.status}'>"
