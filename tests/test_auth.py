from fastapi.testclient import TestClient


def test_user_signup_success(client: TestClient):
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "newpatient@evehealth.com",
            "password": "Password123!",
            "full_name": "Alice Wonderland",
            "phone_number": "+919988776655",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newpatient@evehealth.com"
    assert data["full_name"] == "Alice Wonderland"
    assert data["role"] == "PATIENT"
    assert "id" in data


def test_user_signup_duplicate_email(client: TestClient, test_user):
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": test_user.email,
            "password": "AnotherPassword123!",
            "full_name": "Duplicate Tester",
        },
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_user_signup_invalid_password_length(client: TestClient):
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "shortpw@evehealth.com",
            "password": "123",
            "full_name": "Short Pw",
        },
    )
    assert response.status_code == 422


def test_user_login_success(client: TestClient, test_user):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "Password123!",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == test_user.email


def test_user_login_invalid_password(client: TestClient, test_user):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "WrongPassword!",
        },
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_get_current_user_profile(client: TestClient, auth_headers, test_user):
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["id"] == test_user.id


def test_get_current_user_unauthorized(client: TestClient):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
