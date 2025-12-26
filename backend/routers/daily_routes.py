from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from backend.auth import get_current_user
from backend.models import User
from backend.odds_service.db import get_session

router = APIRouter(
    prefix="/daily",
    tags=["daily"],
    responses={404: {"description": "Not found"}},
)


@router.get("/status")
def get_daily_status(
    current_user: User = Depends(get_current_user),
):
    """
    Check if the user can claim daily credits.
    Returns: {"status": "AVAILABLE" | "CLAIMED"}
    """
    today = date.today()
    if current_user.last_daily_claim_date is None or current_user.last_daily_claim_date < today:
        return {"status": "AVAILABLE"}
    return {"status": "CLAIMED"}


@router.post("/claim")
def claim_daily_credits(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Claim daily credits if available.
    Adds credits (e.g. 100) and updates last_daily_claim_date.
    """
    today = date.today()

    # Re-fetch user to ensure we lock/update properly in this session
    # Although get_current_user provides a user object, let's attach to session explicitly if needed
    # Standard pattern: user is already detached or from another session?
    # Usually in FastAPI deps, we might need to merge or just rely on session.get
    
    # Safe approach: update the user from this session using row locking
    stmt = select(User).where(User.id == current_user.id).with_for_update()
    user_in_db = session.exec(stmt).one()
    
    if user_in_db.last_daily_claim_date and user_in_db.last_daily_claim_date >= today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Daily credits already claimed today.",
        )

    from backend.config import DAILY_CLAIM_AMOUNT
    user_in_db.credits_balance += DAILY_CLAIM_AMOUNT
    user_in_db.last_daily_claim_date = today
    
    session.add(user_in_db)
    session.commit()
    session.refresh(user_in_db)

    return {
        "message": "Daily credits claimed successfully",
        "added_credits": DAILY_CLAIM_AMOUNT,
        "new_balance": user_in_db.credits_balance,
        "status": "CLAIMED",
    }
