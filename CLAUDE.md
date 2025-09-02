- Only write production-ready code, no mock, fake, demo, or placeholder code
- Always write production ready code
- Never create mock data, designs, or code
- when making edits or additions, check any related API endpoints and ensure all are properly connected
- when finished make changes, test build, commit to remote git repo
- Unless explicity required, you (claude) will do everything you can to avoid manual intervention during the process of fixing, update, or editing this project

# Current System Status (August 2025)

## Authentication System Conversion Complete ✅
- **COMPLETED**: Converted from registration-key system to open SaaS authentication
- **Backend**: Custom JWT system in `auth_open.py` module with registration/login endpoints
- **Frontend**: Registration form updated, email verification pages created
- **Database**: Alembic migration 016 removes registration keys, adds email verification fields
- **Config**: Email verification disabled by default (can be enabled later)

## OAuth Partner Integration Complete ✅
- **PHASE 4-8 COMPLETED**: Full partner OAuth integration system implemented
- **Connection Management**: OAuth-based Meta/X account connections with health monitoring
- **Rate Limiting**: Per-tenant rate limiting with Redis token bucket algorithm
- **Circuit Breakers**: Tenant-isolated fault tolerance for resilient publishing
- **Draft Verification**: Content scheduling with draft verification gates
- **Audit Logging**: Comprehensive connection management and publishing audit trails
- **Feature Flags**: `VITE_FEATURE_PARTNER_OAUTH` gating system for controlled rollout

## Current Production Deployment (Render.com) 🌐
- **Main API**: https://socialmedia-api-wxip.onrender.com (FastAPI backend)
- **Frontend**: https://socialmedia-frontend-pycc.onrender.com (React app)
- **Database**: PostgreSQL with pgvector extension
- **Redis**: Configured for caching, rate limiting, and circuit breaker state
- **Status**: Production-ready with OAuth partner integrations

## AI Models & Services 🤖
- **Content Generation**: OpenAI GPT-4o and GPT-4o-mini (not GPT-5)
- **Image Generation**: xAI Grok-2 Vision model with streaming capabilities
- **Embeddings**: OpenAI text-embedding-3-large with 3072-dimensional vectors
- **Platform Integration**: Multi-platform optimization for X, Meta, Instagram

## Architecture Highlights 🏗️
- **Multi-tenant Isolation**: Organization-scoped access control and data separation
- **Resilient Publishing**: Connection-based publishing with retry and backoff
- **Performance Optimization**: Connection pooling, Redis caching, rate limiting
- **Security**: Encrypted token storage, secure OAuth flows, audit logging

## Recently Resolved Issues ✅
- **Authentication Flow**: Custom JWT system working correctly
- **Router Registry**: All API endpoints properly registered
- **Import Conflicts**: Resolved encryption module import issues
- **Test Coverage**: Comprehensive unit and integration test suites

## Current Capabilities
- ✅ User registration and authentication
- ✅ OAuth partner connections (Meta, X/Twitter)
- ✅ Content creation and scheduling
- ✅ AI-powered image generation
- ✅ Rate limiting and circuit breakers
- ✅ Connection health monitoring
- ✅ Draft verification system
- ✅ Audit logging and compliance
- research the internet to confirm the proper way to fix or produce what youre working on
- Guardrail: production-ready only — no mock/fake/demo data in app code or migrations; mocks allowed in tests only; scan & confirm no banned patterns in the diff.
- Never create placeholder files
- Always write production ready code
- Always create valid and proper endpoints
- Never use mock data
- Never write mock code
- Always test build before commit
- Always commit to https://github.com/TailoredAgents/-JH-09-02-Lily-media.ai-.git
- Create a Handoff document for Codex to review all of your fixes after performing them and source the original guiding doc