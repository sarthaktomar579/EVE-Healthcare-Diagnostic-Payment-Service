from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Literal
from pydantic import BaseModel, Field


class PaymentWebhookPayload(BaseModel):
    event_id: str = Field(min_length=5, max_length=100, description="Unique event ID / idempotency key")
    event_type: str = Field(default="payment.status_update", description="Event type name")
    booking_id: int = Field(gt=0, description="Related booking ID")
    transaction_reference: Optional[str] = Field(default=None, description="External payment provider reference")
    amount: Optional[Decimal] = Field(default=None, description="Payment amount recorded by provider")
    status: Literal["SUCCESS", "FAILED"] = Field(
        description="Payment outcome reported by the simulated gateway"
    )
    failure_reason: Optional[str] = Field(default=None, description="Reason if payment failed")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event dispatch timestamp",
    )


class WebhookResponse(BaseModel):
    status: str
    event_id: str
    booking_id: Optional[int] = None
    booking_status: Optional[str] = None
    is_duplicate: bool
    message: str
