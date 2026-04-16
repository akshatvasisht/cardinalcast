from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlmodel import Session, select, func

from backend.models import User
from backend.database import get_db as get_session
from backend.auth import get_current_user_optional

router = APIRouter(
    prefix="/leaderboard",
    tags=["leaderboard"],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
def get_leaderboard(
    response: Response,
    limit: int = Query(default=10, le=50),
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Get top users by credits balance.
    Returns {top: [...], current_user: {...} | null}.
    current_user is included only when authenticated and ranked outside the top N.
    """
    # Cache for 30 seconds — leaderboard changes only when wagers resolve.
    # Use private so a CDN does not serve one user's "(you)" row to another.
    response.headers["Cache-Control"] = "private, max-age=30"
    stmt = select(User).order_by(User.credits_balance.desc()).limit(limit)
    users = session.exec(stmt).all()

    top = []
    current_user_in_top = False
    for rank, user in enumerate(users, start=1):
        top.append({
            "username": user.username,
            "credits_balance": user.credits_balance,
            "rank": rank,
        })
        if current_user and user.id == current_user.id:
            current_user_in_top = True

    # If the authenticated user isn't in the top N, compute their rank
    current_user_entry = None
    if current_user and not current_user_in_top:
        rank_stmt = select(func.count()).where(
            User.credits_balance > current_user.credits_balance
        )
        users_above = session.exec(rank_stmt).one()
        current_user_entry = {
            "username": current_user.username,
            "credits_balance": current_user.credits_balance,
            "rank": users_above + 1,
        }

    return {"top": top, "current_user": current_user_entry}
