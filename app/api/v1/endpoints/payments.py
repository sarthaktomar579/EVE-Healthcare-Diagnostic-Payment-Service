from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.payment import (
    PaymentInitiateRequest,
    PaymentResponse,
    PaymentDetailOut,
)
from app.schemas.webhook import PaymentWebhookPayload, WebhookResponse
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments & Webhooks"])


@router.post(
    "/",
    response_model=PaymentResponse,
    status_code=status.HTTP_200_OK,
    summary="Simulate payment processing",
    description="Simulates a payment attempt for a booking. Can simulate SUCCESS or FAILED outcomes.",
)
def simulate_payment(
    request: PaymentInitiateRequest,
    db: Session = Depends(get_db),
):
    return PaymentService.process_simulated_payment(db=db, request=request)


@router.post(
    "/webhook/",
    response_model=WebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="Idempotent payment webhook endpoint",
    description="Accepts asynchronous payment outcome notifications. Guaranteed idempotent: duplicate events are safely ignored.",
)
def payment_webhook(
    payload: PaymentWebhookPayload,
    db: Session = Depends(get_db),
):
    return PaymentService.process_webhook(db=db, payload=payload)


@router.get(
    "/{payment_id}",
    response_model=PaymentDetailOut,
    summary="Get payment details",
    description="Retrieve payment transaction record by ID.",
)
def get_payment(
    payment_id: int,
    db: Session = Depends(get_db),
):
    payment = PaymentService.get_payment_details(db=db, payment_id=payment_id)
    return PaymentDetailOut.model_validate(payment)
