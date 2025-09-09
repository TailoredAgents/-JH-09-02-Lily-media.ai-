#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Production-ready FastAPI app with comprehensive security hardening and startup health gates
"""
import sys
import os
from pathlib import Path

# Add backend to path FIRST so we can import our warning suppression
backend_path = Path(__file__).parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Import warning suppression before any third-party libraries
try:
    from backend.core.suppress_warnings import suppress_third_party_warnings
    suppress_third_party_warnings()
except ImportError:
    # Fallback if module not available
    import warnings
    warnings.filterwarnings("ignore", category=SyntaxWarning)
    warnings.filterwarnings("ignore", category=DeprecationWarning)

import logging

# Configure production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info("Starting AI Social Media Content Agent (Production)")
logger.info("Python version: {}".format(sys.version))
logger.info("Working directory: {}".format(os.getcwd()))
logger.info("Backend path already added: {}".format(backend_path))

# Import FastAPI with fallback
try:
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.responses import JSONResponse
    from fastapi.staticfiles import StaticFiles
    logger.info("FastAPI imported successfully")
except ImportError as e:
    logger.error("Failed to import FastAPI: {}".format(e))
    logger.error("Please ensure FastAPI is installed: pip install fastapi")
    sys.exit(1)

# P1-2a: Validate environment on startup with strict production enforcement
try:
    from backend.core.env_validator import validate_on_startup, validate_environment
    environment = os.getenv("ENVIRONMENT", "production").lower()
    
    # Get detailed validation results for better startup diagnostics
    validation_results = validate_environment()
    
    if validation_results["validation_passed"]:
        logger.info("✅ Environment validation passed - {} environment".format(environment))
        logger.info("📊 Configuration completeness: {}%".format(validation_results["configuration_completeness"]))
        
        # Log critical warnings
        if validation_results["warnings"]:
            logger.warning("⚠️  Environment validation warnings ({}):".format(len(validation_results["warnings"])))
            for warning in validation_results["warnings"][:5]:  # Log first 5 warnings
                logger.warning("  - {}".format(warning))
    else:
        logger.error("❌ Environment validation failed!")
        logger.error("Missing required variables: {}".format(validation_results["summary"]["missing_required"]))
        
        # In production, strict validation - fail fast with detailed error
        if environment == "production":
            logger.error("🚫 PRODUCTION: Environment validation failure is not permitted")
            logger.error("Required environment variables must be set before startup")
            for error in validation_results["errors"]:
                logger.error("  - {}".format(error))
            sys.exit(1)
        else:
            # In development, log errors but continue
            logger.warning("🔄 DEVELOPMENT: Continuing despite validation error")
            
except ImportError as e:
    logger.error("Environment validation module not available: {}".format(e))
    logger.error("Please ensure backend.core.env_validator is available")
    
    # In production, we require strict validation
    environment = os.getenv("ENVIRONMENT", "production").lower()
    if environment == "production":
        logger.error("🚫 PRODUCTION: Cannot start without environment validation")
        sys.exit(1)
    else:
        logger.warning("🔄 DEVELOPMENT: Continuing despite validation error")

# Create FastAPI app using factory pattern with health gates
environment = os.getenv("ENVIRONMENT", "production").lower()
logger.info("Creating FastAPI app using factory pattern with health gates for {} environment".format(environment))

try:
    from backend.core.app_factory import create_app, AppConfig
    
    # Create app configuration
    config = AppConfig(
        environment=environment,
        title="AI Social Media Content Agent",
        description="Complete autonomous social media management platform with security hardening",
        version="2.0.0",
        debug=environment == "development",
        enable_docs=environment != "production"
    )
    
    # Create app with health gates (production) or without (development)
    app = create_app(config)
    logger.info("✅ FastAPI app created successfully with health gates integration")
    
except ImportError as e:
    logger.error("❌ Failed to import app factory: {}".format(e))
    logger.info("Falling back to direct FastAPI app creation")
    
    # Fallback to direct app creation
    app = FastAPI(
        title="AI Social Media Content Agent",
        description="Complete autonomous social media management platform with security hardening",
        version="2.0.0",
        docs_url="/docs" if environment != "production" else None,
        redoc_url="/redoc" if environment != "production" else None
    )

# All middleware, routers, static files, health endpoints, and exception handlers 
# are now handled by the app factory pattern
logger.info("All application configuration delegated to app factory pattern")

# Database schema safety net (migrations should be run separately)
try:
    from backend.db.ensure_columns import ensure_user_columns, ensure_notifications_table, ensure_content_logs_table, ensure_social_inbox_tables
    logger.info("Running database schema safety net...")
    
    # Only run safety net for critical tables
    ensure_user_columns()
    ensure_notifications_table() 
    ensure_content_logs_table()
    ensure_social_inbox_tables()
    
    logger.info("✅ Database schema safety net completed")
    
except Exception as e:
    logger.warning("⚠️ Schema safety net warnings: {}".format(e))
    logger.info("App will continue - database tables may need manual creation")

logger.info("=== FastAPI App Startup Complete ===")
logger.info("Environment: {}".format(environment))
logger.info("Total routes: {}".format(len(app.routes)))
logger.info("Health gates: {}".format("Enabled" if environment == "production" else "Disabled"))
logger.info("======================================")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)