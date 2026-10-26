from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api import admin, student, submissions
from app.api.auth import UserInfo, get_current_user
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