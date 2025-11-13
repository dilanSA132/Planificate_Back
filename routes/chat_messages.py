from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models.Trip import Trip
from models.User import User
from models.ChatMessage import ChatMessage
from schemas import ChatMessageWrite, ChatMessageRead
from database import get_db

router = APIRouter(prefix="/trips/{trip_id}/messages", tags=["Chat Messages"])


# =====================================================
#                 POST MENSAJE
# =====================================================
@router.post("/", response_model=ChatMessageRead, status_code=status.HTTP_201_CREATED)
def post_message(trip_id: int, payload: ChatMessageWrite, db: Session = Depends(get_db)):
    # El body debe coincidir con el trip de la URL
    if payload.trip_id != trip_id:
        raise HTTPException(status_code=400, detail="trip_id en body no coincide con el path")

    # Validamos que el trip exista
    if not db.query(Trip).filter(Trip.id == trip_id).first():
        raise HTTPException(status_code=404, detail="Trip no existe")

    # VALIDACIÓN CORRECTA DEL USUARIO
    user = db.query(User).filter(User.firebase_uid == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no existe")

    # Validar que haya al menos body o archivo
    if not payload.body.strip() and not payload.file_url:
        raise HTTPException(status_code=400, detail="El mensaje debe tener texto o un archivo adjunto")
    
    msg = ChatMessage(
        trip_id=trip_id,
        user_id=payload.user_id,
        body=payload.body or "",  # Permitir body vacío si hay archivo
        file_url=payload.file_url,
        file_type=payload.file_type,
        file_name=payload.file_name
    )

    db.add(msg)
    db.commit()
    db.refresh(msg)

    return msg


# =====================================================
#                 GET LISTA MENSAJES
# =====================================================
@router.get("/", response_model=List[ChatMessageRead])
def list_messages(trip_id: int, db: Session = Depends(get_db)):

    if not db.query(Trip).filter(Trip.id == trip_id).first():
        raise HTTPException(status_code=404, detail="Trip no existe")

    return (
        db.query(ChatMessage)
        .filter(ChatMessage.trip_id == trip_id)
        .order_by(ChatMessage.created_at.asc())   # correcto
        .all()
    )


# =====================================================
#                 DELETE MENSAJE
# =====================================================
@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(trip_id: int, message_id: int, db: Session = Depends(get_db)):
    msg = (
        db.query(ChatMessage)
        .filter(ChatMessage.id == message_id, ChatMessage.trip_id == trip_id)
        .first()
    )

    if not msg:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")

    db.delete(msg)
    db.commit()
