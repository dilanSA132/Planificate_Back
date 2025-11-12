from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models.Follow import Follow
from models.User import User
from schemas import FollowCreate, FollowRead

router = APIRouter(prefix="/follows", tags=["Follows"])


@router.post("/{follower_id}/follow/{following_id}", response_model=FollowRead, status_code=201)
def follow_user(
    follower_id: str,
    following_id: str,
    db: Session = Depends(get_db)
):
    """
    Follow a user.
    """
    if follower_id == following_id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    
    # Verify both users exist
    follower = db.query(User).filter(User.firebase_uid == follower_id).first()
    following = db.query(User).filter(User.firebase_uid == following_id).first()
    
    if not follower:
        raise HTTPException(status_code=404, detail="Follower user not found")
    if not following:
        raise HTTPException(status_code=404, detail="Following user not found")
    
    # Check if already following
    existing_follow = db.query(Follow).filter(
        Follow.follower_id == follower_id,
        Follow.following_id == following_id
    ).first()
    
    if existing_follow:
        raise HTTPException(status_code=409, detail="Already following this user")
    
    # Create follow relationship
    new_follow = Follow(
        follower_id=follower_id,
        following_id=following_id
    )
    db.add(new_follow)
    
    # Update counters
    follower.following_count += 1
    following.followers_count += 1
    
    db.commit()
    db.refresh(new_follow)
    return new_follow


@router.delete("/{follower_id}/unfollow/{following_id}", status_code=204)
def unfollow_user(
    follower_id: str,
    following_id: str,
    db: Session = Depends(get_db)
):
    """
    Unfollow a user.
    """
    follow = db.query(Follow).filter(
        Follow.follower_id == follower_id,
        Follow.following_id == following_id
    ).first()
    
    if not follow:
        raise HTTPException(status_code=404, detail="Follow relationship not found")
    
    # Get users to update counters
    follower = db.query(User).filter(User.firebase_uid == follower_id).first()
    following = db.query(User).filter(User.firebase_uid == following_id).first()
    
    if follower and following:
        follower.following_count = max(0, follower.following_count - 1)
        following.followers_count = max(0, following.followers_count - 1)
    
    db.delete(follow)
    db.commit()
    return {"message": "Unfollowed successfully"}


@router.get("/{user_id}/following", response_model=List[FollowRead])
def get_following(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get list of users that a user is following.
    """
    follows = db.query(Follow).filter(Follow.follower_id == user_id).all()
    return follows


@router.get("/{user_id}/followers", response_model=List[FollowRead])
def get_followers(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get list of users that follow a user.
    """
    follows = db.query(Follow).filter(Follow.following_id == user_id).all()
    return follows


@router.get("/{follower_id}/is-following/{following_id}", response_model=bool)
def is_following(
    follower_id: str,
    following_id: str,
    db: Session = Depends(get_db)
):
    """
    Check if a user is following another user.
    """
    follow = db.query(Follow).filter(
        Follow.follower_id == follower_id,
        Follow.following_id == following_id
    ).first()
    return follow is not None

