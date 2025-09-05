"""
Unit tests for feature flag enforcement middleware - critical for API gating
"""
import pytest
from unittest.mock import patch, Mock
from fastapi import HTTPException, status

from backend.middleware.feature_flag_enforcement import (
    FeatureFlagDependencies,
    require_flag,
    require_any_flag,
    require_all_flags,
    feature_flag_required,
    get_enabled_flags,
    is_feature_enabled,
    get_flag_status_report
)


class TestFeatureFlagDependencies:
    """Test suite for feature flag dependency functions"""

    def test_require_flag_enabled_success(self):
        """Test successful flag requirement when flag is enabled"""
        with patch('backend.middleware.feature_flag_enforcement.ff', return_value=True):
            dependency = FeatureFlagDependencies.require_flag("WORKFLOW_V2")
            
            # Should not raise exception
            result = dependency()
            assert result is None

    def test_require_flag_disabled_raises_exception(self):
        """Test that disabled flag raises HTTPException"""
        with patch('backend.middleware.feature_flag_enforcement.ff', return_value=False):
            dependency = FeatureFlagDependencies.require_flag("DISABLED_FEATURE")
            
            with pytest.raises(HTTPException) as exc_info:
                dependency()
            
            assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            assert exc_info.value.detail["error"] == "feature_disabled"
            assert exc_info.value.detail["flag"] == "DISABLED_FEATURE"
            assert not exc_info.value.detail["enabled"]

    def test_require_flag_custom_error_message(self):
        """Test custom error message in flag requirement"""
        custom_message = "This experimental feature is not available"
        
        with patch('backend.middleware.feature_flag_enforcement.ff', return_value=False):
            dependency = FeatureFlagDependencies.require_flag(
                "EXPERIMENTAL_FEATURE", 
                error_message=custom_message
            )
            
            with pytest.raises(HTTPException) as exc_info:
                dependency()
            
            assert exc_info.value.detail["message"] == custom_message

    def test_require_any_flag_one_enabled_success(self):
        """Test require_any_flag succeeds when at least one flag is enabled"""
        def mock_ff(flag_name):
            return flag_name == "FEATURE_B"  # Only FEATURE_B is enabled
        
        with patch('backend.middleware.feature_flag_enforcement.ff', side_effect=mock_ff):
            dependency = FeatureFlagDependencies.require_any_flag("FEATURE_A", "FEATURE_B", "FEATURE_C")
            
            # Should not raise exception
            result = dependency()
            assert result is None

    def test_require_any_flag_none_enabled_raises_exception(self):
        """Test require_any_flag raises exception when no flags are enabled"""
        with patch('backend.middleware.feature_flag_enforcement.ff', return_value=False):
            dependency = FeatureFlagDependencies.require_any_flag("FEATURE_A", "FEATURE_B")
            
            with pytest.raises(HTTPException) as exc_info:
                dependency()
            
            assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            assert exc_info.value.detail["error"] == "features_disabled"
            assert "FEATURE_A" in exc_info.value.detail["message"]
            assert "FEATURE_B" in exc_info.value.detail["message"]
            assert exc_info.value.detail["enabled_flags"] == []

    def test_require_all_flags_all_enabled_success(self):
        """Test require_all_flags succeeds when all flags are enabled"""
        with patch('backend.middleware.feature_flag_enforcement.ff', return_value=True):
            dependency = FeatureFlagDependencies.require_all_flags("FEATURE_A", "FEATURE_B")
            
            # Should not raise exception
            result = dependency()
            assert result is None

    def test_require_all_flags_some_disabled_raises_exception(self):
        """Test require_all_flags raises exception when some flags are disabled"""
        def mock_ff(flag_name):
            return flag_name == "FEATURE_A"  # Only FEATURE_A is enabled
        
        with patch('backend.middleware.feature_flag_enforcement.ff', side_effect=mock_ff):
            dependency = FeatureFlagDependencies.require_all_flags("FEATURE_A", "FEATURE_B", "FEATURE_C")
            
            with pytest.raises(HTTPException) as exc_info:
                dependency()
            
            assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            assert exc_info.value.detail["error"] == "features_disabled"
            assert "FEATURE_B" in exc_info.value.detail["disabled_flags"]
            assert "FEATURE_C" in exc_info.value.detail["disabled_flags"]


class TestConvenienceFunctions:
    """Test convenience functions for feature flag checking"""

    def test_require_flag_convenience_function(self):
        """Test the convenience require_flag function"""
        with patch('backend.middleware.feature_flag_enforcement.ff', return_value=True):
            dependency = require_flag("TEST_FEATURE")
            result = dependency()
            assert result is None

    def test_require_any_flag_convenience_function(self):
        """Test the convenience require_any_flag function"""
        with patch('backend.middleware.feature_flag_enforcement.ff', return_value=True):
            dependency = require_any_flag("FEATURE_A", "FEATURE_B")
            result = dependency()
            assert result is None

    def test_require_all_flags_convenience_function(self):
        """Test the convenience require_all_flags function"""
        with patch('backend.middleware.feature_flag_enforcement.ff', return_value=True):
            dependency = require_all_flags("FEATURE_A", "FEATURE_B")
            result = dependency()
            assert result is None


