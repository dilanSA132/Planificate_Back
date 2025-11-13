from fastapi import FastAPI
from database import Base, engine

from routes import (
    users,
    trips,
    trip_members,
    pois,
    itinerary,
    chat_messages,
    poi_cost_estimates,
    osm_services,
    public_routes,
    follows,
)

Base.metadata.create_all(bind=engine)

# Ensure new columns exist in the database for running instances (safe startup migration)
from sqlalchemy import text
try:
    with engine.begin() as conn:
        # Trip location fields
        conn.execute(text("ALTER TABLE trips ADD COLUMN IF NOT EXISTS center_lat DOUBLE PRECISION;"))
        conn.execute(text("ALTER TABLE trips ADD COLUMN IF NOT EXISTS center_lng DOUBLE PRECISION;"))
        conn.execute(text("ALTER TABLE trips ADD COLUMN IF NOT EXISTS city VARCHAR(100);"))
        conn.execute(text("ALTER TABLE trips ADD COLUMN IF NOT EXISTS country VARCHAR(100);"))
        conn.execute(text("ALTER TABLE trips ADD COLUMN IF NOT EXISTS address VARCHAR(250);"))
        
        # POI location fields
        conn.execute(text("ALTER TABLE pois ADD COLUMN IF NOT EXISTS address VARCHAR(250);"))
        conn.execute(text("ALTER TABLE pois ADD COLUMN IF NOT EXISTS city VARCHAR(100);"))
        conn.execute(text("ALTER TABLE pois ADD COLUMN IF NOT EXISTS country VARCHAR(100);"))
        conn.execute(text("ALTER TABLE pois ADD COLUMN IF NOT EXISTS place_name VARCHAR(200);"))
        
        # POI scheduled date
        conn.execute(text("ALTER TABLE pois ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMP WITH TIME ZONE;"))
        
        # POI duration and cost
        conn.execute(text("ALTER TABLE pois ADD COLUMN IF NOT EXISTS duration_minutes INTEGER;"))
        conn.execute(text("ALTER TABLE pois ADD COLUMN IF NOT EXISTS estimated_cost DOUBLE PRECISION;"))
        
        # Trip social features
        conn.execute(text("ALTER TABLE trips ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT FALSE;"))
        
        # User social features
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS bio TEXT;"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_image_url VARCHAR(500);"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS followers_count INTEGER DEFAULT 0;"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS following_count INTEGER DEFAULT 0;"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();"))
        
        # ItineraryItem name field (for activities without POI)
        conn.execute(text("ALTER TABLE itinerary_items ADD COLUMN IF NOT EXISTS name VARCHAR(150);"))
except Exception:
    import sys, traceback
    traceback.print_exc()
    print("Warning: automatic location field migrations failed; you may need to run DB migrations manually.", file=sys.stderr)

app = FastAPI(title="Travel API (Users, Trips, POIs, Itinerary, Chat, Estimates)")

# setup file logger for API failures
from logger_utils import setup_api_logger
api_logger = setup_api_logger()


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    # log request info and stacktrace
    try:
        body = await request.body()
    except Exception:
        body = b""
    import traceback
    tb = traceback.format_exc()
    api_logger.error("Unhandled exception on %s %s | body=%s | error=%s\n%s",
                     request.method, request.url.path, body.decode('utf-8', errors='replace'), str(exc), tb)
    # re-raise as HTTPException-like response
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


from fastapi import HTTPException


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    try:
        body = await request.body()
    except Exception:
        body = b""
    api_logger.warning("HTTPException on %s %s | status=%s | body=%s | detail=%s",
                       request.method, request.url.path, exc.status_code,
                       body.decode('utf-8', errors='replace'), str(exc.detail))
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(users.router)
app.include_router(trips.router)
app.include_router(trip_members.router)
app.include_router(pois.router)
app.include_router(pois.router2)
app.include_router(itinerary.router)
app.include_router(chat_messages.router)
app.include_router(poi_cost_estimates.router)
app.include_router(osm_services.router)
app.include_router(public_routes.router)
app.include_router(follows.router)
