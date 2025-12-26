import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def test_imports():
    print("Testing imports...")
    try:
        from backend import config
        print(f"Config loaded: DB_URL={config.DB_URL}, HOUSE_EDGE={config.HOUSE_EDGE}")
        
        from backend.database import engine, SessionLocal
        print("Database engine loaded.")
        
        from backend.odds_service import db as ml_db
        print("Odds service DB adapter loaded.")
        
        from backend.routers import wager_routes
        print("Wager routes loaded.")

        from backend.resolution import resolve_wagers
        print("Resolution module loaded.")

    except Exception as e:
        print(f"IMPORT ERROR: {e}")
        sys.exit(1)
    print("Imports OK.")

def test_payout_logic():
    print("Testing Payout Logic Config...")
    from backend.odds_service import payout_logic
    from backend import config
    
    # Check if constants are imported correctly (by checking if they exist in the module namespace)
    # We can't easily check the value if it's imported as `from config import HOUSE_EDGE` 
    # but we can check if payout_logic.HOUSE_EDGE == config.HOUSE_EDGE
    if payout_logic.HOUSE_EDGE != config.HOUSE_EDGE:
        print(f"ERROR: Payout logic HOUSE_EDGE ({payout_logic.HOUSE_EDGE}) != Config ({config.HOUSE_EDGE})")
        sys.exit(1)
    print("Payout logic config OK.")

if __name__ == "__main__":
    test_imports()
    test_payout_logic()
    print("Verification script finished successfully.")