class TestFunctionDecorator:
    """Test the function decorator for non-FastAPI usage"""

    def test_feature_flag_required_decorator_enabled(self):
        """Test decorator allows execution when flag is enabled"""
        @feature_flag_required("ENABLED_FEATURE")
        def test_function():
            return "success"
        
        with patch('backend.middleware.feature_flag_enforcement.ff', return_value=True):
            result = test_function()
            assert result == "success"

    def test_feature_flag_required_decorator_disabled(self):
        """Test decorator raises exception when flag is disabled"""
        @feature_flag_required("DISABLED_FEATURE")
        def test_function():
            return "success"
        
        with patch('backend.middleware.feature_flag_enforcement.ff', return_value=False):
            with pytest.raises(RuntimeError) as exc_info:
                test_function()
            
            assert "DISABLED_FEATURE" in str(exc_info.value)

    def test_feature_flag_required_decorator_custom_message(self):
        """Test decorator with custom error message"""
        custom_message = "Custom feature not available"
        
        @feature_flag_required("DISABLED_FEATURE", error_message=custom_message)
        def test_function():
            return "success"
        
        with patch('backend.middleware.feature_flag_enforcement.ff', return_value=False):
            with pytest.raises(RuntimeError) as exc_info:
                test_function()
            
            assert str(exc_info.value) == custom_message

    def test_feature_flag_required_decorator_preserves_function_metadata(self):
        """Test that decorator preserves function metadata"""
        @feature_flag_required("TEST_FEATURE")
        def documented_function():
            """This function has documentation"""
            return "success"
        
        with patch('backend.middleware.feature_flag_enforcement.ff', return_value=True):
            assert documented_function.__name__ == "documented_function"
            assert "documentation" in documented_function.__doc__


class TestUtilityFunctions:
    """Test utility functions for feature flag status"""

    def test_get_enabled_flags(self):
        """Test getting all enabled flags"""
        mock_flags = {
            "WORKFLOW_V2": True,
            "ENABLE_DEEP_RESEARCH": False,
            "IMAGE_GENERATION": True,
            "AUTH0_ENABLED": False
        }
        
        with patch('backend.middleware.feature_flag_enforcement.feature_flags', return_value=mock_flags):
            result = get_enabled_flags()
            assert result == mock_flags

    def test_is_feature_enabled_true(self):
        """Test checking if specific feature is enabled (true case)"""
        with patch('backend.middleware.feature_flag_enforcement.ff', return_value=True):
            result = is_feature_enabled("WORKFLOW_V2")
            assert result is True

    def test_is_feature_enabled_false(self):
        """Test checking if specific feature is enabled (false case)"""
        with patch('backend.middleware.feature_flag_enforcement.ff', return_value=False):
            result = is_feature_enabled("DISABLED_FEATURE")
            assert result is False

    def test_get_flag_status_report(self):
        """Test getting comprehensive flag status report"""
        mock_flags = {
            "WORKFLOW_V2": True,
            "ENABLE_DEEP_RESEARCH": False,
            "IMAGE_GENERATION": True,
            "AUTH0_ENABLED": False,
            "USE_STUB_INTEGRATIONS": True
        }
        
        with patch('backend.middleware.feature_flag_enforcement.feature_flags', return_value=mock_flags):
            result = get_flag_status_report()
            
            assert result["total_flags"] == 5
            assert result["enabled_flags"] == 3
            assert result["disabled_flags"] == 2
            assert result["flags"] == mock_flags
            
            # Check summary fields
            summary = result["summary"]
            assert summary["auth0_disabled"] is True  # AUTH0_ENABLED is False
            assert summary["workflow_v2_enabled"] is True
            assert summary["deep_research_available"] is False
            assert summary["using_stub_integrations"] is True


class TestPreDefinedDependencies:
    """Test pre-defined convenience dependencies"""

    def test_require_workflow_v2_enabled(self):
        """Test require_workflow_v2 dependency when enabled"""
        with patch('backend.middleware.feature_flag_enforcement.ff') as mock_ff:
            mock_ff.return_value = True
            
            from backend.middleware.feature_flag_enforcement import require_workflow_v2
            dependency = require_workflow_v2
            result = dependency()
            
            assert result is None
            mock_ff.assert_called_with("WORKFLOW_V2")

    def test_require_deep_research_enabled(self):
        """Test require_deep_research dependency when enabled"""
        with patch('backend.middleware.feature_flag_enforcement.ff') as mock_ff:
            mock_ff.return_value = True
            
            from backend.middleware.feature_flag_enforcement import require_deep_research
            dependency = require_deep_research
            result = dependency()
            
            assert result is None
            mock_ff.assert_called_with("ENABLE_DEEP_RESEARCH")


