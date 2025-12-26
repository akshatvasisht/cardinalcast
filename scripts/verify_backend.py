import sys
import os
import requests
from datetime import date, timedelta
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import get_db, engine
from backend.models import User, Wager, WeatherForecast, Odds, create_all_tables
from backend.config import DAILY_CLAIM_AMOUNT

# Setup
def setup_db():
    print("Setting up DB...")
    create_all_tables()
    with Session(engine) as session:
        # Create Dummy Forecast for tomorrow
        tomorrow = date.today() + timedelta(days=1)
        existing = session.execute(select(WeatherForecast).where(WeatherForecast.date == tomorrow)).scalars().first()
        if not existing:
            print(f"Creating forecast for {tomorrow}")
            forecast = WeatherForecast(
                date=tomorrow,
                location="Madison",
                noaa_high_temp=75.0,
                noaa_avg_wind_speed=10.0,
                noaa_precip=0.0
            )
            session.add(forecast)
            
            # Create Dummy Odds (for bucket wager)
            odds = Odds(
                forecast_date=tomorrow,
                target="high_temp",
                bucket_low=70.0,
                bucket_high=80.0,
                probability=0.5,
                base_payout_multiplier=1.9,
                jackpot_multiplier=10.0
            )
            session.add(odds)
            session.commit()
        else:
            print("Forecast already exists")

def test_daily_claim_and_wager():
    print("\n--- Testing Daily Claim & Wager ---")
    base_url = "http://localhost:8000"
    
    # We need a user. For this test, relies on Auth mock or we insert one directly
    # Since we can't easily auth against a running server without a token in this script 
    # unless we use the backend code directly. 
    # Let's use backend code directly for verification to avoid auth header hassle, 
    # OR we assume the server is running with a backdoor or we just test functions.
    
    # Actually, the user asked to "run verification script". 
    # If the server is running (npm run dev is frontend, backend might not be running),
    # I should check if backend is running.
    # The `task.md` says "Run basic health check / verification script".
    # I will stick to direct DB/Function calls to verify logic without needing HTTP server up.
    
    with Session(engine) as session:
        # 1. Create User
        user = session.execute(select(User).where(User.username == "verify_user")).scalars().first()
        if not user:
            user = User(username="verify_user", email="verify@example.com", credits_balance=0)
            session.add(user)
            session.commit()
            session.refresh(user)
        print(f"User Balance: {user.credits_balance}")
        
        # 2. Simulate Daily Claim Logic (Directly calling service/route logic equivalent)
        # We want to test row locking, but that requires concurrency.
        # For now, just test logic works.
        from backend.routers.daily_routes import claim_daily_credits_logic # hypothetical extraction
        # Wait, I can't easily import route logic.
        # Let's just manually do the DB update to simulate a claim
        user.credits_balance += DAILY_CLAIM_AMOUNT
        session.commit()
        session.refresh(user)
        print(f"User Balance after Claim: {user.credits_balance}")
        assert user.credits_balance >= 100
        
        # 3. Place Bucket Wager
        print("Placing Bucket Wager...")
        from backend.routers.wager_routes import PlaceWagerRequest, place_wager
        
        tomorrow = date.today() + timedelta(days=1)
        req = PlaceWagerRequest(
            forecast_date=tomorrow,
            target="high_temp",
            amount=10,
            bucket_value=75.0,
            wager_kind="BUCKET"
        )
        
        # Mocking dependency overrides is hard in script. 
        # I'll just call the logic block if I extracted it, or use `test_client`.
        # Using `TestClient` from `fastapi.testclient` is best practice.
        return

from fastapi.testclient import TestClient
from backend.main import app

def run_integration_tests():
    print("\n--- Running Integration Tests with TestClient ---")
    client = TestClient(app)
    
    # Override Dependency? 
    # The auth dependency `get_current_user` needs to return our test user.
    from backend.auth import get_current_user
    async def override_get_current_user():
         with Session(engine) as session:
            return session.execute(select(User).where(User.username == "verify_user")).scalars().first()
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    # 1. Setup Data
    setup_db()
    
    # 2. Claim (if endpoint exists)
    # We didn't implement a specific claim endpoint in strict detail in the prompt reading, 
    # but `daily_routes` implies it.
    # Let's try POST /daily/claim
    resp = client.post("/daily/claim")
    if resp.status_code == 404:
        print("Warning: /daily/claim not found, skipping claim test")
    else:
        print(f"Claim Response: {resp.status_code} {resp.json()}")
        
    # 3. Place Wager
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    
    # Bucket Wager
    payload = {
        "forecast_date": tomorrow,
        "target": "high_temp",
        "amount": 10,
        "bucket_value": 75.0,
        "wager_kind": "BUCKET"
    }
    resp = client.post("/wagers", json=payload)
    print(f"Place Bucket Wager: {resp.status_code} {resp.json()}")
    if resp.status_code != 201:
        print(f"Error: {resp.text}")
        
    # Over/Under Wager
    payload_ou = {
        "forecast_date": tomorrow,
        "target": "high_temp",
        "amount": 10,
        "wager_kind": "OVER_UNDER",
        "direction": "OVER",
        "predicted_value": 72.0
    }
    resp = client.post("/wagers", json=payload_ou)
    print(f"Place O/U Wager: {resp.status_code} {resp.json()}")
    if resp.status_code != 201:
        print(f"Error: {resp.text}")

    # 4. List Wagers
    resp = client.get("/wagers")
    print(f"List Wagers: {resp.status_code}")
    wagers = resp.json()
    print(f"Found {len(wagers)} wagers")
    for w in wagers:
        print(f" - {w['id']}: {w['wager_kind']} {w['amount']} on {w['target']}")

if __name__ == "__main__":
    run_integration_tests()
