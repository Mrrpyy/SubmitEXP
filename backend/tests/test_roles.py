from unittest.mock import MagicMock

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

import app.api.auth as auth
from app.api import admin, student, submissions
from app.api.auth import UserInfo, get_current_user
from app.core import config
from app.core.tokens import create_access_token
from app.main import app

STUDENT_USER = UserInfo(user_id=3, username='student_user', email='student@example.com', role='student')
ADMIN_USER = UserInfo(user_id=1, username='admin_user', email='admin@example.com', role='admin')

USER_ROWS = [
    {'user_id': 3, 'username': 'student_user', 'email': 'student@example.com', 'role': 'student', 'total_points': 25},
    {'user_id': 1, 'username': 'admin_user', 'email': 'admin@example.com', 'role': 'admin', 'total_points': 0},
]

ASSIGNMENT = {
    'canvas_course_id': 900000000001,
    'canvas_assignment_id': 900000000002,
    'assignment_title': 'Roles Test',
    'due_at': '2026-10-18T23:59:00Z',
    'submitted_at': '2026-10-16T20:00:00Z',
}


@pytest.fixture(autouse=True)
def test_secret(monkeypatch):
    # tokens need a secret, this one is only for tests
    monkeypatch.setattr(config, 'JWT_SECRET', 'test-only-secret-that-is-long-enough-for-hs256')


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# pretends a user is logged in without a real token or database
def log_in_as(user: UserInfo):
    app.dependency_overrides[get_current_user] = lambda: user


# not logged in

def test_admin_users_requires_login(client):
    assert client.get('/admin/users').status_code == 401


def test_student_progress_requires_login(client):
    assert client.get('/student/progress').status_code == 401


# students

def test_student_sees_own_progress(client, monkeypatch):
    log_in_as(STUDENT_USER)
    asked_for = []

    def fake_progress(user_id):
        asked_for.append(user_id)
        return {'total_points': 25, 'current_level': 1, 'submissions_recorded': 2}

    monkeypatch.setattr(student, 'load_progress', fake_progress)
    response = client.get('/student/progress')
    assert response.status_code == 200
    assert response.json() == {
        'username': 'student_user',
        'total_points': 25,
        'current_level': 1,
        'submissions_recorded': 2,
    }
    # only the logged in student's id is looked up
    assert asked_for == [3]


def test_student_cannot_list_users(client, monkeypatch):
    log_in_as(STUDENT_USER)
    monkeypatch.setattr(admin, 'load_all_users', lambda: pytest.fail('database should not be touched'))
    response = client.get('/admin/users')
    assert response.status_code == 403


def test_student_cannot_change_roles(client, monkeypatch):
    log_in_as(STUDENT_USER)
    monkeypatch.setattr(admin, 'save_role', lambda user_id, role: pytest.fail('database should not be touched'))
    response = client.post('/admin/users/3/role', json={'role': 'admin'})
    assert response.status_code == 403


# admins

def test_admin_lists_users(client, monkeypatch):
    log_in_as(ADMIN_USER)
    monkeypatch.setattr(admin, 'load_all_users', lambda: USER_ROWS)
    response = client.get('/admin/users')
    assert response.status_code == 200
    assert [row['username'] for row in response.json()] == ['student_user', 'admin_user']
    assert 'password_hash' not in response.json()[0]


def test_admin_changes_a_role(client, monkeypatch):
    log_in_as(ADMIN_USER)
    saved = []
    monkeypatch.setattr(admin, 'save_role', lambda user_id, role: saved.append((user_id, role)))
    monkeypatch.setattr(admin, 'load_all_users', lambda: USER_ROWS)
    response = client.post('/admin/users/3/role', json={'role': 'admin'})
    assert response.status_code == 200
    assert response.json()['role'] == 'admin'
    assert saved == [(3, 'admin')]


def test_admin_cannot_change_own_role(client, monkeypatch):
    log_in_as(ADMIN_USER)
    monkeypatch.setattr(admin, 'save_role', lambda user_id, role: pytest.fail('database should not be touched'))
    response = client.post('/admin/users/1/role', json={'role': 'student'})
    assert response.status_code == 400


def test_role_change_to_unknown_user_is_404(client, monkeypatch):
    log_in_as(ADMIN_USER)
    monkeypatch.setattr(admin, 'load_all_users', lambda: USER_ROWS)
    monkeypatch.setattr(admin, 'save_role', lambda user_id, role: pytest.fail('database should not be touched'))
    response = client.post('/admin/users/999/role', json={'role': 'admin'})
    assert response.status_code == 404


def test_made_up_role_is_rejected(client, monkeypatch):
    log_in_as(ADMIN_USER)
    monkeypatch.setattr(admin, 'save_role', lambda user_id, role: pytest.fail('database should not be touched'))
    response = client.post('/admin/users/3/role', json={'role': 'superuser'})
    assert response.status_code == 422


def test_admin_cannot_view_student_progress(client):
    log_in_as(ADMIN_USER)
    assert client.get('/student/progress').status_code == 403


