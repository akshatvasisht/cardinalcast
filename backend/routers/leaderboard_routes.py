from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func

from backend.models import User
from backend.odds_service.db import get_session

router = APIRouter(
    prefix="/leaderboard",
    tags=["leaderboard"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=List[dict])
def get_leaderboard(
    limit: int = 50,
    session: Session = Depends(get_session),
):
    """
    Get top users by credits balance.
    Returns list of {username, credits_balance, rank}.
    """
    # Select users ordered by credits_balance desc
    stmt = select(User).order_by(User.credits_balance.desc()).limit(limit)
    users = session.exec(stmt).all()

    leaderboard = []
    for rank, user in enumerate(users, start=1):
        leaderboard.append({
            "username": user.username,
            "credits_balance": user.credits_balance,
            "rank": rank,
        })
    
    return leaderboard
