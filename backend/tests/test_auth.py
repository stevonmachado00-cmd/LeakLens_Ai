import pytest
from fastapi.testclient import TestClient

from app.models.user import User

def test_register_user_success(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": "test@example.com",
            "password": "StrongPassword123"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"
    assert data["is_active"] is True
    assert "id" in data
    assert "password" not in data
    assert "hashed_password" not in data

def test_register_user_duplicate_email(client: TestClient):
    # First registration
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "First User",
            "email": "duplicate@example.com",
            "password": "StrongPassword123"
        }
    )
    assert response.status_code == 201
    
    # Second registration with same email
    response2 = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Second User",
            "email": "duplicate@example.com",
            "password": "AnotherPassword456"
        }
    )
    assert response2.status_code == 400
    assert response2.json()["detail"] == "Email already registered"

def test_register_user_invalid_email(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": "not-an-email",
            "password": "StrongPassword123"
        }
    )
    assert response.status_code == 422  # Request Validation Error

def test_register_user_short_password(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": "shortpass@example.com",
            "password": "short"
        }
    )
    assert response.status_code == 422  # Validation Error for password length < 8

def test_login_success(client: TestClient):
    # Register first
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Login User",
            "email": "login@example.com",
            "password": "StrongPassword123"
        }
    )
    
    # Login via JSON POST
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "login@example.com",
            "password": "StrongPassword123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password(client: TestClient):
    # Register first
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Login User",
            "email": "wrongpass@example.com",
            "password": "StrongPassword123"
        }
    )
    
    # Login with incorrect password
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "wrongpass@example.com",
            "password": "IncorrectPassword"
        }
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"

def test_login_nonexistent_email(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "SomePassword123"
        }
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"

def test_get_me_success(client: TestClient):
    # Register
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Profile User",
            "email": "profile@example.com",
            "password": "StrongPassword123"
        }
    )
    
    # Login to get token
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "profile@example.com",
            "password": "StrongPassword123"
        }
    )
    token = login_response.json()["access_token"]
    
    # Access profile
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "profile@example.com"
    assert data["full_name"] == "Profile User"
    assert data["is_active"] is True

def test_get_me_no_token(client: TestClient):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401

def test_get_me_invalid_token(client: TestClient):
    headers = {"Authorization": "Bearer invalid_token_value_here"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401


def test_login_access_token_with_form_data(client: TestClient):
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Form Login User",
            "email": "form-login@example.com",
            "password": "StrongPassword123",
        },
    )

    response = client.post(
        "/api/v1/auth/login/access-token",
        data={"username": "form-login@example.com", "password": "StrongPassword123"},
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


def test_inactive_user_cannot_log_in(client: TestClient, db_session):
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Inactive User",
            "email": "inactive-login@example.com",
            "password": "StrongPassword123",
        },
    )
    user = db_session.query(User).filter(User.email == "inactive-login@example.com").one()
    user.is_active = False
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "inactive-login@example.com", "password": "StrongPassword123"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Inactive user"


def test_inactive_user_token_is_rejected(client: TestClient, db_session):
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Inactive Token User",
            "email": "inactive-token@example.com",
            "password": "StrongPassword123",
        },
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "inactive-token@example.com", "password": "StrongPassword123"},
    )
    token = login_response.json()["access_token"]

    user = db_session.query(User).filter(User.email == "inactive-token@example.com").one()
    user.is_active = False
    db_session.commit()

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Inactive user"
