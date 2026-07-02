from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from backend.core.database import engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))  # Testing DB connection
        print("✅ Successfully connected to the PostgreSQL database!")
    except Exception as e:
        print(f"❌ Failed to connect to the database: {e}")
    
    yield  
    # Shutdown Code come here (TODO)

app = FastAPI(title="ZenOps Backend", lifespan=lifespan)

@app.get("/")
async def root():
    return {"message": "ZenOps Backend is running"}