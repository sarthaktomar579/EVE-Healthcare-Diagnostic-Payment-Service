from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient


def create_sample_booking(client: TestClient, auth_headers, centre_id: int, test_id: int) -> int:
    future_time = datetime.now(timezone.utc) + timedelta(days=2)
    resp = client.post(
        "/api/v1/bookings/",
        headers=auth_headers,
        json={
            "centre_id": centre_id,
            "test_id": test_id,
            "appointment_datetime": future_time.isoformat(),
        },
    )
    return resp.json()["id"]


def test_simulated_payment_success(
    client: TestClient, auth_headers, sample_centre, sample_test, sample_centre_test
):
    booking_id = create_sample_booking(client, auth_headers, sample_centre.id, sample_test.id)

    # Test root endpoint POST /payments/ as well as /api/v1/payments/
    response = client.post(
        "/payments/",
        json={
            "booking_id": booking_id,
            "payment_method": "UPI",
            "simulate_status": "SUCCESS",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["payment_status"] == "SUCCESS"
    assert data["booking_status"] == "CONFIRMED"
    assert data["booking_id"] == booking_id
    assert float(data["amount"]) == 450.00
    assert data["transaction_reference"].startswith("TXN-EVE-")

    # Verify booking status has updated to CONFIRMED
    booking_resp = client.get(f"/api/v1/bookings/{booking_id}", headers=auth_headers)
    assert booking_resp.json()["status"] == "CONFIRMED"


def test_simulated_payment_failed(
    client: TestClient, auth_headers, sample_centre, sample_test, sample_centre_test
):
    booking_id = create_sample_booking(client, auth_headers, sample_centre.id, sample_test.id)

    response = client.post(
        "/payments/",
        json={
            "booking_id": booking_id,
            "payment_method": "CREDIT_CARD",
            "simulate_status": "FAILED",
            "failure_reason": "Card limit exceeded",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["payment_status"] == "FAILED"
    assert data["booking_status"] == "FAILED"
    assert data["failure_reason"] == "Card limit exceeded"

    # Verify booking status has updated to FAILED
    booking_resp = client.get(f"/api/v1/bookings/{booking_id}", headers=auth_headers)
    assert booking_resp.json()["status"] == "FAILED"


def test_payment_for_already_confirmed_booking_fails(
    client: TestClient, auth_headers, sample_centre, sample_test, sample_centre_test
):
    booking_id = create_sample_booking(client, auth_headers, sample_centre.id, sample_test.id)

    # First payment succeeds
    client.post(
        "/payments/",
        json={"booking_id": booking_id, "simulate_status": "SUCCESS"},
    )

    # Second payment attempt must be rejected
    second_pmt = client.post(
        "/payments/",
        json={"booking_id": booking_id, "simulate_status": "SUCCESS"},
    )
    assert second_pmt.status_code == 400
    assert "already confirmed" in second_pmt.json()["detail"]


def test_payment_for_nonexistent_booking(client: TestClient):
    response = client.post(
        "/payments/",
        json={"booking_id": 999999, "simulate_status": "SUCCESS"},
    )
    assert response.status_code == 404
