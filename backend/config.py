import os

# Database
DB_URL = os.getenv("DB_URL", "postgresql://user:password@localhost:5432/cardinalcast")

# Business Logic
DAILY_CLAIM_AMOUNT = 100
HOUSE_EDGE = 0.10
MIN_PAYOUT_MULTIPLIER = 1.01
MAX_PAYOUT_MULTIPLIER = 50.0
MAX_JACKPOT_BONUS = 0.5

# Weather & Waggers
TARGETS = ["high_temp", "avg_wind_speed", "precipitation"]
DEFAULT_LOCATION = "Madison"
