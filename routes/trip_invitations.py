from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
from models.TripInvitation import TripInvitation, InvitationStatus
from models.Trip import Trip
from models.TripMember import TripMember
from models.User import User
from schemas import TripInvitationWrite, TripInvitationRead, TripRead, UserRead
from database import get_db

router = APIRouter(prefix="/trips/{trip_id}/invitations", tags=["Trip Invitations"])


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


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_invitation(
    trip_id: int,
    payload: TripInvitationWrite,
    invited_by_id: Optional[str] = Query(None),  # Query parameter opcional
    db: Session = Depends(get_db)
):
    """Crear una invitación para un viaje"""
    
    # Verificar que el viaje existe
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Viaje no encontrado")
    
    # Si no se proporciona invited_by_id, usar el owner_id del viaje
    if not invited_by_id:
        invited_by_id = trip.owner_id
    
    # Verificar que el usuario que invita es el dueño o un colaborador
    if trip.owner_id != invited_by_id:
        is_member = db.query(TripMember).filter(
            TripMember.trip_id == trip_id,
            TripMember.user_id == invited_by_id
        ).first()
        if not is_member:
            raise HTTPException(status_code=403, detail="No tienes permiso para invitar a este viaje")
    
    # Buscar el usuario por email
    invited_user = db.query(User).filter(User.email == payload.email).first()
    if not invited_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado con ese email")
    
    # Verificar que no sea el mismo usuario
    if invited_user.firebase_uid == invited_by_id:
        raise HTTPException(status_code=400, detail="No puedes invitarte a ti mismo")
    
    # Verificar que no sea ya miembro
    existing_member = db.query(TripMember).filter(
        TripMember.trip_id == trip_id,
        TripMember.user_id == invited_user.firebase_uid
    ).first()
    if existing_member:
        raise HTTPException(status_code=400, detail="Este usuario ya es miembro del viaje")
    
    # Verificar que no haya una invitación pendiente
    existing_invitation = db.query(TripInvitation).filter(
        TripInvitation.trip_id == trip_id,
        TripInvitation.invited_user_id == invited_user.firebase_uid,
        TripInvitation.status == InvitationStatus.PENDING
    ).first()
    if existing_invitation:
        raise HTTPException(status_code=400, detail="Ya existe una invitación pendiente para este usuario")
    
    # Crear la invitación
    invitation = TripInvitation(
        trip_id=trip_id,
        invited_user_id=invited_user.firebase_uid,
        invited_by_id=invited_by_id,
        message=payload.message,
        status=InvitationStatus.PENDING
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    
    # Load relationships
    db.refresh(invitation, ['trip', 'invited_by', 'invited_user'])
    
    # Enviar notificación push al usuario invitado
    try:
        from services.fcm_service import send_notification
        
        if invited_user.fcm_token:
            # Obtener información del que invita
            inviter = db.query(User).filter(User.firebase_uid == invited_by_id).first()
            inviter_name = inviter.username if inviter else "Alguien"
            
            # Enviar notificación
            send_notification(
                fcm_token=invited_user.fcm_token,
                title="Nueva invitación de viaje",
                body=f"{inviter_name} te ha invitado al viaje: {trip.title}",
                data={
                    "type": "trip_invitation",
                    "invitation_id": str(invitation.id),
                    "trip_id": str(trip_id),
                    "invited_by_id": invited_by_id,
                }
            )
    except Exception as e:
        print(f"⚠️ Error enviando notificación: {e}")
        # No fallar si la notificación no se puede enviar
    
    return _invitation_to_read(invitation)


@router.get("/", response_model=List[dict])
def list_invitations(
    trip_id: int,
    db: Session = Depends(get_db)
):
    """Listar todas las invitaciones de un viaje"""
    invitations = db.query(TripInvitation).options(
        joinedload(TripInvitation.trip),
        joinedload(TripInvitation.invited_by),
        joinedload(TripInvitation.invited_user)
    ).filter(
        TripInvitation.trip_id == trip_id
    ).all()
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


@router.delete("/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invitation(
    invitation_id: int,
    user_id: str = Query(..., description="ID del usuario que elimina la invitación"),  # En producción, obtener del token de autenticación
    db: Session = Depends(get_db)
):
    """Eliminar una invitación (solo el que la creó o el invitado)"""
    invitation = db.query(TripInvitation).filter(
        TripInvitation.id == invitation_id
    ).first()
    
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitación no encontrada")
    
    # Solo el que la creó o el invitado pueden eliminarla
    if invitation.invited_by_id != user_id and invitation.invited_user_id != user_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para eliminar esta invitación")
    
    db.delete(invitation)
    db.commit()
    
    return None

