from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.v1 import textbook_router
from src.db.session import engine, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    await init_db()
    yield
    # Dispose engine connections on shutdown
    await engine.dispose()


app = FastAPI(
    title="TextbookMind API",
    description="Academic RAG system for intelligent textbook learning.",
    version="0.1.0",
    lifespan=lifespan,
)

# Register API v1 Routers
app.include_router(textbook_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": "TextbookMind API"}
