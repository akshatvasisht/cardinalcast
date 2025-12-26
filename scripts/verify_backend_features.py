"""Verification script: Test backend daily claims and lifecycle (mock)."""
import logging
import requests
import sys
import time

# Use localhost:8000 assuming backend is running elsewhere or started manually
BASE_URL = "http://localhost:8000"

def test_daily_claims():
    print("Testing Daily Claims...")
    
    # 1. Register a fresh user
    username = f"verifier_{int(time.time())}"
    password = "password123"
    try:
        reg_resp = requests.post(f"{BASE_URL}/auth/register", json={"username": username, "password": password})
        if reg_resp.status_code != 200:
            print(f"FAILED: Register user ({reg_resp.status_code})")
            return
        
        token = reg_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Check status (should be AVAILABLE)
        status_resp = requests.get(f"{BASE_URL}/daily/status", headers=headers)
        if status_resp.status_code != 200 or status_resp.json()["status"] != "AVAILABLE":
            print(f"FAILED: Initial status check. Got {status_resp.json()}")
            return
        print("PASS: Initial status AVAILABLE")
        
        # 3. Claim
        claim_resp = requests.post(f"{BASE_URL}/daily/claim", headers=headers)
        if claim_resp.status_code != 200 or claim_resp.json()["status"] != "CLAIMED":
            print(f"FAILED: Claim. Got {claim_resp.status_code} {claim_resp.text}")
            return
        print("PASS: Claim successful")
        
        # 4. Check status again (should be CLAIMED)
        status_resp_2 = requests.get(f"{BASE_URL}/daily/status", headers=headers)
        if status_resp_2.json()["status"] != "CLAIMED":
             print(f"FAILED: Post-claim status check. Got {status_resp_2.json()}")
             return
        print("PASS: Post-claim status CLAIMED")

        # 5. Claim again (should fail)
        claim_resp_2 = requests.post(f"{BASE_URL}/daily/claim", headers=headers)
        if claim_resp_2.status_code != 400:
            print(f"FAILED: Second claim should satisfy 400. Got {claim_resp_2.status_code}")
            return
        print("PASS: Second claim correctly blocked")

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        print("Ensure backend is running on localhost:8000")


def test_leaderboard():
    print("Testing Leaderboard...")
    resp = requests.get(f"{BASE_URL}/leaderboard")
    if resp.status_code != 200:
        print(f"FAILED: Leaderboard fetch {resp.status_code}")
        return
    data = resp.json()
    if not isinstance(data, list):
         print("FAILED: Leaderboard format")
         return
    print(f"PASS: Leaderboard fetch ({len(data)} entries)")


def test_over_under():
    print("Testing Over/Under Wager...")
    # Requires auth and valid forecast/odds. 
    # Since we can't easily mock ML data without running the full ingestion, 
    # this test might fail 400 if no forecast exists.
    # We will just print the attempt.
    pass


def test_dashboard_dates():
    print("Testing Dashboard Dates...")
    resp = requests.get(f"{BASE_URL}/odds/dates")
    if resp.status_code != 200:
        print(f"FAILED: Dates fetch {resp.status_code}")
        return
    data = resp.json()
    if not isinstance(data, list):
         print("FAILED: Dates format (expected list)")
         return
    print(f"PASS: Dashboard dates fetch ({len(data)} distinct dates)")


if __name__ == "__main__":
    test_daily_claims()
    test_leaderboard()
    test_dashboard_dates()
    # test_over_under() # skipped until data is seeded
