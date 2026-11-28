from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from app.api import badges
from app.api.auth import UserInfo, get_current_user
from app.main import app

ADMIN_USER = UserInfo(user_id=1, username='boss',
                      email='boss@example.com', role='admin')
STUDENT = UserInfo(user_id=3, username='student',
                   email='student@example.com', role='student')
DUE = datetime(2026, 11, 20, 12, 0)


def row(hours_early):
    return {'due_at': DUE, 'submitted_at': DUE - timedelta(hours=hours_early)}


def earned(rows):
    return {b['id'] for b in badges.compute_badges(rows) if b['earned']}


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def login(user):
    app.dependency_overrides[get_current_user] = lambda: user


def test_no_submissions_earns_nothing():
    assert earned([]) == set()


def test_first_submissions():
    assert earned([row(5)]) == {'first_submission'}


def test_early_bird():
    assert 'early_bird' not in earned([row(23)])
    assert 'early_bird' in earned([row(24)])


def test_week_ahead_needs_7_days():
    assert 'week_ahead' not in earned([row(24*7-1)])
    assert 'week_ahead' in earned([row(24*7)])


def test_clutch_is_last_hour_and_not_late():
    assert 'clutch' in earned([row(0.5)])
    assert 'clutch' not in earned([row(2)])
    assert 'clutch' not in earned([row(-0.5)])


def test_high_five_needs_5_submissions():
    assert 'high_five' not in earned([row(5)]*4)
    assert 'high_five' in earned([row(5)]*5)


def test_on_a_roll_needs_3_submissions_in_a_row():
    assert 'on_a_roll' not in earned([row(5), row(5)])
    assert 'on_a_roll' in earned([row(5), row(5), row(5)])


def test_late_submission_breaks_the_roll():
    assert 'on_a_roll' not in earned([row(5), row(5), row(-1), row(5), row(5)])


def test_missing_date_do_not_crash():
    assert earned([{'due_at': None, 'submitted_at': None}]) == {
        'first_submission'}


def test_badges_require_login(client):
    assert client.get('/badges').status_code == 401


def test_admine_cant_use_student_badges(client, monkeypatch):
    login(ADMIN_USER)
    monkeypatch.setattr(badges, 'load_submissions',
                        lambda *args: pytest.fail('Database should not be queried'))
    assert client.get('/badges').status_code == 403


def test_student_sees_own_badges(client, monkeypatch):
    login(STUDENT)
    called = []

    def fake_load(user_id):
        called.append(user_id)
        return [row(30)]
    monkeypatch.setattr(badges, 'load_submissions', fake_load)
    res = client.get('/badges')
    assert res.status_code == 200
    body = res.json()
    assert called == [3]
    assert body['total'] == 6
    assert body['earned_count'] == 2
    by_id = {b['id']: b['earned'] for b in body['badges']}
    assert by_id['first_submission'] is True
    assert by_id['early_bird'] is True
    assert by_id['high_five'] is False


def test_database_error_returns_503(client, monkeypatch):
    login(STUDENT)

    def broken(*args):
        raise SQLAlchemyError('db is down')
    monkeypatch.setattr(badges, 'load_submissions', broken)
    assert client.get('/badges').status_code == 503
