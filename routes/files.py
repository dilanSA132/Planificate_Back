"""
File upload and download endpoints for chat messages.
Supports images (jpg, png, gif, webp) and PDFs.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import Optional
import os
import uuid
from pathlib import Path
import shutil

from database import get_db
from models.Trip import Trip
from models.ChatMessage import ChatMessage

router = APIRouter(prefix="/files", tags=["Files"])

# Configuración
UPLOAD_BASE_DIR = Path("uploads")
MESSAGES_DIR = UPLOAD_BASE_DIR / "messages"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"}
ALLOWED_PDF_TYPES = {"application/pdf"}
ALLOWED_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_PDF_TYPES

# Crear directorios si no existen
MESSAGES_DIR.mkdir(parents=True, exist_ok=True)


def get_file_type(content_type: str) -> str:
    """Determina el tipo de archivo basado en content_type."""
    if content_type in ALLOWED_IMAGE_TYPES:
        return "image"
    elif content_type in ALLOWED_PDF_TYPES:
        return "pdf"
    else:
        return "unknown"


def validate_file(file: UploadFile) -> None:
    """Valida el tipo y tamaño del archivo."""
    # Si no hay content_type, intentar detectarlo desde el nombre del archivo
    content_type = file.content_type
    if not content_type and file.filename:
        ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        mime_map = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp',
            'pdf': 'application/pdf',
        }
        content_type = mime_map.get(ext)
    
    if not content_type or content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no permitido. Tipos permitidos: imágenes (jpg, png, gif, webp) y PDFs. Recibido: {content_type or 'desconocido'}"
        )


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    trip_id: Optional[int] = None,
    message_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Sube un archivo para un mensaje del chat.
    Si se proporciona trip_id y message_id, valida que el mensaje exista y pertenezca al viaje.
    """
    # Validar tipo de archivo
    validate_file(file)
    
    # Validar que el mensaje existe si se proporciona message_id
    if message_id is not None and trip_id is not None:
        message = db.query(ChatMessage).filter(
            ChatMessage.id == message_id,
            ChatMessage.trip_id == trip_id
        ).first()
        if not message:
            raise HTTPException(status_code=404, detail="Mensaje no encontrado")
    
    # Leer contenido del archivo
    content = await file.read()
    
    # Validar tamaño
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Archivo demasiado grande. Tamaño máximo: {MAX_FILE_SIZE / (1024 * 1024):.1f} MB"
        )
    
    # Generar nombre único
    file_ext = Path(file.filename).suffix.lower() or ".bin"
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    
    # Determinar subdirectorio basado en tipo
    file_type = get_file_type(file.content_type)
    if file_type == "image":
        subdir = MESSAGES_DIR / "images"
    elif file_type == "pdf":
        subdir = MESSAGES_DIR / "pdfs"
    else:
        subdir = MESSAGES_DIR / "other"
    
    subdir.mkdir(parents=True, exist_ok=True)
    file_path = subdir / unique_filename
    
    # Guardar archivo
    with open(file_path, "wb") as buffer:
        buffer.write(content)
    
    # Retornar información del archivo
    return {
        "url": f"/files/messages/{file_type}s/{unique_filename}",
        "filename": unique_filename,
        "original_filename": file.filename,
        "content_type": file.content_type,
        "size": len(content),
        "type": file_type
    }


@router.get("/messages/{file_type}/{filename}")
async def get_message_file(file_type: str, filename: str):
    """
    Obtiene un archivo de mensaje.
    file_type puede ser 'images' o 'pdfs'
    """
    # Validar tipo de archivo
    if file_type not in ["images", "pdfs", "other"]:
        raise HTTPException(status_code=400, detail="Tipo de archivo inválido")
    
    file_path = MESSAGES_DIR / file_type / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    # Determinar content-type basado en extensión
    ext = Path(filename).suffix.lower()
    content_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
    }
    content_type = content_type_map.get(ext, "application/octet-stream")
    
    return FileResponse(
        file_path,
        media_type=content_type,
        filename=filename
    )


@router.delete("/messages/{file_type}/{filename}")
async def delete_message_file(
    file_type: str,
    filename: str,
    db: Session = Depends(get_db)
):
    """
    Elimina un archivo de mensaje.
    Solo elimina el archivo físico, no actualiza la base de datos.
    """
    if file_type not in ["images", "pdfs", "other"]:
        raise HTTPException(status_code=400, detail="Tipo de archivo inválido")
    
    file_path = MESSAGES_DIR / file_type / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    try:
        os.remove(file_path)
        return {"message": "Archivo eliminado exitosamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar archivo: {str(e)}")

