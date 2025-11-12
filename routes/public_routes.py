from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime

from database import get_db
from models.PublicRoute import PublicRoute
from models.PublicRouteStop import PublicRouteStop
from models.RouteLike import RouteLike
from models.RouteSave import RouteSave
from models.Trip import Trip
from models.POI import POI
from models.Follow import Follow
from schemas import (
    PublicRouteCreate,
    PublicRouteRead,
    PublicRouteUpdate,
    PublicRouteStopRead,
    RouteLikeCreate,
    RouteLikeRead,
    RouteSaveCreate,
    RouteSaveRead,
)

router = APIRouter(prefix="/public-routes", tags=["Public Routes"])


def _add_author_username(route: PublicRoute) -> PublicRouteRead:
    """Helper to convert PublicRoute to PublicRouteRead with author_username"""
    # Get author username and profile image
    author_username = route.author.username if route.author else None
    author_profile_image_url = route.author.profile_image_url if route.author else None
    
    # Convert to dict, excluding SQLAlchemy internal attributes and relationships
    route_dict = {}
    for key, value in route.__dict__.items():
        if not key.startswith('_') and key != 'author':  # Exclude author relationship
            route_dict[key] = value
    
    # Add author_username and profile image
    route_dict['author_username'] = author_username
    route_dict['author_profile_image_url'] = author_profile_image_url
    
    # Convert stops to list of dicts if present
    if hasattr(route, 'stops') and route.stops:
        route_dict['stops'] = [
            PublicRouteStopRead(
                id=stop.id,
                route_id=stop.route_id,
                order_index=stop.order_index,
                name=stop.name,
                description=stop.description,
                lat=stop.lat,
                lng=stop.lng,
                address=stop.address,
                place_name=stop.place_name,
                duration_minutes=stop.duration_minutes,
                estimated_cost=stop.estimated_cost,
                photos=stop.photos,
            )
            for stop in route.stops
        ]
    else:
        route_dict['stops'] = []
    
    return PublicRouteRead(**route_dict)


@router.post("/publish", response_model=PublicRouteRead, status_code=201)
def publish_trip_as_route(
    trip_id: int,
    user_id: str,  # In production, get this from auth token
    db: Session = Depends(get_db)
):
    """
    Publish a trip as a public route (snapshot).
    Creates a copy of the trip and its POIs.
    """
    # Verify trip exists and user is owner
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    if trip.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to publish this trip")
    
    # Get all POIs ordered by scheduled_at
    pois = db.query(POI).filter(
        POI.trip_id == trip_id
    ).order_by(POI.scheduled_at.asc()).all()
    
    if not pois:
        raise HTTPException(status_code=400, detail="Cannot publish trip without POIs")
    
    # Calculate totals
    total_cost = sum(poi.estimated_cost or 0 for poi in pois)
    total_duration = sum(poi.duration_minutes or 0 for poi in pois) / 60.0  # Convert to hours
    
    # Create public route
    new_route = PublicRoute(
        original_trip_id=trip_id,
        author_id=user_id,
        title=trip.title,
        description=trip.description,
        estimated_total_cost=total_cost if total_cost > 0 else None,
        total_duration_hours=total_duration if total_duration > 0 else None,
        city=trip.city,
        country=trip.country,
        center_lat=trip.center_lat,
        center_lng=trip.center_lng,
        is_published=True,
        published_at=datetime.utcnow(),
    )
    
    db.add(new_route)
    db.flush()  # Get the route ID
    
    # Create stops from POIs
    for idx, poi in enumerate(pois):
        stop = PublicRouteStop(
            route_id=new_route.id,
            order_index=idx,
            name=poi.name,
            description=poi.notes,
            lat=poi.lat,
            lng=poi.lng,
            address=poi.address,
            place_name=poi.place_name,
            duration_minutes=poi.duration_minutes,
            estimated_cost=poi.estimated_cost,
        )
        db.add(stop)
    
    db.commit()
    db.refresh(new_route)
    # Load author relationship
    db.refresh(new_route, ['author'])
    
    return _add_author_username(new_route)


