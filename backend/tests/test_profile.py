from datetime import datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.api import profile
from app.api.auth import UserInfo, get_current_user
from app.main import app

# ---------- setup ----------

STUDENT_USER = UserInfo(user_id=3, username='student_user', email='student@example.com', role='student')
ADMIN_USER = UserInfo(user_id=1, username='admin_user', email='admin@example.com', role='admin')

JOINED = datetime(2026, 9, 15, 12, 0, 0)

STATS_ROW = {
    'total_points': 175,
    'submissions_recorded': 4,
    'early_submissions': 3,
    'best_award': 60,
    'average_award': Decimal('44'),
    'last_submitted_at': datetime(2026, 11, 10, 20, 30, 0),
}


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def log_in_as(user: UserInfo):
    app.dependency_overrides[get_current_user] = lambda: user


def broken_database(*args):
    raise SQLAlchemyError('down')


# ---------- login ----------

def test_profile_requires_login(client):
    assert client.get('/profile').status_code == 401


# ---------- students ----------

def test_student_gets_account_and_stats(client, monkeypatch):
    log_in_as(STUDENT_USER)
    monkeypatch.setattr(profile, 'load_member_since', lambda user_id: JOINED)
    monkeypatch.setattr(profile, 'load_stats', lambda user_id: STATS_ROW)
    body = client.get('/profile').json()
    assert body['username'] == 'student_user'
    assert body['email'] == 'student@example.com'
    assert body['role'] == 'student'
    assert body['member_since'].startswith('2026-09-15')
    assert body['stats']['total_points'] == 175
    assert body['stats']['submissions_recorded'] == 4
    assert body['stats']['early_submissions'] == 3
    assert body['stats']['best_award'] == 60
    assert body['stats']['average_award'] == 44


def test_student_level_matches_level_system(client, monkeypatch):
    log_in_as(STUDENT_USER)
    monkeypatch.setattr(profile, 'load_member_since', lambda user_id: JOINED)
    monkeypatch.setattr(profile, 'load_stats', lambda user_id: STATS_ROW)
    stats = client.get('/profile').json()['stats']
    assert stats['current_level'] == 2
    assert stats['exp_in_level'] == 75
    assert stats['exp_to_next_level'] == 25
    assert stats['progress_percent'] == 75


def test_only_own_profile_is_loaded(client, monkeypatch):
    log_in_as(STUDENT_USER)
    asked_for = []

    def fake_stats(user_id):
        asked_for.append(user_id)
        return STATS_ROW

    monkeypatch.setattr(profile, 'load_member_since', lambda user_id: JOINED)
    monkeypatch.setattr(profile, 'load_stats', fake_stats)
    client.get('/profile')
    assert asked_for == [3]


def test_new_student_starts_at_zero(client, monkeypatch):
    log_in_as(STUDENT_USER)
    # no submissions means mysql returns nulls for max and avg
    empty_row = {
        'total_points': 0,
        'submissions_recorded': 0,
        'early_submissions': None,
        'best_award': None,
        'average_award': None,
        'last_submitted_at': None,
    }
    monkeypatch.setattr(profile, 'load_member_since', lambda user_id: JOINED)
    monkeypatch.setattr(profile, 'load_stats', lambda user_id: empty_row)
    stats = client.get('/profile').json()['stats']
    assert stats['current_level'] == 1
    assert stats['submissions_recorded'] == 0
    assert stats['early_submissions'] == 0
    assert stats['best_award'] == 0
    assert stats['average_award'] == 0
    assert stats['last_submitted_at'] is None


def test_missing_stats_row_does_not_crash(client, monkeypatch):
    log_in_as(STUDENT_USER)
    monkeypatch.setattr(profile, 'load_member_since', lambda user_id: JOINED)
    monkeypatch.setattr(profile, 'load_stats', lambda user_id: {})
    response = client.get('/profile')
    assert response.status_code == 200
    assert response.json()['stats']['total_points'] == 0


def test_profile_never_sends_password_hash(client, monkeypatch):
    log_in_as(STUDENT_USER)
    monkeypatch.setattr(profile, 'load_member_since', lambda user_id: JOINED)
    monkeypatch.setattr(profile, 'load_stats', lambda user_id: STATS_ROW)
    assert 'password' not in client.get('/profile').text


# ---------- admins ----------

def test_admin_gets_profile_without_stats(client, monkeypatch):
    log_in_as(ADMIN_USER)
    monkeypatch.setattr(profile, 'load_member_since', lambda user_id: JOINED)
    monkeypatch.setattr(profile, 'load_stats', lambda user_id: pytest.fail('admins have no stats'))
    body = client.get('/profile').json()
    assert body['role'] == 'admin'
    assert body['stats'] is None


# ---------- database problems ----------

def test_profile_database_down(client, monkeypatch):
    log_in_as(STUDENT_USER)
    monkeypatch.setattr(profile, 'load_member_since', broken_database)
    response = client.get('/profile')
    assert response.status_code == 503
    assert response.json()['detail'] == 'Database is not available'


def test_stats_database_down(client, monkeypatch):
    log_in_as(STUDENT_USER)
    monkeypatch.setattr(profile, 'load_member_since', lambda user_id: JOINED)
    monkeypatch.setattr(profile, 'load_stats', broken_database)
    assert client.get('/profile').status_code == 503


def test_missing_join_date_is_allowed(client, monkeypatch):
    log_in_as(ADMIN_USER)
    monkeypatch.setattr(profile, 'load_member_since', lambda user_id: None)
    body = client.get('/profile').json()
    assert body['member_since'] is None