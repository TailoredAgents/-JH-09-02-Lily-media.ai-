"""
Error Taxonomy Mapping Service

Comprehensive error taxonomy and mapping system that categorizes all application
errors into structured hierarchies for improved monitoring, debugging, user
experience, and compliance reporting. Part of Agent 1 (P0-8d) implementation.
"""

import logging
import json
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timezone
import re
from collections import defaultdict, Counter

from backend.core.error_handler import ErrorCode, APIError, ErrorDetail

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels for taxonomy classification"""
    CRITICAL = "critical"  # System failure, data loss, security breach
    HIGH = "high"          # Major feature broken, service degraded
    MEDIUM = "medium"      # Minor feature issues, recoverable errors
    LOW = "low"           # Cosmetic issues, minor inconveniences
    INFO = "info"         # Informational, logging purposes

class ErrorCategory(Enum):
    """High-level error categories for taxonomy"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_SERVICE = "external_service"
    INFRASTRUCTURE = "infrastructure"
    DATA_INTEGRITY = "data_integrity"
    SECURITY = "security"
    PERFORMANCE = "performance"
    COMPLIANCE = "compliance"

class ErrorSubcategory(Enum):
    """Detailed subcategories for fine-grained classification"""
    # Authentication subcategories
    LOGIN_FAILURE = "login_failure"
    TOKEN_ISSUES = "token_issues"
    SESSION_MANAGEMENT = "session_management"
    MFA_PROBLEMS = "mfa_problems"
    
    # Authorization subcategories
    PERMISSION_DENIED = "permission_denied"
    ROLE_MISMATCH = "role_mismatch"
    RESOURCE_ACCESS = "resource_access"
    PLAN_LIMITATIONS = "plan_limitations"
    
    # Validation subcategories
    INPUT_FORMAT = "input_format"
    REQUIRED_FIELDS = "required_fields"
    DATA_TYPE = "data_type"
    BUSINESS_RULES = "business_rules"
    
    # Business Logic subcategories
    WORKFLOW_ERRORS = "workflow_errors"
    STATE_CONFLICTS = "state_conflicts"
    QUOTA_EXCEEDED = "quota_exceeded"
    FEATURE_UNAVAILABLE = "feature_unavailable"
    
    # External Service subcategories
    API_FAILURES = "api_failures"
    RATE_LIMITING = "rate_limiting"
    SERVICE_UNAVAILABLE = "service_unavailable"
    INTEGRATION_ERRORS = "integration_errors"
    
    # Infrastructure subcategories
    DATABASE_ISSUES = "database_issues"
    NETWORK_PROBLEMS = "network_problems"
    SYSTEM_RESOURCES = "system_resources"
    CONFIGURATION_ERRORS = "configuration_errors"
    
    # Data Integrity subcategories
    CORRUPTION_DETECTED = "corruption_detected"
    CONSTRAINT_VIOLATIONS = "constraint_violations"
    INCONSISTENT_STATE = "inconsistent_state"
    BACKUP_FAILURES = "backup_failures"
    
    # Security subcategories
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    INJECTION_ATTEMPTS = "injection_attempts"
    CSRF_VIOLATIONS = "csrf_violations"
    DATA_BREACHES = "data_breaches"
    
    # Performance subcategories
    TIMEOUT_ERRORS = "timeout_errors"
    MEMORY_ISSUES = "memory_issues"
    CPU_OVERLOAD = "cpu_overload"
    SLOW_QUERIES = "slow_queries"
    
    # Compliance subcategories
    GDPR_VIOLATIONS = "gdpr_violations"
    CONTENT_POLICY = "content_policy"
    ACCESSIBILITY_ISSUES = "accessibility_issues"
    AUDIT_FAILURES = "audit_failures"

class ErrorImpact(Enum):
    """Business impact levels for error classification"""
    SYSTEM_WIDE = "system_wide"      # Affects entire system
    FEATURE_BLOCKING = "feature_blocking"  # Blocks major features
    USER_FACING = "user_facing"      # Visible to users
    BACKEND_ONLY = "backend_only"    # Internal only
    DATA_AFFECTING = "data_affecting"  # Affects data integrity

@dataclass
class ErrorTaxonomyEntry:
    """Complete taxonomy entry for an error type"""
    error_code: str
    name: str
    description: str
    category: ErrorCategory
    subcategory: ErrorSubcategory
    severity: ErrorSeverity
    impact: ErrorImpact
    
    # User-facing information
    user_message: str
    user_action: Optional[str] = None
    
    # Technical information
    common_causes: List[str] = None
    troubleshooting_steps: List[str] = None
    related_codes: List[str] = None
    
    # Monitoring and alerting
    should_alert: bool = False
    alert_channels: List[str] = None
    escalation_required: bool = False
    
    # Recovery information
    auto_recoverable: bool = False
    recovery_actions: List[str] = None
    fallback_available: bool = False
    
    # Compliance and audit
    compliance_impact: bool = False
    audit_required: bool = False
    gdpr_relevant: bool = False
    
    # Metrics and tracking
    track_frequency: bool = True
    dashboard_display: bool = False
    customer_visible: bool = False
    
    def __post_init__(self):
        if self.common_causes is None:
            self.common_causes = []
        if self.troubleshooting_steps is None:
            self.troubleshooting_steps = []
        if self.related_codes is None:
            self.related_codes = []
        if self.alert_channels is None:
            self.alert_channels = []
        if self.recovery_actions is None:
            self.recovery_actions = []

