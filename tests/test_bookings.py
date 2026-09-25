from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient


def test_create_booking_success(client: TestClient, auth_headers, sample_centre, sample_test, sample_centre_test):
    future_time = datetime.now(timezone.utc) + timedelta(days=2)
    response = client.post(
        "/api/v1/bookings/",
        headers=auth_headers,
        json={
            "centre_id": sample_centre.id,
            "test_id": sample_test.id,
            "appointment_datetime": future_time.isoformat(),
            "notes": "Annual health checkup",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "PENDING"
    assert data["booking_reference"].startswith("EVE-BK-")
    # Verified: price is taken from CentreTest (450.00), not supplied by client
    assert float(data["amount"]) == 450.00
    assert data["centre_id"] == sample_centre.id
    assert data["test_id"] == sample_test.id


def test_create_booking_past_datetime_fails(client: TestClient, auth_headers, sample_centre, sample_test, sample_centre_test):
    past_time = datetime.now(timezone.utc) - timedelta(days=1)
    response = client.post(
        "/api/v1/bookings/",
        headers=auth_headers,
        json={
            "centre_id": sample_centre.id,
            "test_id": sample_test.id,
            "appointment_datetime": past_time.isoformat(),
        },
    )
    assert response.status_code == 422


def test_create_booking_test_not_offered(client: TestClient, auth_headers, sample_centre):
    # Test ID 9999 does not exist / is not offered
    future_time = datetime.now(timezone.utc) + timedelta(days=2)
    response = client.post(
        "/api/v1/bookings/",
        headers=auth_headers,
        json={
            "centre_id": sample_centre.id,
            "test_id": 9999,
            "appointment_datetime": future_time.isoformat(),
        },
    )
    assert response.status_code == 404


def test_user_cannot_access_other_users_booking(
    client: TestClient, auth_headers, other_auth_headers, sample_centre, sample_test, sample_centre_test
):
    future_time = datetime.now(timezone.utc) + timedelta(days=2)
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

    # Other user attempts to get booking
    unauthorized_resp = client.get(f"/api/v1/bookings/{booking_id}", headers=other_auth_headers)
    assert unauthorized_resp.status_code == 403
    assert "Not authorized" in unauthorized_resp.json()["detail"]


def test_cancel_booking_success(
    client: TestClient, auth_headers, sample_centre, sample_test, sample_centre_test
):
    future_time = datetime.now(timezone.utc) + timedelta(days=2)
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

    cancel_resp = client.post(
        f"/api/v1/bookings/{booking_id}/cancel",
        headers=auth_headers,
        json={"reason": "Change of plans"},
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"
    assert cancel_resp.json()["cancellation_reason"] == "Change of plans"

    # Attempting to cancel again should fail
    second_cancel = client.post(
        f"/api/v1/bookings/{booking_id}/cancel",
        headers=auth_headers,
        json={"reason": "Cancel again"},
    )
    assert second_cancel.status_code == 400
    assert "already cancelled" in second_cancel.json()["detail"]
