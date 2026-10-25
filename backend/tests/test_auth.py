"""
BidSmart Analytics — Authentication & RBAC Test Suite (Phase 4)
Tests:
1. User Registration (Success, Validation, Password Complexity, Anti-Admin self-assign)
2. Duplicate Account Prevention (Username and Email conflicts)
3. Cryptographic Password Security (Bcrypt hashing, zero plaintext, zero hash leakage)
4. User Authentication & JWT Issuance (Username login, Email login, Invalid credentials)
5. Token Refresh & OAuth2 Form Compatibility
6. Authentication Dependencies & User Profile (/users/me)
7. Role-Based Access Control (RBAC) 401 Unauthorized & 403 Forbidden Enforcements
8. Administrative Governance (Role Promotion, Account Suspension)
"""

import pytest
from fastapi import status
from sqlalchemy.orm import Session
from app.models.user import User, UserStatus
from app.models.role import Role
from app.models.audit_log import AuditLog


# -----------------------------------------------------------------------------
# 1. REGISTRATION TESTS
# -----------------------------------------------------------------------------

def test_register_buyer_success(client, db: Session):
    """Verify clean registration of a buyer account."""
    payload = {
        "username": "new_buyer_test",
        "email": "new.buyer.test@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test New Buyer",
        "phone": "+1-555-8888",
        "role": "BUYER"
    }
    try:
        response = client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["username"] == "new_buyer_test"
        assert data["email"] == "new.buyer.test@example.com"
        assert data["role"] == "BUYER"
        assert "password_hash" not in data  # Never expose password hash!
        assert "password" not in data

        # Verify user in database
        db_user = db.query(User).filter(User.username == "new_buyer_test").first()
        assert db_user is not None
        assert db_user.password_hash.startswith("$2b$")  # Must be bcrypt
    finally:
        u = db.query(User).filter(User.username == "new_buyer_test").first()
        if u:
            db.query(AuditLog).filter(AuditLog.entity_id == u.id, AuditLog.entity_type == "USER").delete()
            db.delete(u)
            db.commit()


def test_register_seller_success(client, db: Session):
    """Verify clean registration of a seller account."""
    payload = {
        "username": "new_seller_test",
        "email": "new.seller.test@example.com",
        "password": "SellerPassword123!",
        "full_name": "Test New Seller",
        "role": "SELLER"
    }
    try:
        response = client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["role"] == "SELLER"
    finally:
        u = db.query(User).filter(User.username == "new_seller_test").first()
        if u:
            db.query(AuditLog).filter(AuditLog.entity_id == u.id, AuditLog.entity_type == "USER").delete()
            db.delete(u)
            db.commit()


