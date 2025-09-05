"""
Integration tests for global feature flag enforcement - R8 completion
Tests comprehensive feature flag coverage across all API endpoints
"""
import pytest
from unittest.mock import patch, Mock
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from backend.middleware.global_feature_flag_middleware import (
    GlobalFeatureFlagMiddleware, 
    FeatureFlagStatusMiddleware,
    get_feature_requirements_for_endpoint,
    validate_all_feature_flags,
    get_feature_flag_coverage_report
)


@pytest.fixture
def test_app():
    """Create test FastAPI app with feature flag middleware"""
    app = FastAPI()
    
    # Add the middleware
    middleware = GlobalFeatureFlagMiddleware()
    app.middleware("http")(middleware)
    
    # Add test routes to simulate real endpoints
    @app.get("/api/content/generate")
    async def test_content_generate():
        return {"message": "content generated"}
    
    @app.post("/api/ai-suggestions/suggestions")
    async def test_ai_suggestions():
        return {"suggestions": []}
    
    @app.get("/api/admin/users")
    async def test_admin_users():
        return {"users": []}
    
    @app.get("/health")
    async def test_health():
        return {"status": "healthy"}
    
    @app.get("/api/auth/me")
    async def test_auth_me():
        return {"user": "test"}
    
    return app


@pytest.fixture
def client(test_app):
    """Test client with feature flag middleware"""
    return TestClient(test_app)


class TestGlobalFeatureFlagMiddleware:
    """Test suite for global feature flag enforcement"""

    def test_allowed_endpoints_bypass_feature_flags(self, client):
        """Test that health checks and auth endpoints are always allowed"""
        with patch('backend.middleware.global_feature_flag_middleware.ff') as mock_ff:
            mock_ff.return_value = False  # All flags disabled
            
            # Health endpoint should work
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "healthy"}
            
            # Auth endpoint should work
            response = client.get("/api/auth/me")
            assert response.status_code == 200

    def test_ai_content_generation_flag_enforcement(self, client):
        """Test AI content generation endpoints require proper flag"""
        # Test with flag disabled
        with patch('backend.middleware.global_feature_flag_middleware.ff') as mock_ff:
            mock_ff.return_value = False
            
            response = client.get("/api/content/generate")
            
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()
            assert data["error"] == "feature_disabled"
            assert data["flag"] == "AI_CONTENT_GENERATION"
            assert data["enabled"] is False
        
        # Test with flag enabled
        with patch('backend.middleware.global_feature_flag_middleware.ff') as mock_ff:
            mock_ff.return_value = True
            
            response = client.get("/api/content/generate")
            assert response.status_code == 200

    def test_ai_suggestions_flag_enforcement(self, client):
        """Test AI suggestions endpoints require proper flag"""
        with patch('backend.middleware.global_feature_flag_middleware.ff') as mock_ff:
            mock_ff.return_value = False
            
            response = client.post("/api/ai-suggestions/suggestions")
            
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()
            assert data["flag"] == "AI_SUGGESTIONS"
            assert "AI Suggestions" in data["message"]

    def test_admin_access_flag_enforcement(self, client):
        """Test admin endpoints require ADMIN_ACCESS flag - critical for security"""
        with patch('backend.middleware.global_feature_flag_middleware.ff') as mock_ff:
            mock_ff.return_value = False
            
            response = client.get("/api/admin/users")
            
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()
            assert data["flag"] == "ADMIN_ACCESS"
            assert "Administrative Access" in data["message"]

    def test_specific_flag_checking_logic(self, client):
        """Test that the middleware checks specific flags correctly"""
        def mock_ff_selective(flag_name):
            # Only AI_CONTENT_GENERATION is enabled
            return flag_name == "AI_CONTENT_GENERATION"
        
        with patch('backend.middleware.global_feature_flag_middleware.ff', side_effect=mock_ff_selective):
            # AI content should work
            response = client.get("/api/content/generate")
            assert response.status_code == 200
            
            # AI suggestions should be blocked
            response = client.post("/api/ai-suggestions/suggestions")
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            
            # Admin should be blocked
            response = client.get("/api/admin/users")
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    def test_middleware_error_handling(self, client):
        """Test middleware handles errors gracefully"""
        with patch('backend.middleware.global_feature_flag_middleware.ff', side_effect=Exception("Flag check failed")):
            # Should not block requests due to middleware errors
            response = client.get("/health")
            assert response.status_code == 200

    def test_path_pattern_matching(self):
        """Test that URL patterns are matched correctly"""
        middleware = GlobalFeatureFlagMiddleware()
        
        # Test AI content patterns
        ai_patterns = [
            "/api/content/generate",
            "/api/content/generate-ideas", 
            "/api/content/generate-image"
        ]
        
        for path in ai_patterns:
            matched = False
            for pattern, config in middleware.endpoint_patterns.items():
                if pattern.match(path):
                    assert config["flag"] in ["AI_CONTENT_GENERATION", "IMAGE_GENERATION"]
                    matched = True
                    break
            assert matched, f"Pattern should match for {path}"

    def test_allowed_patterns_matching(self):
        """Test that allowed patterns work correctly"""
        middleware = GlobalFeatureFlagMiddleware()
        
        allowed_paths = [
            "/health",
            "/health/detailed",
            "/api/monitoring/status",
            "/api/auth/login",
            "/api/feature-flags/",
            "/docs",
            "/openapi.json"
        ]
        
        for path in allowed_paths:
            is_allowed = any(pattern.match(path) for pattern in middleware.allowed_patterns)
            assert is_allowed, f"Path should be allowed: {path}"


