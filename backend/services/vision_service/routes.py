# backend/services/vision_service/routes.py (COMPLETE FILE)
"""
Vision Service API Routes
Location: backend/services/vision_service/routes.py
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
import base64
from datetime import datetime
import os
from pathlib import Path
from PIL import Image  # ✅ ADD THIS IMPORT
import io  # ✅ ADD THIS IMPORT

from models.schemas import ScreenshotMetadata, ScreenCaptureRequest
from services.vision_service.vision_analyzer import VisionAnalyzer
from services.vision_service.diagram_critic import DiagramCritic

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Storage Configuration
# =============================================================================

# Local screenshot storage directory
SCREENSHOT_DIR = Path("data/screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Request/Response Models
# =============================================================================

class AnalyzeImageRequest(BaseModel):
    """Request for basic image analysis."""
    image_base64: str
    task: str = "detailed_caption"


class VisionAnalysisResponse(BaseModel):
    """Response for vision analysis."""
    description: str
    objects_detected: List[str]
    text_detected: List[str]
    spatial_layout: str
    confidence: float


class DiagramCritiqueResponse(BaseModel):
    """Response for diagram critique."""
    screenshot_id: str
    components_identified: List[str]
    relationships_detected: List[str]
    completeness_score: float
    clarity_score: float
    scalability_assessment: str
    missing_elements: List[str]
    strengths: List[str]
    weaknesses: List[str]
    overall_score: float
    detailed_feedback: str


# =============================================================================
# Module Instances
# =============================================================================

vision_analyzer = VisionAnalyzer()
diagram_critic = DiagramCritic()


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/analyze-image", response_model=VisionAnalysisResponse)
async def analyze_image(request: AnalyzeImageRequest):
    """
    Analyze an image using Vision-LLM.
    
    Basic image understanding - describes what's in the image,
    detects objects, reads text (OCR), and describes spatial layout.
    """
    try:
        logger.info("Analyzing image with Vision-LLM")
        
        result = vision_analyzer.analyze_image(
            image_base64=request.image_base64,
            task=request.task
        )
        
        return VisionAnalysisResponse(
            description=result.description,
            objects_detected=result.objects_detected,
            text_detected=result.text_detected,
            spatial_layout=result.spatial_layout,
            confidence=result.confidence
        )
        
    except Exception as e:
        logger.error(f"Image analysis failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/capture-screenshot", response_model=ScreenshotMetadata)
async def capture_screenshot(request: ScreenCaptureRequest):
    """
    Store a screenshot and return metadata.
    
    Saves the screenshot to local storage and returns metadata
    for later retrieval and analysis.
    """
    try:
        logger.info(f"Capturing screenshot for session {request.session_id}")
        
        # Decode and validate image
        try:
            image_bytes = base64.b64decode(request.image_base64)
            image = Image.open(io.BytesIO(image_bytes))
            width, height = image.size
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image data: {str(e)}")
        
        # Generate filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{request.session_id}_{request.question_id}_{timestamp}.png"
        filepath = SCREENSHOT_DIR / filename
        
        # Save image
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        
        file_size = os.path.getsize(filepath)
        
        metadata = ScreenshotMetadata(
            session_id=request.session_id,
            question_id=request.question_id,
            capture_method=request.capture_method,
            file_path=str(filepath),
            file_size_bytes=file_size,
            image_width=width,
            image_height=height
        )
        
        logger.info(f"Screenshot saved: {filepath} ({file_size} bytes)")
        
        return metadata
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Screenshot capture failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Capture failed: {str(e)}")


@router.post("/critique-diagram", response_model=DiagramCritiqueResponse)
async def critique_diagram_endpoint(request: ScreenCaptureRequest):
    """
    Comprehensive system design diagram critique.
    
    Analyzes the diagram using Vision-LLM, then evaluates the design
    using Text-LLM with context from the question and transcript.
    
    Returns structured feedback with scores and improvement suggestions.
    """
    try:
        logger.info(f"Critiquing diagram for session {request.session_id}")
        
        # First, store the screenshot
        screenshot_metadata = await capture_screenshot(request)
        
        # Then, critique the diagram
        critique = diagram_critic.critique(
            screenshot_id=screenshot_metadata.screenshot_id,
            image_base64=request.image_base64,
            question_text=request.question_text,
            transcript=request.transcript,
            interview_type=request.interview_type
        )
        
        return DiagramCritiqueResponse(
            screenshot_id=critique.screenshot_id,
            components_identified=critique.components_identified,
            relationships_detected=critique.relationships_detected,
            completeness_score=critique.completeness_score,
            clarity_score=critique.clarity_score,
            scalability_assessment=critique.scalability_assessment,
            missing_elements=critique.missing_elements,
            strengths=critique.strengths,
            weaknesses=critique.weaknesses,
            overall_score=critique.overall_score,
            detailed_feedback=critique.detailed_feedback
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Diagram critique failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Critique failed: {str(e)}")


@router.get("/screenshots/{session_id}")
async def get_session_screenshots(session_id: str):
    """Get all screenshots for a session."""
    try:
        screenshots = []
        for filepath in SCREENSHOT_DIR.glob(f"{session_id}_*.png"):
            screenshots.append({
                "filename": filepath.name,
                "size_bytes": os.path.getsize(filepath),
                "created_at": datetime.fromtimestamp(os.path.getctime(filepath)).isoformat()
            })
        
        return {
            "session_id": session_id,
            "screenshots": screenshots,
            "total": len(screenshots)
        }
        
    except Exception as e:
        logger.error(f"Failed to list screenshots: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check for vision service."""
    vision_healthy = vision_analyzer.check_health()
    
    return {
        "service": "vision_service",
        "status": "healthy" if vision_healthy else "degraded",
        "vision_model_available": vision_healthy,
        "screenshot_storage": str(SCREENSHOT_DIR),
        "screenshots_stored": len(list(SCREENSHOT_DIR.glob("*.png")))
    }