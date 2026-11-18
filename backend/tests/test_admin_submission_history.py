from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.api import admin
from app.api.auth import UserInfo, get_current_user
from app.main import app

ADMIN = UserInfo(user_id=1, username='boss', email='boss@example.com', role='admin')
STUDENT = UserInfo(user_id=3, username='student', email='student@example.com', role='student')

SUBMISSION = {
    'submission_id': 42,
    'assignment_title': 'Chapter 3 homework',
    'course_name': 'Mathematics',
    'submission_type': 'assignment',
    'due_at': datetime(2026, 11, 16, 23, 59),
    'submitted_at': datetime(2026, 11, 15, 20, 0),
    'created_at': datetime(2026, 11, 15, 20, 2),
    'canvas_course_id': 1000,
    'canvas_assignment_id': 2000,
    'points_awarded': 75,
}


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def login(user):
    app.dependency_overrides[get_current_user] = lambda: user


def test_history_requires_login(client):
    assert client.get('/admin/users/3/submissions').status_code == 401


def test_students_cannot_view_other_users_history(client, monkeypatch):
    login(STUDENT)
    monkeypatch.setattr(admin, 'load_submission_history', lambda *args: pytest.fail('Database should not be queried'))
    assert client.get('/admin/users/8/submissions').status_code == 403


def test_admin_can_view_history(client, monkeypatch):
    login(ADMIN)
    called = []

    def fake_history(user_id, limit, offset):
        called.append((user_id, limit, offset))
        return 1, [SUBMISSION]

    monkeypatch.setattr(admin, 'load_submission_history', fake_history)
    res = client.get('/admin/users/3/submissions')
    assert res.status_code == 200
    body = res.json()
    assert called == [(3, 20, 0)]
    assert body['total'] == 1
    assert body['user_id'] == 3
    assert body['submissions'][0]['assignment_title'] == 'Chapter 3 homework'
    assert body['submissions'][0]['points_awarded'] == 75
    assert body['submissions'][0]['due_at'].startswith('2026-11-16')
    assert 'password_hash' not in res.text


def test_pagination_parameters_passed_to_db(client, monkeypatch):
    login(ADMIN)
    received = []

    def fake_history(user_id, limit, offset):
        received.append((user_id, limit, offset))
        return 41, [SUBMISSION]

    monkeypatch.setattr(admin, 'load_submission_history', fake_history)
    body = client.get('/admin/users/3/submissions?limit=10&offset=20').json()
    assert received == [(3, 10, 20)]
    assert (body['total'], body['limit'], body['offset']) == (41, 10, 20)


@pytest.mark.parametrize('params', ['limit=0', 'limit=101', 'offset=-1', 'limit=abc'])
def test_invalid_pagination_rejected(client, monkeypatch, params):
    login(ADMIN)
    monkeypatch.setattr(admin, 'load_submission_history', lambda *args: pytest.fail('Database should not be queried'))
    assert client.get(f'/admin/users/3/submissions?{params}').status_code == 422


def test_unknown_user_404(client, monkeypatch):
    login(ADMIN)
    monkeypatch.setattr(admin, 'load_submission_history', lambda *args: None)
    assert client.get('/admin/users/999/submissions').status_code == 404


def test_existing_user_without_submissions(client, monkeypatch):
    login(ADMIN)
    monkeypatch.setattr(admin, 'load_submission_history', lambda *args: (0, []))
    res = client.get('/admin/users/3/submissions')
    assert res.status_code == 200
    assert res.json()['submissions'] == []
    assert res.json()['total'] == 0


def test_missing_points_transaction_is_null(client, monkeypatch):
    login(ADMIN)
    monkeypatch.setattr(admin, 'load_submission_history', lambda *args: (1, [{**SUBMISSION, 'points_awarded': None}]))
    res = client.get('/admin/users/3/submissions')
    assert res.status_code == 200
    assert res.json()['submissions'][0]['points_awarded'] is None


def test_database_error_returns_503(client, monkeypatch):
    login(ADMIN)

    def fail(*args):
        raise SQLAlchemyError('sensitive db error')

    monkeypatch.setattr(admin, 'load_submission_history', fail)
    res = client.get('/admin/users/3/submissions')
    assert res.status_code == 503
    assert 'sensitive' not in res.text


def test_sql_uses_bound_user_id_and_pagination(monkeypatch):
    # Inspect real query usage with a minimal fake engine (no MySQL instance required).
    executed = []

    class Result:
        def __init__(self, kind):
            self.kind = kind

        def first(self):
            return (1,)

        def scalar_one(self):
            return 1

        def mappings(self):
            return self

        def all(self):
            return [SUBMISSION]

    class Connection:
        def execute(self, statement, params=None):
            executed.append((str(statement), params))
            return Result('fake')

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class Engine:
        def connect(self):
            return Connection()

    monkeypatch.setattr(admin, 'get_engine', lambda: Engine())
    total, rows = admin.load_submission_history(3, 20, 40)
    assert (total, len(rows)) == (1, 1)
    sql, params = executed[-1]
    assert 'WHERE s.user_id = :user_id' in sql
    assert 'LIMIT :limit OFFSET :offset' in sql
    assert 'LEFT JOIN point_transactions' in sql
    assert params == {'user_id': 3, 'limit': 20, 'offset': 40}
