from datetime import datetime
from decimal import Decimal
from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict
from app.models.payment import PaymentStatus
from app.models.booking import BookingStatus


class PaymentInitiateRequest(BaseModel):
    booking_id: int = Field(gt=0, description="Booking ID to process payment for")
    payment_method: str = Field(default="UPI", description="Simulated method (e.g. UPI, CARD, NETBANKING)")
    simulate_status: Literal["SUCCESS", "FAILED"] = Field(
        default="SUCCESS",
        description="Scenario to simulate: SUCCESS completes booking, FAILED marks booking as failed",
    )
    failure_reason: Optional[str] = Field(
        default="Insufficient funds or bank decline (simulated)",
        description="Optional failure reason message if simulate_status is FAILED",
    )


class PaymentResponse(BaseModel):
    payment_id: int
    transaction_reference: str
    booking_id: int
    amount: Decimal
    currency: str
    payment_status: PaymentStatus
    booking_status: BookingStatus
    payment_method: str
    failure_reason: Optional[str] = None
    created_at: datetime
    message: str

    model_config = ConfigDict(from_attributes=True)


class PaymentDetailOut(BaseModel):
    id: int
    transaction_reference: str
    booking_id: int
    amount: Decimal
    currency: str
    status: PaymentStatus
    payment_method: str
    failure_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
