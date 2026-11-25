from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from app.api import history
from app.api.auth import UserInfo, get_current_user
from app.main import app


ADMIN = UserInfo(user_id=1, username='boss',
                 email='boss@example.com', role='admin')
STUDENT = UserInfo(user_id=3, username='student',
                   email='student@example.com', role='student')
SUBMISSION = {'submission_id': 42, 'assignment_title': 'Prog 2 assignment', 'course_name': 'Programming 2', 'submission_type': 'assignment',
              'due_at': datetime(2026, 11, 16, 23, 59), 'submitted_at': datetime(2026, 11, 15, 20, 0), 'points_awarded': 75, }


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def login(user):
    app.dependency_overrides[get_current_user] = lambda: user


def test_history_requires_login(client):
    assert client.get('/history').status_code == 401
    
def test_admin_cannot_use_student_history_endpoint(client, monkeypatch):
    login(ADMIN)
    monkeypatch.setattr(history, 'load_history', lambda *args: pytest.fail('Database should not be queried'))
    assert client.get('/history').status_code == 403


def test_students_can_view_own_history(client, monkeypatch):
    login(STUDENT)
    called = []

    def fake_history(user_id, limit, offset):
        called.append((user_id, limit, offset))
        return 1, [SUBMISSION]
    monkeypatch.setattr(history, 'load_history', fake_history)
    res = client.get('/history')
    assert res.status_code == 200
    body = res.json()
    assert called == [(3, 20, 0)]
    assert body['total'] == 1
    assert body['submissions'][0]['assignment_title'] == 'Prog 2 assignment'
    assert body['submissions'][0]['points_awarded'] == 75
    assert body['submissions'][0]['due_at'].startswith('2026-11-16')


def test_pagination_parameters_passed_to_db(client, monkeypatch):
    login(STUDENT)
    received = []

    def fake_history(user_id, limit, offset):
        received.append((user_id, limit, offset))
        return 41, [SUBMISSION]
    monkeypatch.setattr(history, 'load_history', fake_history)
    body = client.get('/history?limit=10&offset=20').json()
    assert received == [(3, 10, 20)]
    assert (body['total'], body['limit'], body['offset']) == (41, 10, 20)


@pytest.mark.parametrize('params', ['limit=0', 'limit=101', 'offset=-1', 'limit=abc'])
def test_invalid_pagination_rejected(client, monkeypatch, params):
    login(STUDENT)
    monkeypatch.setattr(history, 'load_history', lambda *args: pytest.fail('Database should not be queried'))
    assert client.get(f'/history?{params}').status_code == 422


def test_students_without_submissions(client, monkeypatch):
    login(STUDENT)
    monkeypatch.setattr(history, 'load_history', lambda *args: (0, []))
    res = client.get('/history')
    assert res.status_code == 200
    body = res.json()
    assert body['total'] == 0
    assert body['submissions'] == []


def test_missing_points_is_null(client, monkeypatch):
    login(STUDENT)
    row = {**SUBMISSION, 'points_awarded': None}
    monkeypatch.setattr(history, 'load_history', lambda *args: (1, [row]))
    assert client.get(
        '/history').json()['submissions'][0]['points_awarded'] is None
    


def test_databse_error_returns_503(client, monkeypatch):
    login(STUDENT)

    def broken(*args):
        raise SQLAlchemyError('db is down')
    monkeypatch.setattr(history, 'load_history', broken)
    assert client.get('/history').status_code == 503
