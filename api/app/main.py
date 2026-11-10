"""FastAPI application factory and middleware."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import admin, auth, health, suggestions, votes, words

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: nothing to do for Phase 0
    yield
    # Shutdown: nothing to do for Phase 0


app = FastAPI(
    title="Lumi API",
    version="0.1.0",
    description="Backend for the Lumi dictionary — a public dictionary of the Taita language.",
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
app.include_router(words.router, prefix="/api")
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(suggestions.router, prefix="/api", tags=["suggestions"])
app.include_router(votes.router, prefix="/api", tags=["votes"])
app.include_router(admin.router, prefix="/api", tags=["admin"])


@app.get("/")
async def root():
    """Root endpoint — basic API info."""
    return {
        "name": "Lumi API",
        "version": "0.1.0",
        "docs": "/docs",
    }
