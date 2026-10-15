import pytest
from fastapi.testclient import TestClient

from app.api import auth
from app.core.passwords import verify_password
from app.main import app

# registration tests, the database is faked so mysql is not needed
client = TestClient(app)


# pretend users table stored in a python list
@pytest.fixture
def fake_db(monkeypatch):
    users = []

    def find_taken_field(username, email):
        for user in users:
            if user['username'] == username:
                return 'username'
            if user['email'] == email:
                return 'email'
        return None

    def insert_user(username, email, password_hash):
        users.append({'username': username, 'email': email, 'password_hash': password_hash})
        return len(users)

    monkeypatch.setattr(auth, 'find_taken_field', find_taken_field)
    monkeypatch.setattr(auth, 'insert_user', insert_user)
    return users


def good_body(**changes):
    body = {'username': 'ale_r', 'email': 'Ale@UFL.edu', 'password': 'longpassword'}
    body.update(changes)
    return body


def test_register_success(fake_db):
    response = client.post('/auth/register', json=good_body())
    assert response.status_code == 201
    data = response.json()
    assert data == {'user_id': 1, 'username': 'ale_r', 'email': 'ale@ufl.edu', 'role': 'student'}
    assert 'password' not in str(data)


def test_password_is_hashed_not_stored(fake_db):
    client.post('/auth/register', json=good_body())
    stored = fake_db[0]['password_hash']
    assert stored != 'longpassword'
    assert verify_password('longpassword', stored)


def test_cannot_register_as_admin(fake_db):
    response = client.post('/auth/register', json=good_body(role='admin'))
    assert response.json()['role'] == 'student'


def test_duplicate_username(fake_db):
    client.post('/auth/register', json=good_body())
    response = client.post('/auth/register', json=good_body(email='other@ufl.edu'))
    assert response.status_code == 409


def test_duplicate_email_any_case(fake_db):
    client.post('/auth/register', json=good_body())
    response = client.post('/auth/register', json=good_body(username='someone', email='ALE@ufl.edu'))
    assert response.status_code == 409


# each of these should get rejected with a 422
@pytest.mark.parametrize('changes', [
    {'username': 'ab'},           # too short
    {'username': 'bad name!'},    # spaces and symbols
    {'email': 'not-an-email'},    # not an email
    {'password': 'short'},        # under 8 characters
    {'password': 'x' * 73},       # over the bcrypt limit
])
def test_bad_input_rejected(fake_db, changes):
    assert client.post('/auth/register', json=good_body(**changes)).status_code == 422