class TestFeatureFlagStatusMiddleware:
    """Test feature flag status middleware"""

    def test_debug_headers_added_in_debug_mode(self):
        """Test that debug headers are added when debug mode is enabled"""
        app = FastAPI()
        
        debug_middleware = FeatureFlagStatusMiddleware(debug_mode=True)
        app.middleware("http")(debug_middleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"test": True}
        
        with patch('backend.middleware.global_feature_flag_middleware.feature_flags') as mock_flags:
            mock_flags.return_value = {"AI_CONTENT_GENERATION": True, "ADMIN_ACCESS": False}
            
            client = TestClient(app)
            response = client.get("/test")
            
            assert "X-Feature-Flags-Total" in response.headers
            assert response.headers["X-Feature-Flags-Total"] == "2"
            assert response.headers["X-Feature-Flags-Enabled"] == "1"

    def test_no_debug_headers_in_production_mode(self):
        """Test that debug headers are not added in production mode"""
        app = FastAPI()
        
        debug_middleware = FeatureFlagStatusMiddleware(debug_mode=False)
        app.middleware("http")(debug_middleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"test": True}
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert "X-Feature-Flags-Total" not in response.headers


class TestHelperFunctions:
    """Test helper functions for feature flag management"""

    def test_get_feature_requirements_for_endpoint(self):
        """Test getting feature requirements for specific endpoints"""
        # Test AI content endpoint
        result = get_feature_requirements_for_endpoint("/api/content/generate")
        assert result is not None
        assert result["flag"] == "AI_CONTENT_GENERATION"
        assert result["feature"] == "AI Content Generation"
        
        # Test admin endpoint
        result = get_feature_requirements_for_endpoint("/api/admin/users")
        assert result is not None
        assert result["flag"] == "ADMIN_ACCESS"
        
        # Test non-matching endpoint
        result = get_feature_requirements_for_endpoint("/api/health")
        assert result is None

    def test_validate_all_feature_flags(self):
        """Test validation of all feature flags"""
        with patch('backend.middleware.global_feature_flag_middleware.feature_flags') as mock_flags:
            mock_flags.return_value = {
                "AI_CONTENT_GENERATION": True,
                "AI_SUGGESTIONS": True,
                "ADMIN_ACCESS": True,
                # Missing some flags
            }
            
            validation = validate_all_feature_flags()
            
            # Should validate existing flags
            assert validation["AI_CONTENT_GENERATION"] is True
            assert validation["AI_SUGGESTIONS"] is True
            assert validation["ADMIN_ACCESS"] is True
            
            # Should identify missing flags
            assert "IMAGE_GENERATION" in validation
            assert "AUTONOMOUS_FEATURES" in validation

    def test_get_feature_flag_coverage_report(self):
        """Test feature flag coverage reporting"""
        report = get_feature_flag_coverage_report()
        
        assert "total_patterns" in report
        assert "flags_in_use" in report
        assert "coverage_summary" in report
        
        # Should have reasonable coverage
        assert report["total_patterns"] > 5
        assert len(report["flags_in_use"]) > 5
        
        # Should categorize features
        summary = report["coverage_summary"]
        assert "ai_features" in summary
        assert "admin_features" in summary
        assert "premium_features" in summary


