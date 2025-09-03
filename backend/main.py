#!/usr/bin/env python3
"""
Wrapper main.py that redirects to the root app.py
This handles Render's cached command while using our standalone app
"""
import sys
import os

# Add root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

import logging

# Setup centralized logging
try:
    from backend.core.logging import setup_development_logging, get_logger
    setup_development_logging()
    logger = get_logger(__name__)
except ImportError:
    # Fallback to basic logging if centralized logging fails
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

logger.info(f"🔄 Redirecting from backend/main.py to root app.py")
logger.info(f"📁 Root directory: {root_dir}")
logger.info(f"🐍 Python version: {sys.version}")

# Import the app from root directory
try:
    from app import app
    logger.info("✅ Successfully imported app from root directory")
except ImportError as e:
    logger.error(f"❌ Failed to import app: {e}")
    # Fallback: create a minimal app here
    from fastapi import FastAPI
    
    app = FastAPI(title="AI Social Media Content Agent - Fallback")
    
    @app.get("/")
    async def root():
        return {"message": "Fallback app is running", "status": "success"}
    
    @app.head("/")
    async def root_head():
        return {}
    
    @app.get("/health")
    async def health():
        return {"status": "healthy", "fallback": True}

# Export the app so uvicorn can find it
__all__ = ["app"]