"""
Interview Assistant - Main FastAPI Application
Author: Mandar
Description: Entry point for the Interview Assistant backend API
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("Starting Interview Assistant API...")
    logger.info(f"Environment: {settings.app_env}")
    
    # TODO: Initialize services here
    # - Load Whisper model
    # - Connect to Ollama
    # - Initialize database connection
    
    yield
    
    # Shutdown
    logger.info("Shutting down Interview Assistant API...")


# Initialize FastAPI app
app = FastAPI(
    title="Interview Assistant API",
    description="Multi-modal AI interview coaching and evaluation platform",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "interview-assistant",
        "version": "0.1.0"
    }


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "message": "Interview Assistant API",
        "docs": "/docs",
        "health": "/health"
    }


# =============================================================================
# Route Imports (uncomment as you build each service)
# =============================================================================

# from services.question_service.routes import router as question_router
# from services.speech_service.routes import router as speech_router
# from services.evaluation_service.routes import router as evaluation_router
# from services.feedback_service.routes import router as feedback_router

# app.include_router(question_router, prefix="/api/v1/questions", tags=["Questions"])
# app.include_router(speech_router, prefix="/api/v1/speech", tags=["Speech"])
# app.include_router(evaluation_router, prefix="/api/v1/evaluation", tags=["Evaluation"])
# app.include_router(feedback_router, prefix="/api/v1/feedback", tags=["Feedback"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )