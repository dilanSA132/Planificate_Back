from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from models.User import User
from models.Follow import Follow
from schemas import UserWrite, UserRead, UserUpdate, UserProfileRead, FCMTokenUpdate
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
        or_(User.firebase_uid == payload.firebase_uid, User.username == payload.username, User.email == payload.email)
    ).first()
    if exists:
        raise HTTPException(status_code=409, detail="UID, username o email ya existen")

    new_user = User(
        firebase_uid=payload.firebase_uid,
        username=payload.username,
        email=payload.email,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.get("/", response_model=List[UserRead])
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: str, db: Session = Depends(get_db)):
    """
    Get a user by ID.
    """
    user = db.query(User).filter(User.firebase_uid == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/{user_id}/profile", response_model=UserProfileRead)
def get_user_profile(
    user_id: str,
    current_user_id: Optional[str] = None,  # In production, get from auth token
    db: Session = Depends(get_db)
):
    """
    Get user profile with follow status.
    """
    user = db.query(User).filter(User.firebase_uid == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check follow status if current_user_id is provided
    is_following = None
    is_followed_by = None
    
    if current_user_id:
        # Check if current user follows this user
        follow = db.query(Follow).filter(
            Follow.follower_id == current_user_id,
            Follow.following_id == user_id
        ).first()
        is_following = follow is not None
        
        # Check if this user follows current user
        reverse_follow = db.query(Follow).filter(
            Follow.follower_id == user_id,
            Follow.following_id == current_user_id
        ).first()
        is_followed_by = reverse_follow is not None
    
    # Convert to dict and add follow status
    profile_dict = {
        "firebase_uid": user.firebase_uid,
        "username": user.username,
        "email": user.email,
        "bio": user.bio,
        "profile_image_url": user.profile_image_url,
        "followers_count": user.followers_count,
        "following_count": user.following_count,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "is_following": is_following,
        "is_followed_by": is_followed_by,
    }
    
    return UserProfileRead(**profile_dict)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: str,
    user_update: UserUpdate,
    db: Session = Depends(get_db)
):
    """
    Update user profile.
    """
    user = db.query(User).filter(User.firebase_uid == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = user_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)
    
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}/fcm-token", status_code=status.HTTP_200_OK)
def update_fcm_token(
    user_id: str,
    payload: FCMTokenUpdate,
    db: Session = Depends(get_db)
):
    """Actualizar el token FCM de un usuario"""
    user = db.query(User).filter(User.firebase_uid == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    user.fcm_token = payload.fcm_token
    db.commit()
    db.refresh(user)
    
    return {"message": "Token FCM actualizado correctamente"}


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_user(firebase_uid: str, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.firebase_uid == firebase_uid).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    db.delete(u)
    db.commit()
