
import jwt
from fastapi.testclient import TestClient

import app.api.auth as auth
from app.main import app

client = TestClient(app)


def test_me_requires_login():
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_me_rejects_invalid_token(monkeypatch):
    def invalid_token(token):
        raise jwt.InvalidTokenError()

    monkeypatch.setattr(
        auth, "read_user_id", invalid_token
    )

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": "Bearer invalid-token"
        },
    )

    assert response.status_code == 401


def test_login_rejects_unknown_user(monkeypatch):
    monkeypatch.setattr(
        auth, "find_user_for_login",
        lambda identifier: None,
    )

    response = client.post(
        "/auth/login",
        json={
            "identifier": "unknown_user",
            "password": "WrongPassword123",
        },
    )

    assert response.status_code == 401


def test_login_rejects_wrong_password(monkeypatch):
    monkeypatch.setattr(
        auth,
        "find_user_for_login",
        lambda identifier: {
            "user_id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "password_hash": "test-hash",
            "role": "student",
        },
    )

    monkeypatch.setattr(
        auth, "password_matches",
        lambda password, password_hash: False,
    )

    response = client.post(
        "/auth/login",
        json={
            "identifier": "testuser",
            "password": "WrongPassword123",
        },
    )

    assert response.status_code == 401


def test_login_success(monkeypatch):
    monkeypatch.setattr(
        auth,
        "find_user_for_login",
        lambda identifier: {
            "user_id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "password_hash": "test-hash",
            "role": "student",
        },
    )

    monkeypatch.setattr(
        auth, "password_matches",
        lambda password, password_hash: True,
    )

    monkeypatch.setattr(
        auth, "create_access_token",
        lambda user_id, role: "test-token",
    )

    response = client.post(
        "/auth/login",
        json={
            "identifier": "testuser",
            "password": "ValidPassword123",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["access_token"] == "test-token"
    assert data["user"]["username"] == "testuser"
    assert data["user"]["role"] == "student"
