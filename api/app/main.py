"""FastAPI application factory and middleware."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import health

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: nothing to do for Phase 0
    yield
    # Shutdown: nothing to do for Phase 0


app = FastAPI(
    title="TaitaLumi API",
    version="0.1.0",
    description="Backend for the TaitaLumi dictionary — a public dictionary of the Taita language.",
    lifespan=lifespan,
)

# CORS — allows the Vue dev server to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint — basic API info."""
    return {
        "name": "TaitaLumi API",
        "version": "0.1.0",
        "docs": "/docs",
    }
