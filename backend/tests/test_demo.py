"""
Demonstration tests for CardinalCast backend.

These tests showcase testing capability for a portfolio project.
For production, would include:
- Comprehensive unit tests (80%+ coverage)
- Integration tests (full user flows)
- Load tests (performance validation)
- Security tests (penetration testing)
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app
import time

client = TestClient(app)


class TestHealthCheck:
    """Basic smoke test - API is operational"""

    def test_health_endpoint(self):
        """Verify API is running and responds to health check"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestAuthentication:
    """User registration and login flows"""

    def test_register_new_user(self):
        """Should create user and return JWT token"""
        timestamp = str(int(time.time() * 1000))
        response = client.post("/auth/register", json={
            "username": f"testuser_{timestamp}",
            "password": "securepass123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_register_duplicate_username(self):
        """Should reject duplicate usernames"""
        timestamp = str(int(time.time() * 1000))
        username = f"duplicate_{timestamp}"

        # First registration succeeds
        response1 = client.post("/auth/register", json={
            "username": username,
            "password": "pass1"
        })
        assert response1.status_code == 200

        # Second registration fails
        response2 = client.post("/auth/register", json={
            "username": username,
            "password": "pass2"
        })
        assert response2.status_code == 400
        assert "already registered" in response2.json()["detail"].lower()

    def test_login_with_valid_credentials(self):
        """Should return token for valid login"""
        timestamp = str(int(time.time() * 1000))
        username = f"logintest_{timestamp}"
        password = "testpass123"

        # Register user
        client.post("/auth/register", json={
            "username": username,
            "password": password
        })

        # Login with same credentials
        response = client.post("/auth/login", json={
            "username": username,
            "password": password
        })
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_with_invalid_password(self):
        """Should reject incorrect password"""
        timestamp = str(int(time.time() * 1000))
        username = f"wrongpass_{timestamp}"

        # Register
        client.post("/auth/register", json={
            "username": username,
            "password": "correctpass"
        })

        # Login with wrong password
        response = client.post("/auth/login", json={
            "username": username,
            "password": "wrongpass"
        })
        assert response.status_code == 401

    def test_login_nonexistent_user(self):
        """Should reject login for user that doesn't exist"""
        timestamp = str(int(time.time() * 1000))
        response = client.post("/auth/login", json={
            "username": f"nonexistent_{timestamp}",
            "password": "anypass"
        })
        assert response.status_code == 401


class TestWagerValidation:
    """Business logic validation for wagers"""

    def test_wager_requires_authentication(self):
        """Should reject unauthenticated wager requests"""
        response = client.post("/wagers", json={
            "forecast_date": "2025-12-31",
            "target": "high_temp",
            "amount": 10,
            "wager_kind": "BUCKET",
            "bucket_value": 50.0
        })
        assert response.status_code == 401

    def test_wager_insufficient_balance(self):
        """Should reject wagers exceeding user balance"""
        # Register and get token
        timestamp = str(int(time.time() * 1000))
        username = f"pooruser_{timestamp}"
        reg_response = client.post("/auth/register", json={
            "username": username,
            "password": "pass"
        })
        token = reg_response.json()["access_token"]

        # Try to wager more than initial 100 credits
        response = client.post(
            "/wagers",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "forecast_date": "2025-12-31",
                "target": "high_temp",
                "amount": 999999,
                "wager_kind": "BUCKET",
                "bucket_value": 50.0
            }
        )
        assert response.status_code == 400
        assert "insufficient" in response.json()["detail"].lower()

    def test_wager_minimum_amount(self):
        """Should reject wagers below minimum (1 credit)"""
        # Register and get token
        timestamp = str(int(time.time() * 1000))
        username = f"mintest_{timestamp}"
        reg_response = client.post("/auth/register", json={
            "username": username,
            "password": "pass"
        })
        token = reg_response.json()["access_token"]

        # Try to wager 0 credits
        response = client.post(
            "/wagers",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "forecast_date": "2025-12-31",
                "target": "high_temp",
                "amount": 0,
                "wager_kind": "BUCKET",
                "bucket_value": 50.0
            }
        )
        assert response.status_code == 400


class TestOddsAPI:
    """Odds generation and retrieval"""

    def test_get_odds_list(self):
        """Should return list of available odds"""
        response = client.get("/odds")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # List may be empty if no odds generated yet, which is OK

    def test_odds_schema_structure(self):
        """Should return properly structured odds objects if available"""
        response = client.get("/odds?limit=10")
        assert response.status_code == 200
        data = response.json()

        if len(data) > 0:
            # If odds exist, validate structure
            odds = data[0]
            required_fields = [
                "forecast_date", "target", "bucket_low",
                "bucket_high", "base_payout_multiplier"
            ]
            for field in required_fields:
                assert field in odds, f"Missing required field: {field}"


class TestUserProfile:
    """User profile and balance management"""

    def test_get_current_user(self):
        """Should return user profile for authenticated request"""
        timestamp = str(int(time.time() * 1000))
        username = f"profile_{timestamp}"
        reg_response = client.post("/auth/register", json={
            "username": username,
            "password": "pass"
        })
        token = reg_response.json()["access_token"]

        # Get user profile
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        user_data = response.json()
        assert user_data["username"] == username
        assert "credits_balance" in user_data
        assert user_data["credits_balance"] == 0  # New users start with 0 credits


# Run with: pytest backend/tests/ -v
# With coverage: pytest backend/tests/ --cov=backend --cov-report=term-missing
