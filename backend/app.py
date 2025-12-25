"""
Interview Assistant - Main FastAPI Application
Author: Mandar
Description: Entry point for the Interview Assistant backend API
Location: backend/app.py
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys

# Add paths for imports
sys.path.insert(0, ".")
sys.path.insert(0, "..")

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
    logger.info("=" * 50)
    logger.info("Starting Interview Assistant API...")
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Ollama URL: {settings.ollama_base_url}")
    logger.info(f"Ollama Model: {settings.ollama_model}")
    
    # Check Ollama connection
    try:
        from utils.llm_client import get_llm_client
        llm = get_llm_client()
        if llm.check_health():
            logger.info("✓ Ollama connection successful")
        else:
            logger.warning("✗ Ollama not available - some features will be limited")
    except Exception as e:
        logger.warning(f"✗ Ollama check failed: {e}")
    
    # Check spaCy
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        logger.info("✓ spaCy model loaded")
    except Exception as e:
        logger.warning(f"✗ spaCy model not available: {e}")
    
    logger.info("=" * 50)
    
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
    allow_origins=[
        "http://localhost:3000",      # React default
        "http://localhost:5173",      # Vite default
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Health & Info Endpoints
# =============================================================================

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
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "questions": "/api/v1/questions",
            "speech": "/api/v1/speech",
            "evaluation": "/api/v1/evaluation (coming soon)",
            "feedback": "/api/v1/feedback (coming soon)"
        }
    }


# =============================================================================
# Route Imports
# =============================================================================

# Question Service (Phase 2)
from services.question_service.routes import router as question_router
app.include_router(question_router, prefix="/api/v1/questions", tags=["Questions"])

# Speech Service (Phase 4)
from services.speech_service.routes import router as speech_router
app.include_router(speech_router, prefix="/api/v1/speech", tags=["Speech"])

# Evaluation Service (Phase 7) - uncomment when ready
# from services.evaluation_service.routes import router as evaluation_router
# app.include_router(evaluation_router, prefix="/api/v1/evaluation", tags=["Evaluation"])

# Feedback Service (Phase 7) - uncomment when ready
# from services.feedback_service.routes import router as feedback_router
# app.include_router(feedback_router, prefix="/api/v1/feedback", tags=["Feedback"])


# =============================================================================
# Error Handlers
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return {
        "error": "Internal server error",
        "detail": str(exc) if settings.debug else "An error occurred"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )