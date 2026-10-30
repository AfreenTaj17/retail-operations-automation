import os

# Test-only JWT secret. Never use this secret in production.
os.environ["JWT_SECRET_KEY"] = "pytest-only-secret-key-do-not-use-in-production"

import pytest
from fastapi.testclient import TestClient

import database
from main import app
from security import hash_password


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_database = tmp_path / "test_retail.db"

    monkeypatch.setattr(
        database, "DATABASE_NAME", str(test_database)
    )

    with TestClient(app) as test_client:
        # Create an employee account through the registration API.
        registration = test_client.post(
            "/register",
            json={
                "username": "test_employee",
                "password": "EmployeePass123"
            },
        )
        assert registration.status_code == 201

        # Create a manager account directly for testing.
        database.create_user(
            username="test_manager",
            password_hash=hash_password("ManagerPass123"),
            role="manager",
        )

        yield test_client


@pytest.fixture
def employee_headers(client):
    response = client.post(
        "/login",
        json={
            "username": "test_employee",
            "password": "EmployeePass123",
        },
    )
    assert response.status_code == 200

    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def manager_headers(client):
    response = client.post(
        "/login",
        json={
            "username": "test_manager",
            "password": "ManagerPass123",
        },
    )
    assert response.status_code == 200

    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_request(client, headers, item="Laptop"):
    return client.post(
        "/requests",
        headers=headers,
        json={
            "item": item,
            "quantity": 3,
            "reason": "Stock replenishment",
        },
    )


def test_employee_login(client):
    response = client.post(
        "/login",
        json={
            "username": "test_employee",
            "password": "EmployeePass123",
        },
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


def test_invalid_login(client):
    response = client.post(
        "/login",
        json={
            "username": "test_employee",
            "password": "WrongPassword123",
        },
    )

    assert response.status_code == 401


def test_get_current_user(client, employee_headers):
    response = client.get(
        "/me", headers=employee_headers
    )

    assert response.status_code == 200
    assert response.json()["username"] == "test_employee"
    assert response.json()["role"] == "employee"


def test_request_without_authentication_is_rejected(client):
    response = client.get("/requests")

    assert response.status_code == 401


def test_create_stock_request(client, employee_headers):
    response = create_request(
        client, employee_headers, "Barcode Scanner"
    )

    assert response.status_code == 201
    assert response.json()["item"] == "Barcode Scanner"
    assert response.json()["status"] == "Pending"


def test_reject_invalid_quantity(client, employee_headers):
    response = client.post(
        "/requests",
        headers=employee_headers,
        json={
            "item": "Laptop",
            "quantity": 0,
            "reason": "Stock replenishment",
        },
    )

    assert response.status_code == 422


def test_request_not_found(client, employee_headers):
    response = client.get(
        "/requests/9999", headers=employee_headers
    )

    assert response.status_code == 404


def test_employee_cannot_approve_request(
    client, employee_headers
):
    request_id = create_request(
        client, employee_headers
    ).json()["request_id"]

    response = client.post(
        f"/requests/{request_id}/approve",
        headers=employee_headers,
    )

    assert response.status_code == 403


def test_manager_can_approve_and_audit(
    client, employee_headers, manager_headers
):
    request_id = create_request(
        client, employee_headers, "Keyboard"
    ).json()["request_id"]

    approval = client.post(
        f"/requests/{request_id}/approve",
        headers=manager_headers,
    )

    assert approval.status_code == 200
    assert approval.json()["status"] == "Approved"

    audit = client.get(
        f"/requests/{request_id}/audit",
        headers=employee_headers,
    )

    assert audit.status_code == 200

    actions = [
        entry["action"] for entry in audit.json()
    ]

    assert "Created" in actions
    assert "Approved" in actions


def test_cannot_approve_twice(
    client, employee_headers, manager_headers
):
    request_id = create_request(
        client, employee_headers
    ).json()["request_id"]

    first = client.post(
        f"/requests/{request_id}/approve",
        headers=manager_headers,
    )

    second = client.post(
        f"/requests/{request_id}/approve",
        headers=manager_headers,
    )

    assert first.status_code == 200
    assert second.status_code == 409


def test_manager_can_reject_request(
    client, employee_headers, manager_headers
):
    request_id = create_request(
        client, employee_headers, "Printer"
    ).json()["request_id"]

    response = client.post(
        f"/requests/{request_id}/reject",
        headers=manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Rejected"


def test_cannot_reject_approved_request(
    client, employee_headers, manager_headers
):
    request_id = create_request(
        client, employee_headers, "Tablet"
    ).json()["request_id"]

    approval = client.post(
        f"/requests/{request_id}/approve",
        headers=manager_headers,
    )

    rejection = client.post(
        f"/requests/{request_id}/reject",
        headers=manager_headers,
    )

    assert approval.status_code == 200
    assert rejection.status_code == 409