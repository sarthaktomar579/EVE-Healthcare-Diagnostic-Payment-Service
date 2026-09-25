from fastapi.testclient import TestClient


def test_create_diagnostic_centre(client: TestClient):
    response = client.post(
        "/api/v1/centres/",
        json={
            "name": "Apollo Diagnostics - Whitefield",
            "location": "Whitefield, Bengaluru",
            "address": "ITPL Main Road",
            "contact_phone": "+918099887766",
            "contact_email": "whitefield@apollo.test",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Apollo Diagnostics - Whitefield"
    assert data["location"] == "Whitefield, Bengaluru"
    assert "id" in data


def test_list_centres_with_pagination(client: TestClient, sample_centre):
    response = client.get("/api/v1/centres/?page=1&size=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1
    assert data["page"] == 1


def test_get_centre_details_with_tests(client: TestClient, sample_centre, sample_centre_test, sample_test):
    response = client.get(f"/api/v1/centres/{sample_centre.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_centre.id
    assert len(data["available_tests"]) >= 1
    offered_test = data["available_tests"][0]
    assert offered_test["test_id"] == sample_test.id
    assert float(offered_test["price"]) == 450.00


def test_create_diagnostic_test(client: TestClient):
    response = client.post(
        "/api/v1/tests/",
        json={
            "name": "Lipid Profile",
            "code": "LIPID-01",
            "category": "Biochemistry",
            "description": "Cholesterol and triglyceride assessment",
            "preparation_instructions": "12-14 hours fasting required",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["code"] == "LIPID-01"


def test_associate_test_to_centre(client: TestClient, sample_centre, sample_test):
    response = client.post(
        f"/api/v1/centres/{sample_centre.id}/tests",
        json={
            "test_id": sample_test.id,
            "price": "550.00",
            "duration_minutes": 25,
            "is_available": True,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["test_id"] == sample_test.id
    assert float(data["price"]) == 550.00
