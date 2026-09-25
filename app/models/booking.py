import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import (
    String,
    DateTime,
    Numeric,
    ForeignKey,
    Enum,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class BookingStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


def generate_booking_reference() -> str:
    """Generates an alphanumeric reference like EVE-BK-A1B2C3D4"""
    return f"EVE-BK-{uuid.uuid4().hex[:8].upper()}"


class Booking(Base, TimestampMixin):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    booking_reference: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, default=generate_booking_reference, nullable=False
    )
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    centre_id: Mapped[int] = mapped_column(
        ForeignKey("diagnostic_centres.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    test_id: Mapped[int] = mapped_column(
        ForeignKey("diagnostic_tests.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    appointment_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, name="booking_status_enum", native_enum=False),
        default=BookingStatus.PENDING,
        index=True,
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    patient: Mapped["User"] = relationship("User", back_populates="bookings", lazy="joined")
    centre: Mapped["DiagnosticCentre"] = relationship("DiagnosticCentre", back_populates="bookings", lazy="joined")
    test: Mapped["DiagnosticTest"] = relationship("DiagnosticTest", back_populates="bookings", lazy="joined")
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="booking", lazy="select")

    def __repr__(self) -> str:
        return f"<Booking id={self.id} ref='{self.booking_reference}' status='{self.status}'>"
