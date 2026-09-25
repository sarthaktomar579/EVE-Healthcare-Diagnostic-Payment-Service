import uuid
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.payment import Payment
from app.models.webhook_event import WebhookEvent
from app.models.booking import Booking


def test_payment_webhook_success_and_idempotency(
    client: TestClient, db_session: Session, auth_headers, sample_centre, sample_test, sample_centre_test
):
    # 1. Create a booking in PENDING status
    future_time = datetime.now(timezone.utc) + timedelta(days=3)
    create_resp = client.post(
        "/api/v1/bookings/",
        headers=auth_headers,
        json={
            "centre_id": sample_centre.id,
            "test_id": sample_test.id,
            "appointment_datetime": future_time.isoformat(),
        },
    )
    booking_id = create_resp.json()["id"]

    event_id = f"evt_webhook_test_{uuid.uuid4().hex[:10]}"
    payload = {
        "event_id": event_id,
        "event_type": "payment.succeeded",
        "booking_id": booking_id,
        "transaction_reference": f"TXN-WEBHOOK-{uuid.uuid4().hex[:8]}",
        "amount": "450.00",
        "status": "SUCCESS",
    }

    # First webhook dispatch: should process normally
    resp1 = client.post("/payments/webhook/", json=payload)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["status"] == "processed"
    assert data1["is_duplicate"] is False
    assert data1["booking_status"] == "CONFIRMED"

    # Second webhook dispatch with exact same event_id: IDEMPOTENT replay
    resp2 = client.post("/payments/webhook/", json=payload)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["status"] == "already_processed"
    assert data2["is_duplicate"] is True
    assert data2["booking_status"] == "CONFIRMED"

    # Third webhook dispatch: still IDEMPOTENT replay
    resp3 = client.post("/payments/webhook/", json=payload)
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert data3["is_duplicate"] is True

    # Critical Database Integrity Verifications:
    # 1. Verify only 1 payment was created for this transaction
    payments_count = (
        db_session.query(Payment)
        .filter(Payment.transaction_reference == payload["transaction_reference"])
        .count()
    )
    assert payments_count == 1, "Duplicate payment created despite idempotent webhook!"

    # 2. Verify only 1 webhook ledger record was persisted
    events_count = (
        db_session.query(WebhookEvent)
        .filter(WebhookEvent.event_id == event_id)
        .count()
    )
    assert events_count == 1, "Duplicate webhook events recorded!"

    # 3. Verify booking status remained CONFIRMED and uncorrupted
    booking = db_session.query(Booking).filter(Booking.id == booking_id).first()
    assert booking.status.value == "CONFIRMED"


def test_payment_webhook_failed_status(
    client: TestClient, db_session: Session, auth_headers, sample_centre, sample_test, sample_centre_test
):
    future_time = datetime.now(timezone.utc) + timedelta(days=3)
    create_resp = client.post(
        "/api/v1/bookings/",
        headers=auth_headers,
        json={
            "centre_id": sample_centre.id,
            "test_id": sample_test.id,
            "appointment_datetime": future_time.isoformat(),
        },
    )
    booking_id = create_resp.json()["id"]

    event_id = f"evt_webhook_fail_{uuid.uuid4().hex[:10]}"
    payload = {
        "event_id": event_id,
        "event_type": "payment.failed",
        "booking_id": booking_id,
        "transaction_reference": f"TXN-FAIL-{uuid.uuid4().hex[:8]}",
        "amount": "450.00",
        "status": "FAILED",
        "failure_reason": "Bank network timeout",
    }

    resp = client.post("/payments/webhook/", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "processed"
    assert resp.json()["booking_status"] == "FAILED"

    booking = db_session.query(Booking).filter(Booking.id == booking_id).first()
    assert booking.status.value == "FAILED"


def test_payment_webhook_invalid_booking_id(client: TestClient):
    payload = {
        "event_id": f"evt_notfound_{uuid.uuid4().hex[:10]}",
        "event_type": "payment.succeeded",
        "booking_id": 999999,
        "status": "SUCCESS",
    }
    resp = client.post("/payments/webhook/", json=payload)
    assert resp.status_code == 404
