from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from core.database import engine
from routers.server_router import router as server_router
from routers.discord_binding_router import router as binding_router, guild_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once when the application starts and shuts down."""

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("✅ Successfully connected to the PostgreSQL database!")
    except Exception as e:
        print(f"❌ Failed to connect to the database: {e}")

    yield

    # Shutdown code goes here
    print("👋 ZenOps Backend shutting down...")


app = FastAPI(
    title="ZenOps Backend",
    version="0.1.0",
    lifespan=lifespan,
)

# Register API routers
app.include_router(server_router)
app.include_router(binding_router)
app.include_router(guild_router)


@app.get("/")
async def root():
    return {
        "message": "ZenOps Backend is running"
    }