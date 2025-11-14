from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
from models.TripInvitation import TripInvitation, InvitationStatus
from models.TripMember import TripMember
from schemas import TripInvitationRead

router = APIRouter(prefix="/invitations", tags=["User Invitations"])
from database import get_db


def _invitation_to_read(invitation: TripInvitation) -> dict:
    """Helper to convert TripInvitation to TripInvitationRead dict"""
    result = {
        "id": invitation.id,
        "trip_id": invitation.trip_id,
        "invited_user_id": invitation.invited_user_id,
        "invited_by_id": invitation.invited_by_id,
        "message": invitation.message,
        "status": invitation.status.value if isinstance(invitation.status, InvitationStatus) else invitation.status,
        "created_at": invitation.created_at,
        "responded_at": invitation.responded_at,
    }
    
    # Include trip info if available
    if invitation.trip:
        result["trip"] = {
            "id": invitation.trip.id,
            "title": invitation.trip.title,
            "description": invitation.trip.description,
            "start_date": invitation.trip.start_date,
            "end_date": invitation.trip.end_date,
            "city": invitation.trip.city,
            "country": invitation.trip.country,
            "is_public": invitation.trip.is_public,
            "owner_id": invitation.trip.owner_id,
            "created_at": invitation.trip.created_at,
            "updated_at": invitation.trip.updated_at,
        }
    
    # Include invited_by user info if available
    if invitation.invited_by:
        result["invited_by"] = {
            "firebase_uid": invitation.invited_by.firebase_uid,
            "username": invitation.invited_by.username,
            "email": invitation.invited_by.email,
            "profile_image_url": invitation.invited_by.profile_image_url,
        }
    
    # Include invited_user info if available
    if invitation.invited_user:
        result["invited_user"] = {
            "firebase_uid": invitation.invited_user.firebase_uid,
            "username": invitation.invited_user.username,
            "email": invitation.invited_user.email,
            "profile_image_url": invitation.invited_user.profile_image_url,
        }
    
    return result


@router.get("/user/{user_id}", response_model=List[dict])
def list_user_invitations(
    user_id: str,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Listar todas las invitaciones de un usuario"""
    query = db.query(TripInvitation).options(
        joinedload(TripInvitation.trip),
        joinedload(TripInvitation.invited_by),
        joinedload(TripInvitation.invited_user)
    ).filter(
        TripInvitation.invited_user_id == user_id
    )
    
    if status_filter:
        try:
            status_enum = InvitationStatus(status_filter)
            query = query.filter(TripInvitation.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Status inválido: {status_filter}")
    
    invitations = query.all()
    return [_invitation_to_read(inv) for inv in invitations]


@router.post("/{invitation_id}/accept", status_code=status.HTTP_200_OK)
def accept_invitation(
    invitation_id: int,
    user_id: str = Query(..., description="ID del usuario que acepta la invitación"),  # En producción, obtener del token de autenticación
    db: Session = Depends(get_db)
):
    """Aceptar una invitación"""
    invitation = db.query(TripInvitation).filter(
        TripInvitation.id == invitation_id,
        TripInvitation.invited_user_id == user_id
    ).first()
    
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitación no encontrada")
    
    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(status_code=400, detail="Esta invitación ya fue respondida")
    
    # Actualizar el estado de la invitación
    invitation.status = InvitationStatus.ACCEPTED
    invitation.responded_at = datetime.utcnow()
    
    # Crear el miembro del viaje
    member = TripMember(
        trip_id=invitation.trip_id,
        user_id=invitation.invited_user_id,
        role="collaborator"
    )
    db.add(member)
    db.commit()
    db.refresh(invitation)
    
    # Load relationships
    db.refresh(invitation, ['trip', 'invited_by', 'invited_user'])
    
    return {"message": "Invitación aceptada", "invitation": _invitation_to_read(invitation)}


@router.post("/{invitation_id}/reject", status_code=status.HTTP_200_OK)
def reject_invitation(
    invitation_id: int,
    user_id: str = Query(..., description="ID del usuario que rechaza la invitación"),  # En producción, obtener del token de autenticación
    db: Session = Depends(get_db)
):
    """Rechazar una invitación"""
    invitation = db.query(TripInvitation).filter(
        TripInvitation.id == invitation_id,
        TripInvitation.invited_user_id == user_id
    ).first()
    
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitación no encontrada")
    
    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(status_code=400, detail="Esta invitación ya fue respondida")
    
    # Actualizar el estado de la invitación
    invitation.status = InvitationStatus.REJECTED
    invitation.responded_at = datetime.utcnow()
    
    db.commit()
    db.refresh(invitation)
    
    # Load relationships
    db.refresh(invitation, ['trip', 'invited_by', 'invited_user'])
    
    return {"message": "Invitación rechazada", "invitation": _invitation_to_read(invitation)}

