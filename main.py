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
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Travel API (Users, Trips, POIs, Itinerary, Chat, Estimates)")

app.include_router(users.router)
app.include_router(trips.router)
app.include_router(trip_members.router)
app.include_router(pois.router)
app.include_router(itinerary.router)
app.include_router(chat_messages.router)
app.include_router(poi_cost_estimates.router)
