import enum
from sqlalchemy import String, Boolean, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    PATIENT = "PATIENT"
    ADMIN = "ADMIN"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(50), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum", native_enum=False),
        default=UserRole.PATIENT,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships will be linked in subsequent steps for bookings
    bookings: Mapped[list["Booking"]] = relationship(
        "Booking",
        back_populates="patient",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email='{self.email}' role='{self.role}'>"
