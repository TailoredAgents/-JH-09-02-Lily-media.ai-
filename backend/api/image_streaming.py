"""
Streaming Image Generation API Endpoints

Provides real-time streaming endpoints for image generation with partial results
for improved user experience and perceived performance.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional
import json
import asyncio

from backend.db.models import User
from backend.auth.dependencies import get_current_active_user
from backend.services.image_generation_service import image_generation_service
from backend.middleware.feature_flag_enforcement import require_flag

router = APIRouter(prefix="/api/images", tags=["image-streaming"])

class StreamingImageRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500)
    platform: str = Field(..., pattern="^(twitter|linkedin|instagram|facebook|tiktok)$")
    partial_images: int = Field(2, ge=1, le=3)
    quality_preset: str = Field("standard", pattern="^(draft|standard|premium|story|banner)$")
    content_context: Optional[str] = Field(None, max_length=2000)
    industry_context: Optional[str] = Field(None, max_length=1000)

@router.post("/stream")
async def stream_image_generation(
    request: StreamingImageRequest,
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_flag("IMAGE_GENERATION"))
):
    """
    Stream image generation with partial results for real-time feedback.
    
    Returns Server-Sent Events (SSE) stream with partial images as they're generated.
    """
    
    async def generate_stream():
        """Generator function for streaming image data"""
        try:
            # Send initial event
            yield f"data: {json.dumps({'status': 'started', 'prompt': request.prompt})}\n\n"
            
            # Stream partial images
            async for event in image_generation_service.generate_streaming_image(
                prompt=request.prompt,
                platform=request.platform,
                partial_images=request.partial_images,
                quality_preset=request.quality_preset
            ):
                yield f"data: {json.dumps(event)}\n\n"
                
                # Add small delay for better streaming experience
                await asyncio.sleep(0.1)
                
        except Exception as e:
            error_event = {
                "status": "error",
                "error": str(e),
                "prompt": request.prompt
            }
            yield f"data: {json.dumps(error_event)}\n\n"
        
        # Send completion event
        yield f"data: {json.dumps({'status': 'stream_ended'})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable proxy buffering
        }
    )

@router.get("/stream-status")
async def get_streaming_status(
    current_user: User = Depends(get_current_active_user)
):
    """Get information about streaming capabilities and limits"""
    
    return {
        "streaming_enabled": True,
        "max_partial_images": 3,
        "supported_platforms": ["twitter", "linkedin", "instagram", "facebook", "tiktok"],
        "quality_presets": ["draft", "standard", "premium", "story", "banner"],
        "model": "grok-2-image",
        "features": [
            "Real-time partial image streaming",
            "Platform-specific optimization",
            "Multiple quality presets",
            "Content context awareness"
        ]
    }