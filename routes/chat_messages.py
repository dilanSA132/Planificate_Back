from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models.Trip import Trip
from models.User import User
from models.ChatMessage import ChatMessage
from schemas import ChatMessageWrite, ChatMessageRead
from database import get_db

router = APIRouter(prefix="/trips/{trip_id}/messages", tags=["Chat Messages"])


@router.post("/", response_model=ChatMessageRead, status_code=status.HTTP_201_CREATED)
def post_message(trip_id: int, payload: ChatMessageWrite, db: Session = Depends(get_db)):
    if payload.trip_id != trip_id:
        raise HTTPException(status_code=400, detail="trip_id en body no coincide con el path")

    if not db.query(Trip).filter(Trip.id == trip_id).first():
        raise HTTPException(status_code=404, detail="Trip no existe")

    if not db.query(User).filter(User.id == payload.user_id).first():
        raise HTTPException(status_code=404, detail="Usuario no existe")

    msg = ChatMessage(**payload.model_dump())
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


@router.get("/", response_model=List[ChatMessageRead])
def list_messages(trip_id: int, db: Session = Depends(get_db)):
    if not db.query(Trip).filter(Trip.id == trip_id).first():
        raise HTTPException(status_code=404, detail="Trip no existe")
    return db.query(ChatMessage).filter(ChatMessage.trip_id == trip_id).order_by(ChatMessage.id.asc()).all()


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(trip_id: int, message_id: int, db: Session = Depends(get_db)):
    msg = db.query(ChatMessage).filter_by(id=message_id, trip_id=trip_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")
    db.delete(msg)
    db.commit()
