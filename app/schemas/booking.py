from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from app.models.booking import BookingStatus


class BookingCreate(BaseModel):
    centre_id: int = Field(gt=0, description="ID of diagnostic centre")
    test_id: int = Field(gt=0, description="ID of diagnostic test to book")
    appointment_datetime: datetime = Field(
        description="Desired appointment date and time (must be in the future)"
    )
    notes: Optional[str] = Field(default=None, max_length=500, description="Optional patient notes / symptoms")

    @field_validator("appointment_datetime")
    @classmethod
    def validate_future_date(cls, v: datetime) -> datetime:
        now = datetime.now(timezone.utc)
        # Ensure v has timezone or compare as UTC
        check_time = v if v.tzinfo else v.replace(tzinfo=timezone.utc)
        if check_time <= now:
            raise ValueError("Appointment datetime must be in the future")
        return v


class BookingCancel(BaseModel):
    reason: Optional[str] = Field(
        default="Cancelled by user",
        max_length=255,
        description="Reason for cancellation",
    )


class BookingOut(BaseModel):
    id: int
    booking_reference: str
    patient_id: int
    patient_name: str
    patient_email: str
    centre_id: int
    centre_name: str
    centre_location: str
    test_id: int
    test_name: str
    test_code: str
    appointment_datetime: datetime
    amount: Decimal
    status: BookingStatus
    notes: Optional[str] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BookingListOut(BaseModel):
    id: int
    booking_reference: str
    centre_name: str
    centre_location: str
    test_name: str
    appointment_datetime: datetime
    amount: Decimal
    status: BookingStatus
    created_at: datetime

    class Config:
        from_attributes = True
