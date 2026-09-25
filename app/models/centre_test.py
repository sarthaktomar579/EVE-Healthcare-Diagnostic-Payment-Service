from decimal import Decimal
from sqlalchemy import ForeignKey, Numeric, Integer, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class CentreTest(Base, TimestampMixin):
    __tablename__ = "centre_tests"
    __table_args__ = (
        UniqueConstraint("centre_id", "test_id", name="uq_centre_test"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    centre_id: Mapped[int] = mapped_column(
        ForeignKey("diagnostic_centres.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    test_id: Mapped[int] = mapped_column(
        ForeignKey("diagnostic_tests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    centre: Mapped["DiagnosticCentre"] = relationship(
        "DiagnosticCentre",
        back_populates="centre_tests",
    )
    test: Mapped["DiagnosticTest"] = relationship(
        "DiagnosticTest",
        back_populates="centre_tests",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<CentreTest id={self.id} centre_id={self.centre_id} test_id={self.test_id} price={self.price}>"
