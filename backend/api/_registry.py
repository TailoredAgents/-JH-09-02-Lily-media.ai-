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
    webhook_reliability,  # P0-11c: Webhook reliability monitoring and management
    legal_documents,  # GA Checklist: Privacy Policy & Terms URLs for platform compliance
    memory_vector,  # Vector memory endpoints used by frontend
    linkedin_oauth,  # LinkedIn OAuth 2.0 integration for autonomous posting
    dashboard_metrics,  # Dashboard metrics API for frontend consumption
    websockets,  # WebSocket endpoints for real-time status updates
    multi_tenant,  # Multi-tenant organization and RBAC management
    billing,  # Stripe billing and subscription management
    plans,  # Subscription plans and feature gating
    plan_billing,  # Enhanced plan-based billing with Stripe integration
    plan_aware_images,  # Plan-aware image generation with usage tracking
    performance,  # Performance monitoring and optimization
    monitoring_metrics,  # Prometheus and Sentry monitoring integration
    sre_dashboard,  # SRE dashboard for enhanced observability and operations
    observability,  # OpenTelemetry observability and metrics endpoints
    plan_management,  # Plan management and quota enforcement API
    data_export,  # GDPR/CCPA data export endpoints for privacy compliance
    data_retention,  # Data retention policy management and automated cleanup
    key_rotation,  # Encryption key rotation schedule and automation
    template_validation,  # Template coverage validation system for AI models
    error_taxonomy,  # Comprehensive error taxonomy mapping and classification
    pw_settings,  # PW-SETTINGS-ADD-001: Pressure washing settings namespaces API
    pw_pricing,  # PW-PRICING-ADD-001: Pressure washing pricing engine with org-scoping
    pw_quotes,  # PW-PRICING-ADD-002: Pressure washing quote endpoints with status lifecycle
    secure_media,  # PW-SEC-ADD-001: Secure media storage with signed URLs
    leads,  # PW-DM-ADD-002: Lead management and media attachment API
    jobs,  # PW-DM-ADD-001: Job management and scheduling API
)

# Import CSRF router
try:
    from backend.core.csrf_protection import csrf_router
    CSRF_ROUTER_AVAILABLE = True
except ImportError:
    CSRF_ROUTER_AVAILABLE = False
    csrf_router = None

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
    webhook_reliability.router,  # P0-11c: Webhook reliability monitoring and management
    legal_documents.router,  # GA Checklist: Privacy Policy & Terms URLs for platform compliance
    linkedin_oauth.router,  # LinkedIn OAuth 2.0 integration for autonomous posting
    dashboard_metrics.router,  # Dashboard metrics API for frontend consumption
    websockets.router,  # WebSocket endpoints for real-time status updates
    multi_tenant.router,  # Multi-tenant organization and RBAC management
    billing.router,  # Stripe billing and subscription management
    plans.router,  # Subscription plans and feature gating
    plan_billing.router,  # Enhanced plan-based billing with Stripe integration
    plan_aware_images.router,  # Plan-aware image generation with usage tracking
    performance.router,  # Performance monitoring and optimization
    monitoring_metrics.router,  # Prometheus and Sentry monitoring integration
    sre_dashboard.router,  # SRE dashboard for enhanced observability and operations
    observability.router,  # OpenTelemetry observability and metrics endpoints
    plan_management.router,  # Plan management and quota enforcement API
    data_export.router,  # GDPR/CCPA data export endpoints for privacy compliance
    data_retention.router,  # Data retention policy management and automated cleanup
    key_rotation.router,  # Encryption key rotation schedule and automation
    template_validation.router,  # Template coverage validation system for AI models
    error_taxonomy.router,  # Comprehensive error taxonomy mapping and classification
    pw_settings.router,  # PW-SETTINGS-ADD-001: Pressure washing settings namespaces API
    pw_pricing.router,  # PW-PRICING-ADD-001: Pressure washing pricing engine with org-scoping
    pw_quotes.router,  # PW-PRICING-ADD-002: Pressure washing quote endpoints with status lifecycle
    secure_media.router,  # PW-SEC-ADD-001: Secure media storage with signed URLs
    leads.router,  # PW-DM-ADD-002: Lead management and media attachment API
    jobs.router,  # PW-DM-ADD-001: Job management and scheduling API
]

# Add CSRF router if available
if CSRF_ROUTER_AVAILABLE and csrf_router:
    ROUTERS.append(csrf_router)  # CSRF token generation and validation endpoints
