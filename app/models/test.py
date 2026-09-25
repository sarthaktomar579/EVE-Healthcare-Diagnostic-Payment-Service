from typing import List
from sqlalchemy import String, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class DiagnosticTest(Base, TimestampMixin):
    __tablename__ = "diagnostic_tests"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), index=True, default="General", nullable=False)
    preparation_instructions: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    centre_tests: Mapped[List["CentreTest"]] = relationship(
        "CentreTest",
        back_populates="test",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    bookings: Mapped[List["Booking"]] = relationship(
        "Booking",
        back_populates="test",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<DiagnosticTest id={self.id} code='{self.code}' name='{self.name}'>"
