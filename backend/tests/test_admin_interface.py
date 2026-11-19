from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from app.api import admin
from app.api.auth import UserInfo, get_current_user
from app.main import app

# ---------- setup ----------

STUDENT_USER = UserInfo(user_id=3, username='student_user', email='student@example.com', role='student')
ADMIN_USER = UserInfo(user_id=1, username='admin_user', email='admin@example.com', role='admin')

STATS_ROW = { 'total_users': 5, 'students': 4, 'admins': 1, 'total_submissions': 12,
    'total_points_awarded': Decimal('640'), }


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def log_in_as(user: UserInfo):
    app.dependency_overrides[get_current_user] = lambda: user


def broken_database():
    raise SQLAlchemyError('down')


# ---------- who can see stats ----------

def test_stats_requires_login(client):
    assert client.get('/admin/stats').status_code == 401


def test_student_cannot_see_stats(client, monkeypatch):
    log_in_as(STUDENT_USER)
    monkeypatch.setattr(admin, 'load_stats', lambda: pytest.fail('database should not be touched'))
    assert client.get('/admin/stats').status_code == 403


# ---------- stats numbers ----------

def test_admin_sees_stats(client, monkeypatch):
    log_in_as(ADMIN_USER)
    monkeypatch.setattr(admin, 'load_stats', lambda: STATS_ROW)
    response = client.get('/admin/stats')
    assert response.status_code == 200
    assert response.json() == { 'total_users': 5, 'students': 4, 'admins': 1, 'total_submissions': 12,
        'total_points_awarded': 640, }


def test_empty_app_stats_are_zero(client, monkeypatch):
    log_in_as(ADMIN_USER)
# no point rows means sum gives back null
    monkeypatch.setattr(admin, 'load_stats', lambda: {**STATS_ROW, 'total_submissions': 0, 'total_points_awarded': None})
    body = client.get('/admin/stats').json()
    assert body['total_submissions'] == 0
    assert body['total_points_awarded'] == 0


def test_missing_stats_row_is_all_zero(client, monkeypatch):
    log_in_as(ADMIN_USER)
    monkeypatch.setattr(admin, 'load_stats', lambda: {})
    body = client.get('/admin/stats').json()
    assert set(body.values()) == {0}


def test_stats_database_down(client, monkeypatch):
    log_in_as(ADMIN_USER)
    monkeypatch.setattr(admin, 'load_stats', broken_database)
    response = client.get('/admin/stats')
    assert response.status_code == 503
    assert response.json()['detail'] == 'Database is not available'


# ---------- user list used by the interface ----------

def test_user_list_has_what_the_interface_needs(client, monkeypatch):
    log_in_as(ADMIN_USER)
    rows = [{'user_id': 3, 'username': 'student_user', 'email': 'student@example.com', 'role': 'student', 'total_points': 25}]
    monkeypatch.setattr(admin, 'load_all_users', lambda: rows)
    body = client.get('/admin/users').json()
    assert set(body[0].keys()) == {'user_id', 'username', 'email', 'role', 'total_points'}


def test_user_list_never_sends_password_hash(client, monkeypatch):
    log_in_as(ADMIN_USER)
    rows = [{'user_id': 3, 'username': 'student_user', 'email': 'student@example.com', 'role': 'student',
             'total_points': 25, 'password_hash': 'secret'}]
    monkeypatch.setattr(admin, 'load_all_users', lambda: rows)
    assert 'secret' not in client.get('/admin/users').text
