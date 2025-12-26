from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User
from backend.auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.execute(select(User).where(User.username == req.username)).scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")
    user = User(username=req.username, password_hash=hash_password(req.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.username == req.username)).scalars().first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(access_token=token)


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "credits_balance": user.credits_balance}
