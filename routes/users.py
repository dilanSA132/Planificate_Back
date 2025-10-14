from typing import List
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from models.User import User           
from schemas import UserWrite, UserRead  
from database import get_db
from utils import get_password_hash

router = APIRouter(prefix="/users", tags=["Users"])


@router.post(
    "/",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def create_user(payload: UserWrite, db: Session = Depends(get_db)):
    exists = db.query(User).filter(
        or_(User.username == payload.username, User.email == payload.email)
    ).first()
    if exists:
        raise HTTPException(status_code=409, detail="Username o email ya existen")

    hashed_password = get_password_hash(payload.password)
    new_user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hashed_password,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.get("/", response_model=List[UserRead])
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    db.delete(u)
    db.commit()
