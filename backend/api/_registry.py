"""
Centralized router registry for all API endpoints
"""
from . import (
    auth_open,  # New open SaaS authentication
    auth_fastapi_users,
    admin,
    two_factor,
    user_credentials,
    user_settings,  # User preferences and configuration
    ai_suggestions,  # AI contextual suggestions
    content,
    goals,
    memory,
    workflow_v2,
    monitoring,
    diagnostics,
    content_history,
    notifications,
    vector_search,
    vector_search_production,
    similarity,
    deep_research,
    integration_services,
    feature_flags,
    autonomous,
    performance_monitoring,
    social_platforms,
    social_inbox,  # Phase 3A social inbox for managing interactions
    organizations,
    system_logs,  # System logging and error tracking
    database_health,  # Database schema health checks
    partner_oauth,  # Partner OAuth for multi-tenant connections
    assistant_chat,  # OpenAI Assistant chat for landing page
    data_deletion,  # GA Checklist: Data deletion endpoints for compliance
    webhooks,  # GA Checklist: Meta webhook endpoints for compliance
    legal_documents,  # GA Checklist: Privacy Policy & Terms URLs for platform compliance
    memory_vector,  # Vector memory endpoints used by frontend
    linkedin_oauth,  # LinkedIn OAuth 2.0 integration for autonomous posting
    dashboard_metrics,  # Dashboard metrics API for frontend consumption
    websockets,  # WebSocket endpoints for real-time status updates
    multi_tenant,  # Multi-tenant organization and RBAC management
)

# All routers to be registered with the FastAPI app
ROUTERS = [
    auth_fastapi_users.router,  # FastAPI Users authentication (primary)
    auth_open.router,  # Open SaaS authentication (no registration keys)
    two_factor.router,  # Two-Factor Authentication endpoints
    admin.router,  # Admin authentication and management system
    user_credentials.router,  # User social media credentials management
    user_settings.router,  # User preferences and configuration
    ai_suggestions.router,  # AI contextual suggestions
    content.router,
    goals.router,
    memory.router,
    workflow_v2.router,
    monitoring.router,
    monitoring.analytics_router,  # /api/analytics endpoints
    diagnostics.router,
    content_history.router,
    notifications.router,
    vector_search_production.router,  # Production pgvector search (primary)
    vector_search.router,  # Legacy vector search (will be phased out)
    memory_vector.router,  # Vector memory endpoints used by frontend
    similarity.router,
    deep_research.router,
    integration_services.router,
    feature_flags.router,
    autonomous.router,
    # performance_monitoring.router,  # Middleware only - no router
    social_platforms.router,  # Social media platform connections and posting
    social_inbox.router,  # Phase 3A social inbox for managing interactions
    organizations.router,  # Multi-tenant organization management
    system_logs.router,  # System logging and error tracking endpoints
    database_health.router,  # Database schema health monitoring
    partner_oauth.router,  # Partner OAuth for multi-tenant connections
    assistant_chat.router,  # OpenAI Assistant chat for landing page
    data_deletion.router,  # GA Checklist: Data deletion endpoints for compliance
    webhooks.router,  # GA Checklist: Meta webhook endpoints for compliance
    legal_documents.router,  # GA Checklist: Privacy Policy & Terms URLs for platform compliance
    linkedin_oauth.router,  # LinkedIn OAuth 2.0 integration for autonomous posting
    dashboard_metrics.router,  # Dashboard metrics API for frontend consumption
    websockets.router,  # WebSocket endpoints for real-time status updates
    multi_tenant.router,  # Multi-tenant organization and RBAC management
]