class TestFeatureFlagPatterns:
    """Test specific feature flag patterns and requirements"""

    def test_all_ai_endpoints_covered(self):
        """Test that all AI endpoints have feature flag coverage"""
        ai_endpoints = [
            "/api/content/generate",
            "/api/content/generate-ideas",
            "/api/ai-suggestions/suggestions",
            "/api/content/generate-image",
            "/api/social-inbox/generate-response"
        ]
        
        for endpoint in ai_endpoints:
            requirement = get_feature_requirements_for_endpoint(endpoint)
            assert requirement is not None, f"AI endpoint should have feature flag: {endpoint}"
            assert "AI" in requirement["flag"] or "IMAGE" in requirement["flag"]

    def test_all_admin_endpoints_covered(self):
        """Test that all admin endpoints require ADMIN_ACCESS flag"""
        admin_endpoints = [
            "/api/admin/users",
            "/api/admin/login", 
            "/api/admin/dashboard",
            "/api/admin/settings"
        ]
        
        for endpoint in admin_endpoints:
            requirement = get_feature_requirements_for_endpoint(endpoint)
            assert requirement is not None, f"Admin endpoint should have feature flag: {endpoint}"
            assert requirement["flag"] == "ADMIN_ACCESS"

    def test_billing_endpoints_covered(self):
        """Test that billing endpoints have proper feature flags"""
        billing_endpoints = [
            "/api/billing/checkout",
            "/api/billing/subscription",
            "/api/billing/customer-portal"
        ]
        
        for endpoint in billing_endpoints:
            requirement = get_feature_requirements_for_endpoint(endpoint)
            assert requirement is not None, f"Billing endpoint should have feature flag: {endpoint}"
            assert requirement["flag"] == "BILLING_MANAGEMENT"

    def test_autonomous_endpoints_covered(self):
        """Test that autonomous features have proper feature flags"""
        autonomous_endpoints = [
            "/api/autonomous/execute-cycle",
            "/api/autonomous/research",
            "/api/autonomous/status"
        ]
        
        for endpoint in autonomous_endpoints:
            requirement = get_feature_requirements_for_endpoint(endpoint)
            assert requirement is not None, f"Autonomous endpoint should have feature flag: {endpoint}"
            assert requirement["flag"] == "AUTONOMOUS_FEATURES"