@router.get("/feed", response_model=List[PublicRouteRead])
def get_public_routes_feed(
    skip: int = 0,
    limit: int = 20,
    city: str = None,
    country: str = None,
    db: Session = Depends(get_db)
):
    """
    Get feed of published public routes.
    Can filter by city or country.
    """
    query = db.query(PublicRoute).filter(PublicRoute.is_published == True)
    
    if city:
        query = query.filter(PublicRoute.city.ilike(f"%{city}%"))
    
    if country:
        query = query.filter(PublicRoute.country.ilike(f"%{country}%"))
    
    routes = query.options(joinedload(PublicRoute.author)).order_by(desc(PublicRoute.published_at)).offset(skip).limit(limit).all()
    
    # Add author_username to each route
    return [_add_author_username(route) for route in routes]


@router.get("/feed/personalized", response_model=List[PublicRouteRead])
def get_personalized_feed(
    user_id: str,  # In production, get this from auth token
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get personalized feed of public routes from users that the current user follows.
    Returns empty list if user is not following anyone (no fallback to general feed).
    """
    # Get list of user IDs that the current user is following
    following = db.query(Follow).filter(Follow.follower_id == user_id).all()
    following_ids = [f.following_id for f in following]
    
    if not following_ids:
        # If not following anyone, return empty list (no fallback)
        return []
    
    # Get routes from followed users only
    routes = db.query(PublicRoute).options(joinedload(PublicRoute.author)).filter(
        PublicRoute.is_published == True,
        PublicRoute.author_id.in_(following_ids)
    ).order_by(desc(PublicRoute.published_at)).offset(skip).limit(limit).all()
    
    # Add author_username to each route
    return [_add_author_username(route) for route in routes]


@router.get("/{route_id}", response_model=PublicRouteRead)
def get_public_route(route_id: int, db: Session = Depends(get_db)):
    """
    Get a specific public route by ID.
    Increments view count.
    """
    route = db.query(PublicRoute).options(joinedload(PublicRoute.author)).filter(PublicRoute.id == route_id).first()
    
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    # Increment views
    route.views_count += 1
    db.commit()
    db.refresh(route)
    
    return _add_author_username(route)


@router.patch("/{route_id}", response_model=PublicRouteRead)
def update_public_route(
    route_id: int,
    route_update: PublicRouteUpdate,
    user_id: str,  # In production, get this from auth token
    db: Session = Depends(get_db)
):
    """
    Update a public route (only author can update).
    """
    route = db.query(PublicRoute).options(joinedload(PublicRoute.author)).filter(PublicRoute.id == route_id).first()
    
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    if route.author_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this route")
    
    # Update fields
    update_data = route_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(route, field, value)
    
    db.commit()
    db.refresh(route)
    
    return _add_author_username(route)


@router.delete("/{route_id}", status_code=204)
def delete_public_route(
    route_id: int,
    user_id: str,  # In production, get this from auth token
    db: Session = Depends(get_db)
):
    """
    Delete a public route (only author can delete).
    """
    route = db.query(PublicRoute).filter(PublicRoute.id == route_id).first()
    
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    if route.author_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this route")
    
    db.delete(route)
    db.commit()
    
    return None


# ---------- Likes ----------

@router.post("/{route_id}/like", response_model=RouteLikeRead, status_code=201)
def like_route(
    route_id: int,
    user_id: str,  # In production, get this from auth token
    db: Session = Depends(get_db)
):
    """
    Like a public route.
    """
    # Verify route exists
    route = db.query(PublicRoute).filter(PublicRoute.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    # Check if already liked
    existing = db.query(RouteLike).filter(
        RouteLike.route_id == route_id,
        RouteLike.user_id == user_id
    ).first()
    
    if existing:
        return existing  # Already liked, return existing
    
    # Create like
    like = RouteLike(route_id=route_id, user_id=user_id)
    db.add(like)
    
    # Increment likes count
    route.likes_count += 1
    
    db.commit()
    db.refresh(like)
    
    return like


@router.delete("/{route_id}/like", status_code=204)
def unlike_route(
    route_id: int,
    user_id: str,  # In production, get this from auth token
    db: Session = Depends(get_db)
):
    """
    Remove like from a public route.
    """
    like = db.query(RouteLike).filter(
        RouteLike.route_id == route_id,
        RouteLike.user_id == user_id
    ).first()
    
    if not like:
        raise HTTPException(status_code=404, detail="Like not found")
    
    # Decrement likes count
    route = db.query(PublicRoute).filter(PublicRoute.id == route_id).first()
    if route:
        route.likes_count = max(0, route.likes_count - 1)
    
    db.delete(like)
    db.commit()
    
    return None


@router.get("/{route_id}/is-liked")
def check_if_liked(
    route_id: int,
    user_id: str,  # In production, get this from auth token
    db: Session = Depends(get_db)
):
    """
    Check if user has liked this route.
    """
    like = db.query(RouteLike).filter(
        RouteLike.route_id == route_id,
        RouteLike.user_id == user_id
    ).first()
    
    return {"is_liked": like is not None}


# ---------- Saves ----------

@router.post("/{route_id}/save", response_model=RouteSaveRead, status_code=201)
def save_route(
    route_id: int,
    user_id: str,  # In production, get this from auth token
    db: Session = Depends(get_db)
):
    """
    Save a public route for later.
    """
    # Verify route exists
    route = db.query(PublicRoute).filter(PublicRoute.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    # Check if already saved
    existing = db.query(RouteSave).filter(
        RouteSave.route_id == route_id,
        RouteSave.user_id == user_id
    ).first()
    
    if existing:
        return existing  # Already saved
    
    # Create save
    save = RouteSave(route_id=route_id, user_id=user_id)
    db.add(save)
    
    # Increment saves count
    route.saves_count += 1
    
    db.commit()
    db.refresh(save)
    
    return save


@router.delete("/{route_id}/save", status_code=204)
def unsave_route(
    route_id: int,
    user_id: str,  # In production, get this from auth token
    db: Session = Depends(get_db)
):
    """
    Remove saved route.
    """
    save = db.query(RouteSave).filter(
        RouteSave.route_id == route_id,
        RouteSave.user_id == user_id
    ).first()
    
    if not save:
        raise HTTPException(status_code=404, detail="Save not found")
    
    # Decrement saves count
    route = db.query(PublicRoute).filter(PublicRoute.id == route_id).first()
    if route:
        route.saves_count = max(0, route.saves_count - 1)
    
    db.delete(save)
    db.commit()
    
    return None


@router.get("/{route_id}/is-saved")
def check_if_saved(
    route_id: int,
    user_id: str,  # In production, get this from auth token
    db: Session = Depends(get_db)
):
    """
    Check if user has saved this route.
    """
    save = db.query(RouteSave).filter(
        RouteSave.route_id == route_id,
        RouteSave.user_id == user_id
    ).first()
    
    return {"is_saved": save is not None}


@router.get("/user/{user_id}/saved", response_model=List[PublicRouteRead])
def get_user_saved_routes(
    user_id: str,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get all routes saved by a user.
    """
    saves = db.query(RouteSave).filter(
        RouteSave.user_id == user_id
    ).order_by(desc(RouteSave.created_at)).offset(skip).limit(limit).all()
    
    route_ids = [save.route_id for save in saves]
    routes = db.query(PublicRoute).options(joinedload(PublicRoute.author)).filter(PublicRoute.id.in_(route_ids)).all()
    
    return [_add_author_username(route) for route in routes]


@router.get("/user/{user_id}/routes", response_model=List[PublicRouteRead])
def get_user_public_routes(
    user_id: str,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get all public routes published by a specific user.
    """
    routes = db.query(PublicRoute).options(joinedload(PublicRoute.author)).filter(
        PublicRoute.author_id == user_id,
        PublicRoute.is_published == True
    ).order_by(desc(PublicRoute.published_at)).offset(skip).limit(limit).all()
    
    return [_add_author_username(route) for route in routes]