def test_register_duplicate_username_conflict(client):
    """Verify 409 Conflict when attempting to register duplicate username."""
    payload = {
        "username": "admin_sarah",  # Existing seed username
        "email": "unique.sarah.email@example.com",
        "password": "Password123!",
        "full_name": "Sarah Duplicate",
        "role": "BUYER"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "already registered" in response.json()["detail"].lower()


def test_register_duplicate_email_conflict(client):
    """Verify 409 Conflict when attempting to register duplicate email."""
    payload = {
        "username": "brand_new_unique_user",
        "email": "sarah.chen@bidsmart.io",  # Existing seed email
        "password": "Password123!",
        "full_name": "Sarah Email Dup",
        "role": "BUYER"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "already registered" in response.json()["detail"].lower()


def test_register_password_complexity_validation(client):
    """Verify 422 Unprocessable Content on weak passwords."""
    # 1. Too short (< 8 chars)
    r1 = client.post("/api/v1/auth/register", json={
        "username": "weak_pass_1", "email": "w1@test.com", "password": "Pass1", "full_name": "Test"
    })
    assert r1.status_code == 422

    # 2. No uppercase
    r2 = client.post("/api/v1/auth/register", json={
        "username": "weak_pass_2", "email": "w2@test.com", "password": "password123", "full_name": "Test"
    })
    assert r2.status_code == 422

    # 3. No numeric digit
    r3 = client.post("/api/v1/auth/register", json={
        "username": "weak_pass_3", "email": "w3@test.com", "password": "PasswordWithoutDigits", "full_name": "Test"
    })
    assert r3.status_code == 422


def test_register_disallows_admin_role_self_assignment(client):
    """Security check: Attempting to self-register with ADMIN role must be rejected."""
    payload = {
        "username": "rogue_admin_wannabe",
        "email": "rogue.admin@test.com",
        "password": "Password123!",
        "full_name": "Rogue Admin",
        "role": "ADMIN"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    assert "admin is forbidden" in response.text.lower()


# -----------------------------------------------------------------------------
# 2. LOGIN & JWT ISSUANCE TESTS
# -----------------------------------------------------------------------------

def test_login_with_username_success(client):
    """Verify login with username returns access and refresh tokens."""
    response = client.post("/api/v1/auth/login", json={
        "username_or_email": "elena_r",
        "password": "password123"
    })
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 15 * 60
    assert data["user"]["username"] == "elena_r"
    assert data["user"]["role"] == "BUYER"
    assert "password_hash" not in data["user"]


def test_login_with_email_success(client):
    """Verify login with email address."""
    response = client.post("/api/v1/auth/login", json={
        "username_or_email": "marcus.vance@vanceestates.com",
        "password": "password123"
    })
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["user"]["username"] == "vance_estates"
    assert data["user"]["role"] == "SELLER"


def test_login_invalid_password(client):
    """Verify 401 Unauthorized when password is incorrect."""
    response = client.post("/api/v1/auth/login", json={
        "username_or_email": "admin_sarah",
        "password": "WrongPassword123!"
    })
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "invalid username/email or password" in response.json()["detail"].lower()


def test_login_nonexistent_user(client):
    """Verify 401 Unauthorized for unknown user."""
    response = client.post("/api/v1/auth/login", json={
        "username_or_email": "non_existent_ghost_user",
        "password": "SomePassword123!"
    })
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_oauth2_form_login(client):
    """Verify standard OAuth2 form login for Swagger UI interactive testing."""
    response = client.post(
        "/api/v1/auth/login/oauth",
        data={"username": "admin_sarah", "password": "password123"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == "ADMIN"


def test_refresh_token_lifecycle(client):
    """Verify renewing access token using refresh token."""
    login_resp = client.post("/api/v1/auth/login", json={
        "username_or_email": "david_k",
        "password": "password123"
    })
    refresh_token = login_resp.json()["refresh_token"]

    refresh_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == status.HTTP_200_OK
    data = refresh_resp.json()
    assert "access_token" in data
    assert data["user"]["username"] == "david_k"


# -----------------------------------------------------------------------------
# 3. AUTHENTICATION DEPENDENCIES & USER PROFILE TESTS
# -----------------------------------------------------------------------------

def test_get_current_user_me_unauthenticated(client):
    """Verify 401 Unauthorized when accessing /users/me without token."""
    response = client.get("/api/v1/users/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user_me_with_invalid_token(client):
    """Verify 401 Unauthorized with forged/invalid token."""
    headers = {"Authorization": "Bearer invalid.token.signature.payload"}
    response = client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user_me_authenticated(client):
    """Verify successful retrieval of own profile using valid JWT token."""
    login_resp = client.post("/api/v1/auth/login", json={
        "username_or_email": "elena_r",
        "password": "password123"
    })
    token = login_resp.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    me_resp = client.get("/api/v1/users/me", headers=headers)
    assert me_resp.status_code == status.HTTP_200_OK
    data = me_resp.json()
    assert data["username"] == "elena_r"
    assert data["email"] == "elena.rostova@gmail.com"
    assert data["role"] == "BUYER"
    assert "password_hash" not in data


def test_update_user_me_profile(client):
    """Verify updating full name and phone number on current profile."""
    login_resp = client.post("/api/v1/auth/login", json={
        "username_or_email": "elena_r",
        "password": "password123"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    update_payload = {"full_name": "Elena Rostova Updated", "phone": "+1-555-9999"}
    put_resp = client.put("/api/v1/users/me", json=update_payload, headers=headers)
    assert put_resp.status_code == status.HTTP_200_OK
    assert put_resp.json()["full_name"] == "Elena Rostova Updated"
    assert put_resp.json()["phone"] == "+1-555-9999"


# -----------------------------------------------------------------------------
# 4. ROLE-BASED ACCESS CONTROL (RBAC) & 401/403 TESTS
# -----------------------------------------------------------------------------

def test_rbac_unauthenticated_requests(client):
    """Verify 401 on role-gated routes without authorization token."""
    assert client.get("/api/v1/users/portal/buyer-only").status_code == status.HTTP_401_UNAUTHORIZED
    assert client.get("/api/v1/users/portal/seller-only").status_code == status.HTTP_401_UNAUTHORIZED
    assert client.get("/api/v1/users/portal/admin-only").status_code == status.HTTP_401_UNAUTHORIZED


def test_rbac_buyer_permissions(client):
    """
    Verify Buyer role permissions:
    - Allowed: /portal/buyer-only (200)
    - Forbidden: /portal/seller-only (403)
    - Forbidden: /portal/admin-only (403)
    """
    login_resp = client.post("/api/v1/auth/login", json={"username_or_email": "elena_r", "password": "password123"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Allowed buyer portal
    r1 = client.get("/api/v1/users/portal/buyer-only", headers=headers)
    assert r1.status_code == status.HTTP_200_OK
    assert r1.json()["access"] == "granted"

    # 2. Forbidden seller portal
    r2 = client.get("/api/v1/users/portal/seller-only", headers=headers)
    assert r2.status_code == status.HTTP_403_FORBIDDEN
    assert "insufficient privileges" in r2.json()["detail"].lower()

    # 3. Forbidden admin portal
    r3 = client.get("/api/v1/users/portal/admin-only", headers=headers)
    assert r3.status_code == status.HTTP_403_FORBIDDEN


def test_rbac_seller_permissions(client):
    """
    Verify Seller role permissions:
    - Allowed: /portal/seller-only (200)
    - Forbidden: /portal/buyer-only (403)
    - Forbidden: /portal/admin-only (403)
    """
    login_resp = client.post("/api/v1/auth/login", json={"username_or_email": "vance_estates", "password": "password123"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Allowed seller portal
    r1 = client.get("/api/v1/users/portal/seller-only", headers=headers)
    assert r1.status_code == status.HTTP_200_OK

    # 2. Forbidden buyer portal (seller is not a buyer)
    r2 = client.get("/api/v1/users/portal/buyer-only", headers=headers)
    assert r2.status_code == status.HTTP_403_FORBIDDEN

    # 3. Forbidden admin portal
    r3 = client.get("/api/v1/users/portal/admin-only", headers=headers)
    assert r3.status_code == status.HTTP_403_FORBIDDEN


def test_rbac_admin_omnipotence(client):
    """
    Verify Admin role has elevated access across all portals:
    - Allowed: /portal/buyer-only (200)
    - Allowed: /portal/seller-only (200)
    - Allowed: /portal/admin-only (200)
    """
    login_resp = client.post("/api/v1/auth/login", json={"username_or_email": "admin_sarah", "password": "password123"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/v1/users/portal/buyer-only", headers=headers).status_code == status.HTTP_200_OK
    assert client.get("/api/v1/users/portal/seller-only", headers=headers).status_code == status.HTTP_200_OK
    assert client.get("/api/v1/users/portal/admin-only", headers=headers).status_code == status.HTTP_200_OK


# -----------------------------------------------------------------------------
# 5. ADMINISTRATIVE GOVERNANCE TESTS
# -----------------------------------------------------------------------------

def test_admin_list_users_governance(client):
    """Verify only admin can list all registered users."""
    buyer_login = client.post("/api/v1/auth/login", json={"username_or_email": "david_k", "password": "password123"}).json()
    r_buyer = client.get("/api/v1/users", headers={"Authorization": f"Bearer {buyer_login['access_token']}"})
    assert r_buyer.status_code == status.HTTP_403_FORBIDDEN

    admin_login = client.post("/api/v1/auth/login", json={"username_or_email": "admin_sarah", "password": "password123"}).json()
    r_admin = client.get("/api/v1/users", headers={"Authorization": f"Bearer {admin_login['access_token']}"})
    assert r_admin.status_code == status.HTTP_200_OK
    assert len(r_admin.json()) >= 32


def test_admin_role_promotion(client, db: Session):
    """Verify admin promoting a BUYER to SELLER."""
    admin_token = client.post("/api/v1/auth/login", json={"username_or_email": "admin_sarah", "password": "password123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    patch_resp = client.patch("/api/v1/users/9/role", json={"role": "SELLER"}, headers=headers)
    assert patch_resp.status_code == status.HTTP_200_OK
    assert patch_resp.json()["role"] == "SELLER"

    # Reset role back to BUYER for test idempotency
    client.patch("/api/v1/users/9/role", json={"role": "BUYER"}, headers=headers)


def test_admin_account_suspension_enforcement(client, db: Session):
    """
    Verify account suspension flow:
    1. Admin suspends a user
    2. Suspended user is rejected on login with 403
    3. Existing tokens for suspended user are rejected on protected routes with 403
    4. Admin restores user to ACTIVE
    """
    admin_token = client.post("/api/v1/auth/login", json={"username_or_email": "admin_sarah", "password": "password123"}).json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    user_token = client.post("/api/v1/auth/login", json={"username_or_email": "collector_dan", "password": "password123"}).json()["access_token"]

    suspend_resp = client.patch("/api/v1/users/10/status", json={"status": "SUSPENDED"}, headers=admin_headers)
    assert suspend_resp.status_code == status.HTTP_200_OK
    assert suspend_resp.json()["status"] == "SUSPENDED"

    login_attempt = client.post("/api/v1/auth/login", json={"username_or_email": "collector_dan", "password": "password123"})
    assert login_attempt.status_code == status.HTTP_403_FORBIDDEN
    assert "account suspended" in login_attempt.json()["detail"].lower()

    me_attempt = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {user_token}"})
    assert me_attempt.status_code == status.HTTP_403_FORBIDDEN

    restore_resp = client.patch("/api/v1/users/10/status", json={"status": "ACTIVE"}, headers=admin_headers)
    assert restore_resp.status_code == status.HTTP_200_OK
    assert restore_resp.json()["status"] == "ACTIVE"
