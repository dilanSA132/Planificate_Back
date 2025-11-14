import firebase_admin
from firebase_admin import credentials, messaging
import os
from typing import Optional

# Inicializar Firebase Admin (solo una vez)
_initialized = False

def initialize_firebase_admin():
    """Inicializar Firebase Admin SDK"""
    global _initialized
    if not _initialized:
        try:
            # Ruta al archivo de credenciales
            cred_path = os.getenv(
                "FIREBASE_CREDENTIALS_PATH",
                os.path.join(os.path.dirname(__file__), "..", "serviceAccountKey.json")
            )
            
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                _initialized = True
                print(f"✅ Firebase Admin inicializado con: {cred_path}")
            else:
                print(f"⚠️ Archivo de credenciales no encontrado: {cred_path}")
                print("   Las notificaciones push no funcionarán sin este archivo")
                # Intentar usar variable de entorno (para producción)
                if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                    firebase_admin.initialize_app()
                    _initialized = True
                    print("✅ Firebase Admin inicializado desde variable de entorno")
                else:
                    _initialized = False
        except Exception as e:
            print(f"❌ Error inicializando Firebase Admin: {e}")
            _initialized = False

def send_notification(
    fcm_token: str,
    title: str,
    body: str,
    data: Optional[dict] = None
) -> bool:
    """Enviar una notificación push a un dispositivo"""
    initialize_firebase_admin()
    
    if not _initialized or not fcm_token:
        if not _initialized:
            print("⚠️ Firebase Admin no está inicializado")
        return False
    
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            token=fcm_token,
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        badge=1,
                        sound="default",
                    ),
                ),
            ),
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    sound="default",
                    channel_id="high_importance_channel",
                ),
            ),
        )
        
        response = messaging.send(message)
        print(f"✅ Notificación enviada: {response}")
        return True
    except Exception as e:
        print(f"❌ Error enviando notificación: {e}")
        return False

def send_notification_to_multiple(
    fcm_tokens: list[str],
    title: str,
    body: str,
    data: Optional[dict] = None
) -> dict:
    """Enviar notificación a múltiples dispositivos"""
    initialize_firebase_admin()
    
    if not _initialized or not fcm_tokens:
        return {"success": 0, "failure": len(fcm_tokens) if fcm_tokens else 0}
    
    try:
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            tokens=fcm_tokens,
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        badge=1,
                        sound="default",
                    ),
                ),
            ),
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    sound="default",
                    channel_id="high_importance_channel",
                ),
            ),
        )
        
        response = messaging.send_multicast(message)
        return {
            "success": response.success_count,
            "failure": response.failure_count,
        }
    except Exception as e:
        print(f"❌ Error enviando notificaciones múltiples: {e}")
        return {"success": 0, "failure": len(fcm_tokens)}

