import json
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.booking import Booking, BookingStatus
from app.models.payment import Payment, PaymentStatus, generate_transaction_reference
from app.models.webhook_event import WebhookEvent
from app.schemas.payment import PaymentInitiateRequest, PaymentResponse
from app.schemas.webhook import PaymentWebhookPayload, WebhookResponse
from app.core.logging import logger


class PaymentService:
    @classmethod
    def process_simulated_payment(
        cls,
        db: Session,
        request: PaymentInitiateRequest,
    ) -> PaymentResponse:
        """
        Simulates payment processing for a booking.
        Updates booking status to CONFIRMED on SUCCESS or FAILED on FAILED.
        """
        booking = db.query(Booking).filter(Booking.id == request.booking_id).first()
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Booking with ID {request.booking_id} not found",
            )

        # State validation
        if booking.status == BookingStatus.CONFIRMED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Booking is already confirmed and paid",
            )

        if booking.status == BookingStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot process payment for a cancelled booking",
            )

        # Execute simulated payment outcome
        txn_ref = generate_transaction_reference()
        is_success = request.simulate_status == "SUCCESS"

        payment = Payment(
            transaction_reference=txn_ref,
            booking_id=booking.id,
            amount=booking.amount,
            currency="INR",
            status=PaymentStatus.SUCCESS if is_success else PaymentStatus.FAILED,
            payment_method=request.payment_method.upper(),
            failure_reason=None if is_success else request.failure_reason,
            metadata_json=json.dumps({"simulation": True, "scenario": request.simulate_status}),
        )
        db.add(payment)

        # State transition on booking
        if is_success:
            booking.status = BookingStatus.CONFIRMED
            msg = "Payment processed successfully. Booking confirmed."
        else:
            booking.status = BookingStatus.FAILED
            msg = f"Payment simulation failed: {request.failure_reason}. Booking marked as failed."

        db.commit()
        db.refresh(payment)
        db.refresh(booking)

        logger.info(
            f"Simulated payment {txn_ref} for booking {booking.booking_reference}: "
            f"Outcome={payment.status.value}, BookingStatus={booking.status.value}"
        )

        return PaymentResponse(
            payment_id=payment.id,
            transaction_reference=payment.transaction_reference,
            booking_id=booking.id,
            amount=payment.amount,
            currency=payment.currency,
            payment_status=payment.status,
            booking_status=booking.status,
            payment_method=payment.payment_method,
            failure_reason=payment.failure_reason,
            created_at=payment.created_at,
            message=msg,
        )

    @classmethod
    def process_webhook(
        cls,
        db: Session,
        payload: PaymentWebhookPayload,
    ) -> WebhookResponse:
        """
        Idempotent payment webhook processor.
        Guarantees that multiple deliveries of the exact same event_id:
        1. Do NOT create duplicate payments.
        2. Do NOT create duplicate bookings.
        3. Do NOT corrupt booking or payment state.
        """
        # Step 1: Idempotency check via WebhookEvent ledger
        existing_event = (
            db.query(WebhookEvent)
            .filter(WebhookEvent.event_id == payload.event_id)
            .first()
        )

        if existing_event:
            logger.warning(
                f"Idempotent Webhook replay ignored: Event ID '{payload.event_id}' has already been processed."
            )
            booking = db.query(Booking).filter(Booking.id == payload.booking_id).first()
            return WebhookResponse(
                status="already_processed",
                event_id=payload.event_id,
                booking_id=payload.booking_id,
                booking_status=booking.status.value if booking else "UNKNOWN",
                is_duplicate=True,
                message="Duplicate webhook event received; safely ignored without state change.",
            )

        # Step 2: Validate related booking
        booking = db.query(Booking).filter(Booking.id == payload.booking_id).first()
        if not booking:
            logger.error(f"Webhook processing error: Booking {payload.booking_id} does not exist.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Associated booking ID {payload.booking_id} not found",
            )

        txn_ref = payload.transaction_reference or generate_transaction_reference()
        amount = payload.amount or booking.amount

        # Step 3: Handle state transitions safely
        if payload.status == "SUCCESS":
            if booking.status == BookingStatus.PENDING:
                booking.status = BookingStatus.CONFIRMED
                logger.info(f"Webhook updated booking {booking.id} to CONFIRMED")
            elif booking.status == BookingStatus.CONFIRMED:
                logger.info(f"Booking {booking.id} was already CONFIRMED. Keeping state safe.")

            # Record payment if not already recorded for this transaction reference
            existing_pmt = (
                db.query(Payment)
                .filter(Payment.transaction_reference == txn_ref)
                .first()
            )
            if not existing_pmt:
                pmt = Payment(
                    transaction_reference=txn_ref,
                    booking_id=booking.id,
                    amount=amount,
                    currency="INR",
                    status=PaymentStatus.SUCCESS,
                    payment_method="WEBHOOK_GATEWAY",
                    metadata_json=payload.model_dump_json(),
                )
                db.add(pmt)
            summary_msg = f"Payment succeeded. Booking status is {booking.status.value}."

        else:  # FAILED
            if booking.status == BookingStatus.PENDING:
                booking.status = BookingStatus.FAILED
                logger.info(f"Webhook updated booking {booking.id} to FAILED")

            existing_pmt = (
                db.query(Payment)
                .filter(Payment.transaction_reference == txn_ref)
                .first()
            )
            if not existing_pmt:
                pmt = Payment(
                    transaction_reference=txn_ref,
                    booking_id=booking.id,
                    amount=amount,
                    currency="INR",
                    status=PaymentStatus.FAILED,
                    payment_method="WEBHOOK_GATEWAY",
                    failure_reason=payload.failure_reason or "Reported failed by payment gateway",
                    metadata_json=payload.model_dump_json(),
                )
                db.add(pmt)
            summary_msg = f"Payment failed. Booking status is {booking.status.value}."

        # Step 4: Record event in idempotency ledger
        webhook_log = WebhookEvent(
            event_id=payload.event_id,
            event_type=payload.event_type,
            booking_id=booking.id,
            status="PROCESSED",
            raw_payload=payload.model_dump_json(),
            response_summary=summary_msg,
        )
        db.add(webhook_log)

        # Atomic commit
        db.commit()
        db.refresh(booking)

        logger.info(f"Webhook event {payload.event_id} processed successfully for booking {booking.id}")

        return WebhookResponse(
            status="processed",
            event_id=payload.event_id,
            booking_id=booking.id,
            booking_status=booking.status.value,
            is_duplicate=False,
            message=summary_msg,
        )

    @classmethod
    def get_payment_details(cls, db: Session, payment_id: int) -> Payment:
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payment with ID {payment_id} not found",
            )
        return payment