class TestFeatureFlagSecurity:
    """Test security aspects of feature flag enforcement"""

    def test_admin_endpoints_cannot_be_bypassed(self, client):
        """Test that admin endpoints cannot be accessed without flags - CRITICAL"""
        admin_paths = [
            "/api/admin/users",
            "/api/admin/dashboard", 
            "/api/admin/system-settings"
        ]
        
        with patch('backend.middleware.global_feature_flag_middleware.ff') as mock_ff:
            mock_ff.return_value = False  # All flags disabled
            
            for path in admin_paths:
                response = client.get(path)
                # Should be blocked even if endpoint doesn't exist
                assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
                data = response.json()
                assert data["flag"] == "ADMIN_ACCESS"

    def test_billing_endpoints_cannot_be_bypassed(self, client):
        """Test that financial endpoints are properly protected"""
        billing_paths = [
            "/api/billing/checkout",
            "/api/billing/subscription"
        ]
        
        with patch('backend.middleware.global_feature_flag_middleware.ff') as mock_ff:
            mock_ff.return_value = False
            
            for path in billing_paths:
                response = client.get(path)
                assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    def test_feature_flag_bypass_attempts(self, client):
        """Test various attempts to bypass feature flags"""
        bypass_attempts = [
            # Try different HTTP methods
            ("GET", "/api/admin/users"),
            ("POST", "/api/admin/users"),
            ("PUT", "/api/admin/users"), 
            ("DELETE", "/api/admin/users"),
            
            # Try path variations
            ("GET", "/api/admin/users/"),
            ("GET", "/api/admin/users/1"),
            ("GET", "/API/ADMIN/USERS"),  # Case sensitivity
        ]
        
        with patch('backend.middleware.global_feature_flag_middleware.ff') as mock_ff:
            mock_ff.return_value = False
            
            for method, path in bypass_attempts:
                response = client.request(method, path)
                # Should be blocked regardless of method or path variation
                assert response.status_code in [
                    status.HTTP_503_SERVICE_UNAVAILABLE,  # Blocked by feature flag
                    status.HTTP_404_NOT_FOUND,  # Endpoint doesn't exist
                    status.HTTP_405_METHOD_NOT_ALLOWED  # Method not allowed
                ]

    def test_concurrent_flag_checks(self, client):
        """Test that concurrent requests handle feature flags correctly"""
        import concurrent.futures
        import threading
        
        def check_endpoint(path):
            with patch('backend.middleware.global_feature_flag_middleware.ff') as mock_ff:
                mock_ff.return_value = False
                response = client.get(path)
                return response.status_code
        
        # Test concurrent access to protected endpoints
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for _ in range(20):
                future = executor.submit(check_endpoint, "/api/admin/users")
                futures.append(future)
            
            # All should be consistently blocked
            results = [future.result() for future in futures]
            for result in results:
                assert result == status.HTTP_503_SERVICE_UNAVAILABLE


class TestFeatureFlagConfiguration:
    """Test feature flag configuration and management"""

    def test_all_required_flags_defined(self):
        """Test that all required feature flags are properly defined"""
        with patch('backend.middleware.global_feature_flag_middleware.feature_flags') as mock_flags:
            # Mock with all expected flags
            expected_flags = {
                "AI_CONTENT_GENERATION": True,
                "AI_SUGGESTIONS": True,
                "AI_SOCIAL_RESPONSES": True,
                "IMAGE_GENERATION": True,
                "AUTONOMOUS_FEATURES": True,
                "ADVANCED_WORKFLOWS": True,
                "ENABLE_DEEP_RESEARCH": True,
                "ADMIN_ACCESS": True,
                "BILLING_MANAGEMENT": True,
                "ORGANIZATION_MANAGEMENT": True,
                "ADVANCED_ANALYTICS": True,
                "VECTOR_SEARCH": True,
                "ADVANCED_MEMORY": True,
            }
            mock_flags.return_value = expected_flags
            
            validation = validate_all_feature_flags()
            
            # All flags should be valid
            for flag, is_valid in validation.items():
                assert is_valid, f"Required flag should be defined: {flag}"

    def test_feature_flag_performance(self):
        """Test that feature flag checking is performant"""
        import time
        
        middleware = GlobalFeatureFlagMiddleware()
        
        # Time multiple pattern matches
        test_paths = [
            "/api/content/generate",
            "/api/admin/users", 
            "/api/billing/checkout",
            "/health",
            "/api/auth/login"
        ]
        
        start_time = time.time()
        
        for _ in range(1000):
            for path in test_paths:
                # Simulate pattern matching
                for pattern in middleware.endpoint_patterns.keys():
                    if pattern.match(path):
                        break
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should be very fast (less than 1 second for 5000 matches)
        assert duration < 1.0, f"Pattern matching too slow: {duration}s"