def test_admin_cannot_earn_exp(client, monkeypatch):
    log_in_as(ADMIN_USER)
    engine = MagicMock()
    monkeypatch.setattr(submissions, 'get_engine', lambda: engine)
    response = client.post('/submissions/assignment', json=ASSIGNMENT)
    assert response.status_code == 403
    engine.begin.assert_not_called()


# the role comes from the database, not from the token

def test_role_is_read_from_database_not_token(client, monkeypatch):
    # token is fine, but the database says this account is a student
    monkeypatch.setattr(auth, 'read_user_id', lambda token: 3)
    monkeypatch.setattr(
        auth, 'find_user_by_id',
        lambda user_id: {'user_id': 3, 'username': 'student_user', 'email': 'student@example.com', 'role': 'student'},
    )
    monkeypatch.setattr(admin, 'load_all_users', lambda: pytest.fail('database should not be touched'))
    response = client.get('/admin/users', headers={'Authorization': 'Bearer looks-like-an-admin-token'})
    assert response.status_code == 403


def test_demoted_admin_loses_access_right_away(client, monkeypatch):
    # account was admin when the token was made, then got changed to student
    token = create_access_token(1, 'admin')
    monkeypatch.setattr(
        auth, 'find_user_by_id',
        lambda user_id: {'user_id': 1, 'username': 'old_admin', 'email': 'old@example.com', 'role': 'student'},
    )
    response = client.get('/admin/users', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 403


def test_bad_token_on_admin_page_is_401(client, monkeypatch):
    def broken_token(token):
        raise jwt.InvalidTokenError()

    monkeypatch.setattr(auth, 'read_user_id', broken_token)
    response = client.get('/admin/users', headers={'Authorization': 'Bearer not-a-real-token'})
    assert response.status_code == 401


def test_forbidden_message_is_clear(client):
    log_in_as(STUDENT_USER)
    response = client.get('/admin/users')
    assert response.json()['detail'] == 'Your account does not have permission to do this'


# role change request checks

def test_admin_can_demote_another_admin(client, monkeypatch):
    log_in_as(ADMIN_USER)
    other_admin = {'user_id': 7, 'username': 'other_admin', 'email': 'other@example.com', 'role': 'admin', 'total_points': 0}
    saved = []
    monkeypatch.setattr(admin, 'load_all_users', lambda: [other_admin, *USER_ROWS])
    monkeypatch.setattr(admin, 'save_role', lambda user_id, role: saved.append((user_id, role)))
    response = client.post('/admin/users/7/role', json={'role': 'student'})
    assert response.status_code == 200
    assert response.json()['role'] == 'student'
    assert saved == [(7, 'student')]


def test_role_change_needs_a_role(client, monkeypatch):
    log_in_as(ADMIN_USER)
    monkeypatch.setattr(admin, 'save_role', lambda user_id, role: pytest.fail('database should not be touched'))
    response = client.post('/admin/users/3/role', json={})
    assert response.status_code == 422


def test_role_change_rejects_extra_fields(client, monkeypatch):
    log_in_as(ADMIN_USER)
    monkeypatch.setattr(admin, 'save_role', lambda user_id, role: pytest.fail('database should not be touched'))
    response = client.post('/admin/users/3/role', json={'role': 'admin', 'user_id': 1})
    assert response.status_code == 422


def test_role_names_are_case_sensitive(client, monkeypatch):
    log_in_as(ADMIN_USER)
    monkeypatch.setattr(admin, 'save_role', lambda user_id, role: pytest.fail('database should not be touched'))
    response = client.post('/admin/users/3/role', json={'role': 'Admin'})
    assert response.status_code == 422


# database problems give a 503 instead of crashing

def broken_database(*args):
    raise SQLAlchemyError('database is down')


def test_admin_users_database_down(client, monkeypatch):
    log_in_as(ADMIN_USER)
    monkeypatch.setattr(admin, 'load_all_users', broken_database)
    response = client.get('/admin/users')
    assert response.status_code == 503


def test_role_change_database_down(client, monkeypatch):
    log_in_as(ADMIN_USER)
    monkeypatch.setattr(admin, 'load_all_users', lambda: USER_ROWS)
    monkeypatch.setattr(admin, 'save_role', broken_database)
    response = client.post('/admin/users/3/role', json={'role': 'admin'})
    assert response.status_code == 503


def test_student_progress_database_down(client, monkeypatch):
    log_in_as(STUDENT_USER)
    monkeypatch.setattr(student, 'load_progress', broken_database)
    response = client.get('/student/progress')
    assert response.status_code == 503


# new student with no progress row yet

def test_student_with_no_progress_starts_at_zero(client, monkeypatch):
    log_in_as(STUDENT_USER)
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value.execute.return_value.mappings.return_value.first.return_value = None
    monkeypatch.setattr(student, 'get_engine', lambda: engine)
    response = client.get('/student/progress')
    assert response.status_code == 200
    assert response.json()['total_points'] == 0
    assert response.json()['current_level'] == 1
    assert response.json()['submissions_recorded'] == 0


# admin list with no accounts

def test_admin_list_can_be_empty(client, monkeypatch):
    log_in_as(ADMIN_USER)
    monkeypatch.setattr(admin, 'load_all_users', lambda: [])
    response = client.get('/admin/users')
    assert response.status_code == 200
    assert response.json() == []