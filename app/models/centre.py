from typing import List
from sqlalchemy import String, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class DiagnosticCentre(Base, TimestampMixin):
    __tablename__ = "diagnostic_centres"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    location: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=True)
    contact_phone: Mapped[str] = mapped_column(String(50), nullable=True)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    centre_tests: Mapped[List["CentreTest"]] = relationship(
        "CentreTest",
        back_populates="centre",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    bookings: Mapped[List["Booking"]] = relationship(
        "Booking",
        back_populates="centre",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<DiagnosticCentre id={self.id} name='{self.name}' location='{self.location}'>"
