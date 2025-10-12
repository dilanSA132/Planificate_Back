from fastapi import FastAPI
from database import Base, engine
from routes import users

Base.metadata.create_all(bind=engine)

app = FastAPI(title="FastAPI Usuarios Simples")

app.include_router(users.router)
