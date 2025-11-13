# API de Archivos para Mensajes del Chat

Este sistema permite subir y descargar archivos (imágenes y PDFs) asociados a mensajes del chat.

## Estructura de Directorios

```
uploads/
  messages/
    images/    # Imágenes (jpg, png, gif, webp)
    pdfs/      # Documentos PDF
    other/     # Otros tipos (reservado para futuro)
```

## Endpoints

### 1. Subir Archivo

**POST** `/files/upload`

Sube un archivo y retorna la URL para accederlo.

**Parámetros:**
- `file` (form-data): El archivo a subir
- `trip_id` (opcional): ID del viaje (para validación)
- `message_id` (opcional): ID del mensaje (para validación)

**Tipos de archivo permitidos:**
- Imágenes: `image/jpeg`, `image/jpg`, `image/png`, `image/gif`, `image/webp`
- PDFs: `application/pdf`

**Tamaño máximo:** 10 MB

**Respuesta exitosa (200):**
```json
{
  "url": "/files/messages/images/uuid.jpg",
  "filename": "uuid.jpg",
  "original_filename": "foto.jpg",
  "content_type": "image/jpeg",
  "size": 123456,
  "type": "image"
}
```

**Errores:**
- `400`: Tipo de archivo no permitido o archivo demasiado grande
- `404`: Mensaje no encontrado (si se proporciona message_id)

### 2. Obtener Archivo

**GET** `/files/messages/{file_type}/{filename}`

Descarga un archivo.

**Parámetros de ruta:**
- `file_type`: `images`, `pdfs`, o `other`
- `filename`: Nombre del archivo (UUID + extensión)

**Ejemplo:**
```
GET /files/messages/images/123e4567-e89b-12d3-a456-426614174000.jpg
```

**Respuesta:** Archivo binario con el content-type apropiado

**Errores:**
- `400`: Tipo de archivo inválido
- `404`: Archivo no encontrado

### 3. Eliminar Archivo

**DELETE** `/files/messages/{file_type}/{filename}`

Elimina un archivo del servidor.

**Parámetros de ruta:**
- `file_type`: `images`, `pdfs`, o `other`
- `filename`: Nombre del archivo

**Respuesta exitosa (200):**
```json
{
  "message": "Archivo eliminado exitosamente"
}
```

## Uso con Mensajes del Chat

### Flujo recomendado:

1. **Subir archivo:**
   ```bash
   POST /files/upload
   Content-Type: multipart/form-data
   
   file: [archivo]
   trip_id: 123
   ```

2. **Crear mensaje con archivo:**
   ```bash
   POST /trips/123/messages
   {
     "trip_id": 123,
     "user_id": "firebase_uid",
     "body": "Mira esta foto",
     "file_url": "/files/messages/images/uuid.jpg",
     "file_type": "image"
   }
   ```

3. **Obtener archivo:**
   ```bash
   GET /files/messages/images/uuid.jpg
   ```

## Modelo de Datos

El modelo `ChatMessage` ahora incluye:
- `file_url`: URL del archivo (ej: `/files/messages/images/uuid.jpg`)
- `file_type`: Tipo de archivo (`image` o `pdf`)

## Seguridad

- Validación de tipos de archivo permitidos
- Límite de tamaño (10 MB)
- Nombres de archivo únicos (UUID) para evitar colisiones
- Validación de existencia de mensaje/trip antes de asociar archivo

## Notas

- Los archivos se almacenan localmente en el servidor
- Para producción, considera migrar a un servicio de almacenamiento en la nube (S3, Firebase Storage, etc.)
- Los archivos no se eliminan automáticamente cuando se elimina un mensaje (se debe implementar lógica adicional si se requiere)