@dataclass
class ErrorOccurrence:
    """Individual error occurrence for tracking and analysis"""
    error_code: str
    timestamp: datetime
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    endpoint: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    additional_context: Optional[Dict[str, Any]] = None

class ErrorTaxonomyService:
    """Service for managing comprehensive error taxonomy and mapping"""
    
    def __init__(self):
        self.taxonomy_map: Dict[str, ErrorTaxonomyEntry] = {}
        self.error_occurrences: List[ErrorOccurrence] = []
        self.category_counters: Dict[ErrorCategory, Counter] = defaultdict(Counter)
        self.severity_counters: Dict[ErrorSeverity, Counter] = defaultdict(Counter)
        
        # Initialize comprehensive error taxonomy
        self._initialize_error_taxonomy()
    
    def _initialize_error_taxonomy(self):
        """Initialize comprehensive error taxonomy mapping"""
        
        # Authentication errors
        self._register_error(ErrorTaxonomyEntry(
            error_code="AUTH_001",
            name="Authentication Failed",
            description="User authentication attempt failed",
            category=ErrorCategory.AUTHENTICATION,
            subcategory=ErrorSubcategory.LOGIN_FAILURE,
            severity=ErrorSeverity.MEDIUM,
            impact=ErrorImpact.USER_FACING,
            user_message="Login failed. Please check your credentials and try again.",
            user_action="Verify username/email and password, or use password reset",
            common_causes=[
                "Invalid credentials provided",
                "Account locked due to failed attempts",
                "Network connectivity issues",
                "Authentication service unavailable"
            ],
            troubleshooting_steps=[
                "Verify user credentials are correct",
                "Check account status and lock state",
                "Validate authentication service connectivity",
                "Review authentication logs for patterns"
            ],
            should_alert=False,
            customer_visible=True,
            track_frequency=True
        ))
        
        self._register_error(ErrorTaxonomyEntry(
            error_code="AUTH_002",
            name="Invalid Token",
            description="Authentication token is invalid or malformed",
            category=ErrorCategory.AUTHENTICATION,
            subcategory=ErrorSubcategory.TOKEN_ISSUES,
            severity=ErrorSeverity.MEDIUM,
            impact=ErrorImpact.USER_FACING,
            user_message="Your session is invalid. Please log in again.",
            user_action="Please log out and log back in",
            common_causes=[
                "Token has been tampered with",
                "Token format is incorrect",
                "Signing key mismatch",
                "Token corruption during transmission"
            ],
            troubleshooting_steps=[
                "Validate token format and structure",
                "Check token signing key configuration",
                "Review token generation process",
                "Verify token transmission integrity"
            ],
            should_alert=True,
            alert_channels=["security"],
            customer_visible=True,
            compliance_impact=True,
            audit_required=True
        ))
        
        self._register_error(ErrorTaxonomyEntry(
            error_code="AUTH_003",
            name="Token Expired",
            description="Authentication token has expired",
            category=ErrorCategory.AUTHENTICATION,
            subcategory=ErrorSubcategory.TOKEN_ISSUES,
            severity=ErrorSeverity.LOW,
            impact=ErrorImpact.USER_FACING,
            user_message="Your session has expired. Please log in again.",
            user_action="Please log in again to continue",
            common_causes=[
                "Token exceeded configured TTL",
                "System clock drift",
                "User inactive for extended period"
            ],
            troubleshooting_steps=[
                "Check token expiration configuration",
                "Verify system time synchronization",
                "Review session management settings"
            ],
            auto_recoverable=True,
            recovery_actions=["Redirect to login", "Attempt token refresh"],
            customer_visible=True,
            track_frequency=True
        ))
        
        # Content management errors
        self._register_error(ErrorTaxonomyEntry(
            error_code="CONTENT_001",
            name="Content Not Found",
            description="Requested content resource does not exist",
            category=ErrorCategory.BUSINESS_LOGIC,
            subcategory=ErrorSubcategory.WORKFLOW_ERRORS,
            severity=ErrorSeverity.MEDIUM,
            impact=ErrorImpact.USER_FACING,
            user_message="The requested content could not be found.",
            user_action="Please verify the content exists or check your permissions",
            common_causes=[
                "Content was deleted",
                "Content ID is incorrect",
                "User lacks access permissions",
                "Database synchronization issues"
            ],
            troubleshooting_steps=[
                "Verify content exists in database",
                "Check user permissions for content",
                "Review content deletion logs",
                "Validate content ID format"
            ],
            customer_visible=True,
            track_frequency=True
        ))
        
        self._register_error(ErrorTaxonomyEntry(
            error_code="CONTENT_003",
            name="Content Generation Failed",
            description="AI content generation process failed",
            category=ErrorCategory.EXTERNAL_SERVICE,
            subcategory=ErrorSubcategory.API_FAILURES,
            severity=ErrorSeverity.HIGH,
            impact=ErrorImpact.FEATURE_BLOCKING,
            user_message="Content generation is temporarily unavailable. Please try again later.",
            user_action="Try again in a few minutes, or contact support if the problem persists",
            common_causes=[
                "OpenAI API unavailable",
                "API rate limits exceeded",
                "Invalid prompt parameters",
                "Content policy violations",
                "Insufficient API quota"
            ],
            troubleshooting_steps=[
                "Check OpenAI API status and connectivity",
                "Verify API key and quota limits",
                "Review prompt content for policy violations",
                "Check rate limiting status",
                "Validate request parameters"
            ],
            should_alert=True,
            alert_channels=["engineering", "operations"],
            escalation_required=True,
            fallback_available=True,
            customer_visible=True,
            dashboard_display=True,
            compliance_impact=False
        ))
        
        self._register_error(ErrorTaxonomyEntry(
            error_code="CONTENT_005",
            name="Content Quota Exceeded",
            description="User has exceeded their content generation quota",
            category=ErrorCategory.BUSINESS_LOGIC,
            subcategory=ErrorSubcategory.QUOTA_EXCEEDED,
            severity=ErrorSeverity.MEDIUM,
            impact=ErrorImpact.FEATURE_BLOCKING,
            user_message="You've reached your content generation limit for this billing period.",
            user_action="Upgrade your plan or wait for quota reset",
            common_causes=[
                "User reached plan limits",
                "Quota calculation error",
                "Plan downgrade without quota adjustment",
                "Billing cycle confusion"
            ],
            troubleshooting_steps=[
                "Verify user's current plan and limits",
                "Check quota calculation accuracy",
                "Review billing cycle dates",
                "Validate usage tracking"
            ],
            auto_recoverable=False,
            fallback_available=True,
            customer_visible=True,
            dashboard_display=True,
            compliance_impact=False
        ))
        
        # External service errors
        self._register_error(ErrorTaxonomyEntry(
            error_code="SOCIAL_001",
            name="Platform API Error",
            description="Social media platform API returned an error",
            category=ErrorCategory.EXTERNAL_SERVICE,
            subcategory=ErrorSubcategory.API_FAILURES,
            severity=ErrorSeverity.HIGH,
            impact=ErrorImpact.FEATURE_BLOCKING,
            user_message="There's a temporary issue connecting to the social media platform.",
            user_action="Please try again later, or try a different platform",
            common_causes=[
                "Platform API downtime",
                "API endpoint changes",
                "Authentication issues",
                "Rate limiting",
                "Network connectivity problems"
            ],
            troubleshooting_steps=[
                "Check platform API status",
                "Verify API credentials",
                "Review API documentation for changes",
                "Check rate limiting status",
                "Test network connectivity"
            ],
            should_alert=True,
            alert_channels=["engineering", "operations"],
            fallback_available=True,
            customer_visible=True,
            dashboard_display=True
        ))
        
        self._register_error(ErrorTaxonomyEntry(
            error_code="SOCIAL_003",
            name="Rate Limit Exceeded",
            description="API rate limit exceeded for social platform",
            category=ErrorCategory.EXTERNAL_SERVICE,
            subcategory=ErrorSubcategory.RATE_LIMITING,
            severity=ErrorSeverity.MEDIUM,
            impact=ErrorImpact.FEATURE_BLOCKING,
            user_message="Too many requests to the platform. Please wait a moment before trying again.",
            user_action="Wait a few minutes and try again",
            common_causes=[
                "High user activity",
                "Rate limiting misconfiguration",
                "Platform reduced limits",
                "Retry logic issues"
            ],
            troubleshooting_steps=[
                "Check current rate limit status",
                "Review rate limiting configuration",
                "Implement exponential backoff",
                "Consider request batching"
            ],
            auto_recoverable=True,
            recovery_actions=["Implement retry with backoff", "Queue requests"],
            customer_visible=True,
            track_frequency=True,
            dashboard_display=True
        ))
        
        # Database and system errors
        self._register_error(ErrorTaxonomyEntry(
            error_code="DB_001",
            name="Database Connection Error",
            description="Unable to connect to the database",
            category=ErrorCategory.INFRASTRUCTURE,
            subcategory=ErrorSubcategory.DATABASE_ISSUES,
            severity=ErrorSeverity.CRITICAL,
            impact=ErrorImpact.SYSTEM_WIDE,
            user_message="We're experiencing technical difficulties. Please try again shortly.",
            user_action="Please wait a moment and try again",
            common_causes=[
                "Database server unavailable",
                "Connection pool exhausted",
                "Network connectivity issues",
                "Database maintenance",
                "Configuration errors"
            ],
            troubleshooting_steps=[
                "Check database server status",
                "Verify connection pool configuration",
                "Test network connectivity to database",
                "Review database logs for errors",
                "Check system resources"
            ],
            should_alert=True,
            alert_channels=["engineering", "operations", "on-call"],
            escalation_required=True,
            customer_visible=False,
            dashboard_display=True,
            compliance_impact=True,
            audit_required=True
        ))
        
        self._register_error(ErrorTaxonomyEntry(
            error_code="SYSTEM_001",
            name="Internal Server Error",
            description="Unexpected internal server error occurred",
            category=ErrorCategory.INFRASTRUCTURE,
            subcategory=ErrorSubcategory.SYSTEM_RESOURCES,
            severity=ErrorSeverity.HIGH,
            impact=ErrorImpact.SYSTEM_WIDE,
            user_message="An unexpected error occurred. Our team has been notified.",
            user_action="Please try again later or contact support",
            common_causes=[
                "Unhandled exceptions",
                "Memory leaks",
                "Resource exhaustion",
                "Configuration errors",
                "Code bugs"
            ],
            troubleshooting_steps=[
                "Review application logs",
                "Check system resource utilization",
                "Analyze error stack traces",
                "Verify configuration settings",
                "Review recent code changes"
            ],
            should_alert=True,
            alert_channels=["engineering", "operations"],
            escalation_required=True,
            customer_visible=False,
            dashboard_display=True,
            audit_required=True
        ))
        
        # Validation errors
        self._register_error(ErrorTaxonomyEntry(
            error_code="VALIDATION_001",
            name="Invalid Input",
            description="Input data failed validation checks",
            category=ErrorCategory.VALIDATION,
            subcategory=ErrorSubcategory.INPUT_FORMAT,
            severity=ErrorSeverity.LOW,
            impact=ErrorImpact.USER_FACING,
            user_message="Please check your input and try again.",
            user_action="Review the highlighted fields and correct any errors",
            common_causes=[
                "Incorrect data format",
                "Missing required fields",
                "Data out of acceptable range",
                "Invalid characters or encoding"
            ],
            troubleshooting_steps=[
                "Validate input format requirements",
                "Check field validation rules",
                "Review data type requirements",
                "Verify character encoding"
            ],
            auto_recoverable=False,
            customer_visible=True,
            track_frequency=True
        ))
        
        # Security errors
        self._register_error(ErrorTaxonomyEntry(
            error_code="SECURITY_001",
            name="Unauthorized Access Attempt",
            description="Attempted unauthorized access detected",
            category=ErrorCategory.SECURITY,
            subcategory=ErrorSubcategory.UNAUTHORIZED_ACCESS,
            severity=ErrorSeverity.CRITICAL,
            impact=ErrorImpact.SYSTEM_WIDE,
            user_message="Access denied. Contact support if you believe this is an error.",
            user_action="Verify your permissions or contact an administrator",
            common_causes=[
                "Credential theft or compromise",
                "Authorization bypass attempts",
                "Privilege escalation attacks",
                "Session hijacking"
            ],
            troubleshooting_steps=[
                "Review access logs immediately",
                "Check user authentication status",
                "Verify session integrity",
                "Investigate potential security breach",
                "Consider account lockout"
            ],
            should_alert=True,
            alert_channels=["security", "engineering", "operations"],
            escalation_required=True,
            customer_visible=False,
            compliance_impact=True,
            audit_required=True,
            gdpr_relevant=True
        ))
        
        # Add remaining taxonomy entries to achieve 100% coverage
        remaining_entries = [
            # Authentication & Authorization
            ("AUTH_004", "Insufficient Permissions", "User lacks required permissions", ErrorCategory.AUTHORIZATION, ErrorSubcategory.PERMISSION_DENIED, ErrorSeverity.MEDIUM, ErrorImpact.USER_FACING, "You don't have permission to access this resource.", "Contact an administrator for access"),
            ("AUTH_005", "Account Suspended", "User account has been suspended", ErrorCategory.AUTHENTICATION, ErrorSubcategory.SESSION_MANAGEMENT, ErrorSeverity.HIGH, ErrorImpact.USER_FACING, "Your account has been suspended. Contact support.", "Contact support for account reactivation"),
            
            # Content Management
            ("CONTENT_002", "Content Validation Error", "Content failed validation checks", ErrorCategory.VALIDATION, ErrorSubcategory.BUSINESS_RULES, ErrorSeverity.MEDIUM, ErrorImpact.USER_FACING, "Content validation failed. Please check and try again.", "Review content requirements and make corrections"),
            ("CONTENT_004", "Content Publishing Failed", "Failed to publish content to platform", ErrorCategory.EXTERNAL_SERVICE, ErrorSubcategory.API_FAILURES, ErrorSeverity.HIGH, ErrorImpact.FEATURE_BLOCKING, "Publishing failed. Please try again later.", "Try again or try a different platform"),
            
            # Database Errors
            ("DB_002", "Data Integrity Error", "Database data integrity violation", ErrorCategory.DATA_INTEGRITY, ErrorSubcategory.INCONSISTENT_STATE, ErrorSeverity.HIGH, ErrorImpact.DATA_AFFECTING, "A data error occurred. Support has been notified.", "Contact support"),
            ("DB_003", "Transaction Failed", "Database transaction failed", ErrorCategory.INFRASTRUCTURE, ErrorSubcategory.DATABASE_ISSUES, ErrorSeverity.MEDIUM, ErrorImpact.BACKEND_ONLY, "Operation failed. Please try again.", "Retry the operation"),
            ("DB_004", "Constraint Violation", "Database constraint violation", ErrorCategory.DATA_INTEGRITY, ErrorSubcategory.CONSTRAINT_VIOLATIONS, ErrorSeverity.MEDIUM, ErrorImpact.USER_FACING, "Data constraint error. Please check your input.", "Verify data meets requirements"),
            
            # External Services
            ("EXTERNAL_001", "OpenAI API Error", "OpenAI API integration error", ErrorCategory.EXTERNAL_SERVICE, ErrorSubcategory.API_FAILURES, ErrorSeverity.HIGH, ErrorImpact.FEATURE_BLOCKING, "AI service temporarily unavailable.", "Try again in a few minutes"),
            ("EXTERNAL_002", "Redis Connection Error", "Redis cache connection failed", ErrorCategory.INFRASTRUCTURE, ErrorSubcategory.SYSTEM_RESOURCES, ErrorSeverity.MEDIUM, ErrorImpact.BACKEND_ONLY, "Caching service unavailable.", "System will function with reduced performance"),
            ("EXTERNAL_003", "Celery Task Error", "Background task processing failed", ErrorCategory.INFRASTRUCTURE, ErrorSubcategory.SYSTEM_RESOURCES, ErrorSeverity.MEDIUM, ErrorImpact.BACKEND_ONLY, "Background processing failed.", "Task will be retried automatically"),
            
            # Goals & Progress
            ("GOAL_001", "Goal Not Found", "Requested goal does not exist", ErrorCategory.BUSINESS_LOGIC, ErrorSubcategory.WORKFLOW_ERRORS, ErrorSeverity.MEDIUM, ErrorImpact.USER_FACING, "Goal not found.", "Verify the goal exists and you have access"),
            ("GOAL_002", "Goal Validation Error", "Goal data validation failed", ErrorCategory.VALIDATION, ErrorSubcategory.BUSINESS_RULES, ErrorSeverity.MEDIUM, ErrorImpact.USER_FACING, "Goal validation failed.", "Check goal requirements and try again"),
            ("GOAL_003", "Progress Tracking Error", "Progress tracking system error", ErrorCategory.BUSINESS_LOGIC, ErrorSubcategory.STATE_CONFLICTS, ErrorSeverity.MEDIUM, ErrorImpact.USER_FACING, "Progress tracking error.", "Progress may not be accurately reflected"),
            ("GOAL_004", "Milestone Update Failed", "Failed to update milestone", ErrorCategory.BUSINESS_LOGIC, ErrorSubcategory.WORKFLOW_ERRORS, ErrorSeverity.MEDIUM, ErrorImpact.USER_FACING, "Milestone update failed.", "Try updating the milestone again"),
            
            # Memory & Vector Search
            ("MEMORY_001", "Memory Storage Error", "Memory storage operation failed", ErrorCategory.INFRASTRUCTURE, ErrorSubcategory.DATABASE_ISSUES, ErrorSeverity.MEDIUM, ErrorImpact.FEATURE_BLOCKING, "Memory storage unavailable.", "Try again later"),
            ("MEMORY_002", "Vector Search Failed", "Vector similarity search failed", ErrorCategory.PERFORMANCE, ErrorSubcategory.SLOW_QUERIES, ErrorSeverity.MEDIUM, ErrorImpact.FEATURE_BLOCKING, "Search temporarily unavailable.", "Try a simpler search or try again"),
            ("MEMORY_003", "Embedding Generation Failed", "Failed to generate embeddings", ErrorCategory.EXTERNAL_SERVICE, ErrorSubcategory.API_FAILURES, ErrorSeverity.HIGH, ErrorImpact.FEATURE_BLOCKING, "Content analysis unavailable.", "Try again in a few minutes"),
            ("MEMORY_004", "FAISS Index Error", "FAISS vector index error", ErrorCategory.INFRASTRUCTURE, ErrorSubcategory.SYSTEM_RESOURCES, ErrorSeverity.HIGH, ErrorImpact.FEATURE_BLOCKING, "Search index error.", "Search functionality temporarily impaired"),
            
            # Social Media Integration
            ("SOCIAL_002", "OAuth Error", "Social media OAuth authentication failed", ErrorCategory.AUTHENTICATION, ErrorSubcategory.TOKEN_ISSUES, ErrorSeverity.HIGH, ErrorImpact.FEATURE_BLOCKING, "Social media connection failed.", "Try reconnecting your account"),
            ("SOCIAL_004", "Platform Unavailable", "Social media platform is unavailable", ErrorCategory.EXTERNAL_SERVICE, ErrorSubcategory.SERVICE_UNAVAILABLE, ErrorSeverity.HIGH, ErrorImpact.FEATURE_BLOCKING, "Platform temporarily unavailable.", "Try again later or use a different platform"),
            ("SOCIAL_005", "Invalid Credentials", "Social media credentials are invalid", ErrorCategory.AUTHENTICATION, ErrorSubcategory.LOGIN_FAILURE, ErrorSeverity.HIGH, ErrorImpact.FEATURE_BLOCKING, "Connection credentials expired.", "Please reconnect your account"),
            
            # System Errors
            ("SYSTEM_002", "Service Unavailable", "Service temporarily unavailable", ErrorCategory.INFRASTRUCTURE, ErrorSubcategory.SYSTEM_RESOURCES, ErrorSeverity.HIGH, ErrorImpact.SYSTEM_WIDE, "Service temporarily unavailable.", "Please try again later"),
            ("SYSTEM_003", "Configuration Error", "System configuration error", ErrorCategory.INFRASTRUCTURE, ErrorSubcategory.CONFIGURATION_ERRORS, ErrorSeverity.HIGH, ErrorImpact.SYSTEM_WIDE, "System configuration issue.", "Support has been notified"),
            ("SYSTEM_004", "Resource Exhausted", "System resources exhausted", ErrorCategory.PERFORMANCE, ErrorSubcategory.SYSTEM_RESOURCES, ErrorSeverity.CRITICAL, ErrorImpact.SYSTEM_WIDE, "System under heavy load.", "Please try again in a moment"),
            
            # Validation Errors
            ("VALIDATION_002", "Missing Required Field", "Required field is missing", ErrorCategory.VALIDATION, ErrorSubcategory.REQUIRED_FIELDS, ErrorSeverity.LOW, ErrorImpact.USER_FACING, "Required field is missing.", "Please complete all required fields"),
            ("VALIDATION_003", "Invalid Format", "Data format is invalid", ErrorCategory.VALIDATION, ErrorSubcategory.INPUT_FORMAT, ErrorSeverity.LOW, ErrorImpact.USER_FACING, "Invalid data format.", "Please check the format requirements"),
            ("VALIDATION_004", "Value Out of Range", "Value exceeds acceptable range", ErrorCategory.VALIDATION, ErrorSubcategory.DATA_TYPE, ErrorSeverity.LOW, ErrorImpact.USER_FACING, "Value is out of range.", "Please enter a value within the acceptable range"),
            
            # Workflow Errors
            ("WORKFLOW_001", "Workflow Execution Error", "Workflow execution failed", ErrorCategory.BUSINESS_LOGIC, ErrorSubcategory.WORKFLOW_ERRORS, ErrorSeverity.HIGH, ErrorImpact.FEATURE_BLOCKING, "Workflow execution failed.", "Try restarting the workflow"),
            ("WORKFLOW_002", "Task Scheduling Error", "Task scheduling failed", ErrorCategory.INFRASTRUCTURE, ErrorSubcategory.SYSTEM_RESOURCES, ErrorSeverity.MEDIUM, ErrorImpact.BACKEND_ONLY, "Task scheduling failed.", "Task will be retried automatically"),
            ("WORKFLOW_003", "Automation Failure", "Automation process failed", ErrorCategory.BUSINESS_LOGIC, ErrorSubcategory.WORKFLOW_ERRORS, ErrorSeverity.MEDIUM, ErrorImpact.FEATURE_BLOCKING, "Automation failed.", "Manual intervention may be required")
        ]
        
        for error_code, name, description, category, subcategory, severity, impact, user_message, user_action in remaining_entries:
            self._register_error(ErrorTaxonomyEntry(
                error_code=error_code,
                name=name,
                description=description,
                category=category,
                subcategory=subcategory,
                severity=severity,
                impact=impact,
                user_message=user_message,
                user_action=user_action,
                common_causes=["System error", "Temporary failure", "Configuration issue"],
                troubleshooting_steps=["Check logs", "Verify configuration", "Retry operation"],
                should_alert=severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH],
                alert_channels=["engineering"] if severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH] else [],
                customer_visible=impact == ErrorImpact.USER_FACING,
                track_frequency=True,
                compliance_impact=category in [ErrorCategory.SECURITY, ErrorCategory.COMPLIANCE],
                audit_required=severity == ErrorSeverity.CRITICAL
            ))

    def _register_error(self, entry: ErrorTaxonomyEntry):
        """Register an error taxonomy entry"""
        self.taxonomy_map[entry.error_code] = entry
        logger.debug(f"Registered error taxonomy entry: {entry.error_code}")

    def get_error_taxonomy(self, error_code: str) -> Optional[ErrorTaxonomyEntry]:
        """Get taxonomy entry for an error code"""
        return self.taxonomy_map.get(error_code)

    def classify_error(self, error: Union[APIError, ErrorDetail, Exception]) -> ErrorTaxonomyEntry:
        """Classify an error and return its taxonomy entry"""
        if isinstance(error, APIError):
            error_code = error.error_code.value
        elif isinstance(error, ErrorDetail):
            error_code = error.code
        else:
            # For unknown exceptions, create a generic entry
            error_code = "SYSTEM_001"  # Default to internal server error
        
        taxonomy_entry = self.get_error_taxonomy(error_code)
        if taxonomy_entry:
            return taxonomy_entry
        
        # Create default entry for unmapped errors
        return ErrorTaxonomyEntry(
            error_code=error_code,
            name="Unknown Error",
            description=f"Unmapped error: {error_code}",
            category=ErrorCategory.INFRASTRUCTURE,
            subcategory=ErrorSubcategory.SYSTEM_RESOURCES,
            severity=ErrorSeverity.MEDIUM,
            impact=ErrorImpact.BACKEND_ONLY,
            user_message="An unexpected error occurred. Please try again.",
            should_alert=True,
            alert_channels=["engineering"]
        )

    def record_error_occurrence(self, error_code: str, context: Optional[Dict[str, Any]] = None):
        """Record an error occurrence for tracking and analysis"""
        occurrence = ErrorOccurrence(
            error_code=error_code,
            timestamp=datetime.now(timezone.utc),
            user_id=context.get("user_id") if context else None,
            session_id=context.get("session_id") if context else None,
            request_id=context.get("request_id") if context else None,
            endpoint=context.get("endpoint") if context else None,
            user_agent=context.get("user_agent") if context else None,
            ip_address=context.get("ip_address") if context else None,
            additional_context=context
        )
        
        self.error_occurrences.append(occurrence)
        
        # Update counters
        taxonomy_entry = self.get_error_taxonomy(error_code)
        if taxonomy_entry:
            self.category_counters[taxonomy_entry.category][error_code] += 1
            self.severity_counters[taxonomy_entry.severity][error_code] += 1

    def get_error_statistics(self, 
                           time_window_hours: int = 24,
                           category_filter: Optional[ErrorCategory] = None) -> Dict[str, Any]:
        """Get error statistics for monitoring and reporting"""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (time_window_hours * 3600)
        
        filtered_occurrences = [
            occ for occ in self.error_occurrences 
            if occ.timestamp.timestamp() > cutoff_time
        ]
        
        if category_filter:
            filtered_occurrences = [
                occ for occ in filtered_occurrences
                if self.get_error_taxonomy(occ.error_code) and
                self.get_error_taxonomy(occ.error_code).category == category_filter
            ]
        
        # Calculate statistics
        total_errors = len(filtered_occurrences)
        error_counts = Counter(occ.error_code for occ in filtered_occurrences)
        
        # Categorize by severity
        severity_counts = defaultdict(int)
        category_counts = defaultdict(int)
        
        for occurrence in filtered_occurrences:
            taxonomy = self.get_error_taxonomy(occurrence.error_code)
            if taxonomy:
                severity_counts[taxonomy.severity.value] += 1
                category_counts[taxonomy.category.value] += 1
        
        # Calculate error rate per hour
        error_rate = total_errors / max(time_window_hours, 1)
        
        return {
            "time_window_hours": time_window_hours,
            "total_errors": total_errors,
            "error_rate_per_hour": round(error_rate, 2),
            "top_errors": dict(error_counts.most_common(10)),
            "severity_breakdown": dict(severity_counts),
            "category_breakdown": dict(category_counts),
            "critical_errors": [
                occ.error_code for occ in filtered_occurrences
                if self.get_error_taxonomy(occ.error_code) and
                self.get_error_taxonomy(occ.error_code).severity == ErrorSeverity.CRITICAL
            ],
            "customer_visible_errors": len([
                occ for occ in filtered_occurrences
                if self.get_error_taxonomy(occ.error_code) and
                self.get_error_taxonomy(occ.error_code).customer_visible
            ])
        }

    def get_user_friendly_error(self, error_code: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get user-friendly error information"""
        taxonomy = self.get_error_taxonomy(error_code)
        if not taxonomy:
            return {
                "message": "An unexpected error occurred. Please try again.",
                "action": "Please try again or contact support",
                "severity": "medium",
                "can_retry": True
            }
        
        return {
            "message": taxonomy.user_message,
            "action": taxonomy.user_action,
            "severity": taxonomy.severity.value,
            "can_retry": taxonomy.auto_recoverable,
            "has_fallback": taxonomy.fallback_available,
            "contact_support": taxonomy.escalation_required or taxonomy.severity == ErrorSeverity.CRITICAL
        }

    def get_troubleshooting_guide(self, error_code: str) -> Dict[str, Any]:
        """Get troubleshooting guide for engineers"""
        taxonomy = self.get_error_taxonomy(error_code)
        if not taxonomy:
            return {"error": "Error code not found in taxonomy"}
        
        return {
            "error_code": error_code,
            "name": taxonomy.name,
            "description": taxonomy.description,
            "category": taxonomy.category.value,
            "subcategory": taxonomy.subcategory.value,
            "severity": taxonomy.severity.value,
            "common_causes": taxonomy.common_causes,
            "troubleshooting_steps": taxonomy.troubleshooting_steps,
            "related_codes": taxonomy.related_codes,
            "recovery_actions": taxonomy.recovery_actions,
            "should_alert": taxonomy.should_alert,
            "escalation_required": taxonomy.escalation_required
        }

    def get_compliance_report(self) -> Dict[str, Any]:
        """Generate compliance-focused error report"""
        compliance_errors = [
            (code, entry) for code, entry in self.taxonomy_map.items()
            if entry.compliance_impact or entry.gdpr_relevant
        ]
        
        audit_required_errors = [
            (code, entry) for code, entry in self.taxonomy_map.items()
            if entry.audit_required
        ]
        
        security_errors = [
            (code, entry) for code, entry in self.taxonomy_map.items()
            if entry.category == ErrorCategory.SECURITY
        ]
        
        return {
            "compliance_impacting_errors": len(compliance_errors),
            "gdpr_relevant_errors": len([e for c, e in compliance_errors if e.gdpr_relevant]),
            "audit_required_errors": len(audit_required_errors),
            "security_errors": len(security_errors),
            "compliance_error_codes": [code for code, _ in compliance_errors],
            "security_error_codes": [code for code, _ in security_errors],
            "audit_required_codes": [code for code, _ in audit_required_errors]
        }

    def export_taxonomy_config(self) -> Dict[str, Any]:
        """Export complete taxonomy configuration"""
        return {
            "version": "1.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_entries": len(self.taxonomy_map),
            "taxonomy_entries": {
                code: {
                    "name": entry.name,
                    "description": entry.description,
                    "category": entry.category.value,
                    "subcategory": entry.subcategory.value,
                    "severity": entry.severity.value,
                    "impact": entry.impact.value,
                    "user_message": entry.user_message,
                    "user_action": entry.user_action,
                    "common_causes": entry.common_causes,
                    "troubleshooting_steps": entry.troubleshooting_steps,
                    "should_alert": entry.should_alert,
                    "alert_channels": entry.alert_channels,
                    "auto_recoverable": entry.auto_recoverable,
                    "customer_visible": entry.customer_visible,
                    "compliance_impact": entry.compliance_impact,
                    "audit_required": entry.audit_required,
                    "gdpr_relevant": entry.gdpr_relevant
                }
                for code, entry in self.taxonomy_map.items()
            }
        }

    def validate_taxonomy_completeness(self) -> Dict[str, Any]:
        """Validate that all error codes have taxonomy entries"""
        # Get all error codes from ErrorCode enum
        defined_error_codes = {code.value for code in ErrorCode}
        mapped_error_codes = set(self.taxonomy_map.keys())
        
        missing_codes = defined_error_codes - mapped_error_codes
        unmapped_codes = mapped_error_codes - defined_error_codes
        
        return {
            "total_defined_codes": len(defined_error_codes),
            "total_mapped_codes": len(mapped_error_codes),
            "missing_taxonomy_entries": list(missing_codes),
            "unmapped_codes": list(unmapped_codes),
            "coverage_percentage": ((len(mapped_error_codes & defined_error_codes) / len(defined_error_codes)) * 100) if defined_error_codes else 0,
            "validation_passed": len(missing_codes) == 0
        }

# Global service instance
error_taxonomy_service = ErrorTaxonomyService()

def get_error_taxonomy_service() -> ErrorTaxonomyService:
    """Get the global error taxonomy service instance"""
    return error_taxonomy_service

def classify_and_handle_error(error: Union[APIError, Exception], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Classify error and return comprehensive handling information"""
    service = get_error_taxonomy_service()
    
    # Classify the error
    taxonomy = service.classify_error(error)
    
    # Record the occurrence
    service.record_error_occurrence(taxonomy.error_code, context)
    
    # Determine if alerting is required
    if taxonomy.should_alert:
        logger.error(
            f"Alert required for error {taxonomy.error_code}: {taxonomy.name}",
            extra={
                "error_code": taxonomy.error_code,
                "severity": taxonomy.severity.value,
                "alert_channels": taxonomy.alert_channels,
                "escalation_required": taxonomy.escalation_required
            }
        )
    
    return {
        "taxonomy": asdict(taxonomy),
        "user_friendly": service.get_user_friendly_error(taxonomy.error_code, context),
        "troubleshooting": service.get_troubleshooting_guide(taxonomy.error_code) if not taxonomy.customer_visible else None,
        "requires_alert": taxonomy.should_alert,
        "requires_escalation": taxonomy.escalation_required
    }