class TestFeatureFlagLogging:
    """Test logging behavior in feature flag enforcement"""

    @patch('backend.middleware.feature_flag_enforcement.logger')
    def test_feature_flag_failure_logging(self, mock_logger):
        """Test that feature flag failures are logged"""
        with patch('backend.middleware.feature_flag_enforcement.ff', return_value=False):
            dependency = require_flag("DISABLED_FEATURE")
            
            with pytest.raises(HTTPException):
                dependency()
            
            mock_logger.warning.assert_called_once()
            warning_message = mock_logger.warning.call_args[0][0]
            assert "DISABLED_FEATURE" in warning_message

    @patch('backend.middleware.feature_flag_enforcement.logger')
    def test_function_decorator_logging(self, mock_logger):
        """Test that function decorator failures are logged"""
        @feature_flag_required("DISABLED_FEATURE")
        def test_function():
            return "success"
        
        with patch('backend.middleware.feature_flag_enforcement.ff', return_value=False):
            with pytest.raises(RuntimeError):
                test_function()
            
            mock_logger.warning.assert_called_once()
            warning_message = mock_logger.warning.call_args[0][0]
            assert "DISABLED_FEATURE" in warning_message
            assert "test_function" in warning_message


class TestFeatureFlagErrorDetails:
    """Test detailed error information in exceptions"""

    def test_error_detail_structure_single_flag(self):
        """Test error detail structure for single flag requirement"""
        with patch('backend.middleware.feature_flag_enforcement.ff', return_value=False):
            dependency = require_flag("TEST_FEATURE")
            
            with pytest.raises(HTTPException) as exc_info:
                dependency()
            
            detail = exc_info.value.detail
            assert isinstance(detail, dict)
            assert detail["error"] == "feature_disabled"
            assert detail["flag"] == "TEST_FEATURE"
            assert detail["enabled"] is False
            assert "message" in detail

    def test_error_detail_structure_multiple_flags(self):
        """Test error detail structure for multiple flag requirements"""
        with patch('backend.middleware.feature_flag_enforcement.ff', return_value=False):
            dependency = require_any_flag("FEATURE_A", "FEATURE_B")
            
            with pytest.raises(HTTPException) as exc_info:
                dependency()
            
            detail = exc_info.value.detail
            assert isinstance(detail, dict)
            assert detail["error"] == "features_disabled"
            assert "required_flags" in detail
            assert "enabled_flags" in detail
            assert detail["required_flags"] == ["FEATURE_A", "FEATURE_B"]
            assert detail["enabled_flags"] == []

    def test_partial_flag_enablement_details(self):
        """Test error details when some flags are enabled"""
        def mock_ff(flag_name):
            return flag_name == "FEATURE_A"
        
        with patch('backend.middleware.feature_flag_enforcement.ff', side_effect=mock_ff):
            dependency = require_all_flags("FEATURE_A", "FEATURE_B", "FEATURE_C")
            
            with pytest.raises(HTTPException) as exc_info:
                dependency()
            
            detail = exc_info.value.detail
            assert "disabled_flags" in detail
            assert set(detail["disabled_flags"]) == {"FEATURE_B", "FEATURE_C"}
            assert detail["required_flags"] == ["FEATURE_A", "FEATURE_B", "FEATURE_C"]


class TestFeatureFlagIntegration:
    """Integration tests for feature flag enforcement"""

    def test_real_feature_flag_integration(self):
        """Test with actual feature flag configuration (without mocking)"""
        # Test that actual flags from config work
        from backend.core.feature_flags import ff
        
        # These should not raise exceptions as they use real config
        workflow_enabled = ff("WORKFLOW_V2")
        auth0_enabled = ff("AUTH0_ENABLED") 
        
        # Just verify they return boolean values
        assert isinstance(workflow_enabled, bool)
        assert isinstance(auth0_enabled, bool)

    def test_unknown_flag_returns_false(self):
        """Test that unknown flags default to False"""
        from backend.core.feature_flags import ff
        
        result = ff("UNKNOWN_NONEXISTENT_FLAG")
        assert result is False

    def test_flag_configuration_consistency(self):
        """Test that flag configuration is consistent"""
        from backend.core.feature_flags import feature_flags
        
        flags = feature_flags()
        
        # Should contain expected default flags
        expected_flags = ["WORKFLOW_V2", "AUTH0_ENABLED", "IMAGE_GENERATION"]
        for flag in expected_flags:
            assert flag in flags
            assert isinstance(flags[flag], bool)