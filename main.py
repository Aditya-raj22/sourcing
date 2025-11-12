"""
AI-Driven Outreach Engine - Main Application

FastAPI backend for managing email outreach campaigns with AI enrichment.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from src.database import engine, Base
from src.config import config
from src.api import contacts, drafts, campaigns, replies

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info("Starting AI-Driven Outreach Engine...")

    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")

    # Validate configuration
    if not config.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set - AI features will not work")

    logger.info("Application started successfully")

    yield

    # Shutdown
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="AI-Driven Outreach Engine",
    description="Intelligent email outreach automation with AI enrichment and clustering",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(contacts.router)
app.include_router(drafts.router)
app.include_router(campaigns.router)
app.include_router(replies.router)


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "AI-Driven Outreach Engine API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "database": "connected",
        "openai": "configured" if config.OPENAI_API_KEY else "not configured"
    }


@app.get("/api/config")
def get_config():
    """Get public configuration."""
    return {
        "daily_budget_limit": config.DAILY_BUDGET_LIMIT,
        "gmail_daily_send_limit": config.GMAIL_DAILY_SEND_LIMIT,
        "max_spam_score": config.MAX_SPAM_SCORE,
        "respect_business_hours": config.RESPECT_BUSINESS_HOURS,
        "openai_model_gpt": config.OPENAI_MODEL_GPT,
        "openai_model_embedding": config.OPENAI_MODEL_EMBEDDING
    }


if __name__ == "__main__":
    import uvicorn

    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload during development
        log_level="info"
    )
