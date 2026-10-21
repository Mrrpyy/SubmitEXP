from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from app.api import submissions
from app.api.auth import UserInfo, get_current_user
from app.main import app

ASSIGNMENT = {
    "canvas_course_id": 900000000001,
    "canvas_assignment_id": 900000000002,
    "assignment_title": "EXP Calculation Test",
    "course_name": "SubmitEXP Testing",
    "due_at": "2026-10-18T23:59:00Z",
    "submitted_at": "2026-10-16T20:00:00Z",
}

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def signed_in():
    app.dependency_overrides[get_current_user] = lambda: UserInfo(
        user_id=3,
        username="test_user",
        email="test@example.com",
        role="student",
    )
    yield
    app.dependency_overrides.clear()

def mock_database(monkeypatch, *, duplicate=False):
    connection = MagicMock()
    engine = MagicMock()
    engine.begin.return_value.__enter__.return_value = connection
    if duplicate:
        connection.execute.side_effect = IntegrityError(
            "INSERT", {}, Exception(1062, "Duplicate entry")
        )
    else:
        inserted = MagicMock()
        inserted.lastrowid = 3

        progress = MagicMock()
        progress.mappings.return_value.one.return_value = {
            "total_points": 15,
            "current_level": 1,
        }

        connection.execute.side_effect = [
            inserted,
            MagicMock(),
            MagicMock(),
            progress,
        ]

    monkeypatch.setattr(
        submissions, "get_engine", lambda: engine
    )
    return connection, engine

def test_assignment_award_updates_all_three_tables(
    client, signed_in, monkeypatch
):
    connection, engine = mock_database(monkeypatch)

    response = client.post(
        "/submissions/assignment", json=ASSIGNMENT
    )
    assert response.status_code == 201
    assert response.json() == {
        "submission_id": 3,
        "points_awarded": 15,
        "total_points": 15,
        "current_level": 1,
    }
    assert engine.begin.call_count == 1
    assert connection.execute.call_count == 4
    calls = connection.execute.call_args_list
    assert calls[0].args[1]["user_id"] == 3
    assert calls[1].args[1]["points"] == 15
    assert calls[2].args[1]["points"] == 15

def test_duplicate_assignment_returns_conflict(
    client, signed_in, monkeypatch
):
    mock_database(monkeypatch, duplicate=True)

    response = client.post(
        "/submissions/assignment", json=ASSIGNMENT
    )
    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Points already recorded for this assignment"
    )

def test_login_required(client):
    response = client.post(
        "/submissions/assignment", json=ASSIGNMENT
    )
    assert response.status_code == 401

def test_invalid_timezone_rejected(
    client, signed_in, monkeypatch
):
    connection, _ = mock_database(monkeypatch)
    payload = {
        **ASSIGNMENT,
        "due_at": "2026-10-18T23:59:00",
    }
    response = client.post(
        "/submissions/assignment", json=payload
    )

    assert response.status_code == 422
    connection.execute.assert_not_called()

def test_late_assignment_awards_zero(
    client, signed_in, monkeypatch
):
    connection, _ = mock_database(monkeypatch)
    payload = {
        **ASSIGNMENT,
        "submitted_at": "2026-10-19T00:00:00Z",
    }
    response = client.post(
        "/submissions/assignment", json=payload
    )
    assert response.status_code == 201
    assert response.json()["points_awarded"] == 0
    assert (
        connection.execute.call_args_list[1].args[1]["points"]
        == 0
    )
