
import pytest
from fastapi.testclient import TestClient

import database
from main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_database = tmp_path / "test_retail.db"
    monkeypatch.setattr(
        database, "DATABASE_NAME", str(test_database)
    )

    with TestClient(app) as test_client:
        yield test_client


def test_create_stock_request(client):
    response = client.post(
        "/requests",
        json={
            "item": "Barcode Scanner",
            "quantity": 3,
            "reason": "Replace damaged scanners",
        },
    )

    assert response.status_code == 201
    assert response.json()["item"] == "Barcode Scanner"
    assert response.json()["status"] == "Pending"


def test_reject_invalid_quantity(client):
    response = client.post(
        "/requests",
        json={
            "item": "Laptop",
            "quantity": 0,
            "reason": "Stock replenishment",
        },
    )

    assert response.status_code == 422


def test_request_not_found(client):
    response = client.get("/requests/9999")

    assert response.status_code == 404


def test_approval_and_audit_log(client):
    create_response = client.post(
        "/requests",
        json={
            "item": "Keyboard",
            "quantity": 4,
            "reason": "Replace faulty keyboards",
        },
    )

    request_id = create_response.json()["request_id"]

    approval_response = client.post(
        f"/requests/{request_id}/approve"
    )

    assert approval_response.status_code == 200
    assert approval_response.json()["status"] == "Approved"

    audit_response = client.get(
        f"/requests/{request_id}/audit"
    )

    actions = [
        entry["action"] for entry in audit_response.json()
    ]

    assert "Created" in actions
    assert "Approved" in actions


def test_cannot_approve_twice(client):
    create_response = client.post(
        "/requests",
        json={
            "item": "Monitor",
            "quantity": 2,
            "reason": "Additional workstations",
        },
    )

    request_id = create_response.json()["request_id"]

    first_approval = client.post(
        f"/requests/{request_id}/approve"
    )
    second_approval = client.post(
        f"/requests/{request_id}/approve"
    )

    assert first_approval.status_code == 200
    assert second_approval.status_code == 409
