"""
Unit tests for embedding dimension validation system
"""
import pytest
import numpy as np
from unittest.mock import patch
from datetime import datetime

from backend.core.embedding_validation import (
    EmbeddingDimensionValidator,
    EmbeddingValidationResult,
    get_embedding_validator,
    validate_embedding_dimension
)
from backend.core.constants import EMBEDDINGS_DIMENSION


class TestEmbeddingDimensionValidator:
    """Test cases for EmbeddingDimensionValidator"""
    
    def test_validator_initialization(self):
        """Test validator initializes with correct dimension"""
        validator = EmbeddingDimensionValidator()
        assert validator.expected_dimension == EMBEDDINGS_DIMENSION
        assert validator.metrics.total_validations == 0
        assert validator.metrics.valid_embeddings == 0
    
    def test_valid_embedding_validation(self):
        """Test validation of a valid embedding"""
        validator = EmbeddingDimensionValidator()
        
        # Create a valid normalized embedding
        embedding = np.random.randn(EMBEDDINGS_DIMENSION).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)  # Normalize
        
        result = validator.validate_embedding(embedding, "test_content_1")
        
        assert result.is_valid is True
        assert result.dimension == EMBEDDINGS_DIMENSION
        assert result.expected_dimension == EMBEDDINGS_DIMENSION
        assert len(result.issues) == 0
        assert 0.95 <= result.norm <= 1.05  # Should be normalized
        assert validator.metrics.valid_embeddings == 1
        assert validator.metrics.total_validations == 1
    
    def test_dimension_mismatch(self):
        """Test validation fails for wrong dimensions"""
        validator = EmbeddingDimensionValidator()
        
        # Create embedding with wrong dimension
        embedding = np.random.randn(1536).astype(np.float32)  # Wrong dimension
        
        result = validator.validate_embedding(embedding, "test_content_2")
        
        assert result.is_valid is False
        assert result.dimension == 1536
        assert result.expected_dimension == EMBEDDINGS_DIMENSION
        assert len(result.issues) > 0
        assert any("Dimension mismatch" in issue for issue in result.issues)
        assert validator.metrics.invalid_embeddings == 1
        assert validator.metrics.dimension_mismatches == 1
    
    def test_nan_values_detection(self):
        """Test detection of NaN values"""
        validator = EmbeddingDimensionValidator()
        
        # Create embedding with NaN values
        embedding = np.random.randn(EMBEDDINGS_DIMENSION).astype(np.float32)
        embedding[100] = np.nan
        
        result = validator.validate_embedding(embedding, "test_content_3")
        
        assert result.is_valid is False
        assert any("NaN values" in issue for issue in result.issues)
        assert validator.metrics.nan_issues == 1
    
    def test_infinity_values_detection(self):
        """Test detection of infinity values"""
        validator = EmbeddingDimensionValidator()
        
        # Create embedding with infinity values
        embedding = np.random.randn(EMBEDDINGS_DIMENSION).astype(np.float32)
        embedding[200] = np.inf
        
        result = validator.validate_embedding(embedding, "test_content_4")
        
        assert result.is_valid is False
        assert any("infinite values" in issue for issue in result.issues)
        assert validator.metrics.nan_issues == 1
    
    def test_zero_vector_detection(self):
        """Test detection of zero vectors"""
        validator = EmbeddingDimensionValidator()
        
        # Create zero embedding
        embedding = np.zeros(EMBEDDINGS_DIMENSION, dtype=np.float32)
        
        result = validator.validate_embedding(embedding, "test_content_5")
        
        assert result.is_valid is False
        assert any("Zero or near-zero vector" in issue for issue in result.issues)
        assert validator.metrics.zero_vector_issues == 1
    
    def test_normalization_issue_detection(self):
        """Test detection of unnormalized vectors"""
        validator = EmbeddingDimensionValidator()
        
        # Create unnormalized embedding
        embedding = np.random.randn(EMBEDDINGS_DIMENSION).astype(np.float32) * 10  # Large values
        
        result = validator.validate_embedding(embedding, "test_content_6")
        
        assert result.is_valid is False
        assert any("not properly normalized" in issue for issue in result.issues)
        assert validator.metrics.normalization_issues == 1
    
    def test_constant_values_pattern_detection(self):
        """Test detection of constant value patterns"""
        validator = EmbeddingDimensionValidator()
        
        # Create embedding with constant values
        embedding = np.full(EMBEDDINGS_DIMENSION, 0.5, dtype=np.float32)
        
        result = validator.validate_embedding(embedding, "test_content_7")
        
        assert result.is_valid is False
        assert any("constant values" in issue for issue in result.issues)
    
    def test_sparse_embedding_detection(self):
        """Test detection of overly sparse embeddings"""
        validator = EmbeddingDimensionValidator()
        
        # Create very sparse embedding (99% zeros)
        embedding = np.zeros(EMBEDDINGS_DIMENSION, dtype=np.float32)
        # Set only a few non-zero values
        embedding[:10] = 0.1
        embedding = embedding / np.linalg.norm(embedding)  # Normalize
        
        result = validator.validate_embedding(embedding, "test_content_8")
        
        assert result.is_valid is False
        assert any("too sparse" in issue for issue in result.issues)
    
    def test_extreme_values_detection(self):
        """Test detection of extreme values"""
        validator = EmbeddingDimensionValidator()
        
        # Create embedding with extreme values
        embedding = np.random.randn(EMBEDDINGS_DIMENSION).astype(np.float32) * 0.01
        embedding[0] = 50.0  # Extreme value
        
        result = validator.validate_embedding(embedding, "test_content_9")
        
        assert result.is_valid is False
        assert any("extreme values" in issue for issue in result.issues)
    
    def test_list_input_conversion(self):
        """Test validation with list input"""
        validator = EmbeddingDimensionValidator()
        
        # Create valid embedding as list
        embedding_array = np.random.randn(EMBEDDINGS_DIMENSION).astype(np.float32)
        embedding_array = embedding_array / np.linalg.norm(embedding_array)
        embedding_list = embedding_array.tolist()
        
        result = validator.validate_embedding(embedding_list, "test_content_10")
        
        assert result.is_valid is True
        assert result.dimension == EMBEDDINGS_DIMENSION
    
    def test_batch_validation(self):
        """Test batch validation"""
        validator = EmbeddingDimensionValidator()
        
        # Create batch of embeddings
        batch_size = 5
        embeddings = np.random.randn(batch_size, EMBEDDINGS_DIMENSION).astype(np.float32)
        
        # Normalize all embeddings
        for i in range(batch_size):
            embeddings[i] = embeddings[i] / np.linalg.norm(embeddings[i])
        
        content_ids = [f"batch_content_{i}" for i in range(batch_size)]
        
        results = validator.validate_embedding_batch(embeddings, content_ids)
        
        assert len(results) == batch_size
        assert all(result.is_valid for result in results)
        assert validator.metrics.total_validations == batch_size
        assert validator.metrics.valid_embeddings == batch_size
    
    def test_normalize_embedding(self):
        """Test embedding normalization"""
        validator = EmbeddingDimensionValidator()
        
        # Create unnormalized embedding
        embedding = np.random.randn(EMBEDDINGS_DIMENSION).astype(np.float32) * 5
        
        normalized, success = validator.normalize_embedding(embedding)
        
        assert success is True
        assert np.isclose(np.linalg.norm(normalized), 1.0, rtol=1e-5)
    
    def test_normalize_zero_vector_fails(self):
        """Test that normalizing zero vector fails"""
        validator = EmbeddingDimensionValidator()
        
        # Create zero embedding
        embedding = np.zeros(EMBEDDINGS_DIMENSION, dtype=np.float32)
        
        normalized, success = validator.normalize_embedding(embedding)
        
        assert success is False
        assert np.array_equal(normalized, embedding)  # Should return original
    
    def test_validate_and_fix_embedding_success(self):
        """Test validate and fix for fixable embedding"""
        validator = EmbeddingDimensionValidator()
        
        # Create unnormalized but otherwise valid embedding
        embedding = np.random.randn(EMBEDDINGS_DIMENSION).astype(np.float32) * 3
        
        fixed, result = validator.validate_and_fix_embedding(embedding, "test_fix_1")
        
        assert fixed is not None
        assert result.is_valid is True
        assert np.isclose(np.linalg.norm(fixed), 1.0, rtol=1e-5)
    
    def test_validate_and_fix_embedding_unfixable(self):
        """Test validate and fix for unfixable embedding"""
        validator = EmbeddingDimensionValidator()
        
        # Create embedding with wrong dimension (unfixable)
        embedding = np.random.randn(1536).astype(np.float32)
        
        fixed, result = validator.validate_and_fix_embedding(embedding, "test_fix_2")
        
        assert fixed is None
        assert result.is_valid is False
    
    def test_metrics_tracking(self):
        """Test metrics are properly tracked"""
        validator = EmbeddingDimensionValidator()
        
        # Valid embedding
        valid_embedding = np.random.randn(EMBEDDINGS_DIMENSION).astype(np.float32)
        valid_embedding = valid_embedding / np.linalg.norm(valid_embedding)
        validator.validate_embedding(valid_embedding)
        
        # Invalid embedding (wrong dimension)
        invalid_embedding = np.random.randn(1536).astype(np.float32)
        validator.validate_embedding(invalid_embedding)
        
        metrics = validator.get_validation_metrics()
        
        assert metrics['total_validations'] == 2
        assert metrics['valid_embeddings'] == 1
        assert metrics['invalid_embeddings'] == 1
        assert metrics['dimension_mismatches'] == 1
        assert metrics['success_rate'] == 0.5
        assert metrics['expected_dimension'] == EMBEDDINGS_DIMENSION
        assert metrics['last_validation_at'] is not None
    
    def test_reset_metrics(self):
        """Test metrics reset functionality"""
        validator = EmbeddingDimensionValidator()
        
        # Generate some metrics
        embedding = np.random.randn(EMBEDDINGS_DIMENSION).astype(np.float32)
        validator.validate_embedding(embedding)
        
        assert validator.metrics.total_validations > 0
        
        # Reset metrics
        validator.reset_metrics()
        
        assert validator.metrics.total_validations == 0
        assert validator.metrics.valid_embeddings == 0
        assert validator.metrics.invalid_embeddings == 0


class TestGlobalFunctions:
    """Test global convenience functions"""
    
    def test_get_embedding_validator_singleton(self):
        """Test that get_embedding_validator returns singleton"""
        validator1 = get_embedding_validator()
        validator2 = get_embedding_validator()
        
        assert validator1 is validator2
        assert isinstance(validator1, EmbeddingDimensionValidator)
    
    def test_validate_embedding_dimension_function(self):
        """Test convenience validation function"""
        embedding = np.random.randn(EMBEDDINGS_DIMENSION).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)
        
        result = validate_embedding_dimension(embedding, "test_function")
        
        assert isinstance(result, EmbeddingValidationResult)
        assert result.is_valid is True


class TestErrorHandling:
    """Test error handling in validation"""
    
    def test_invalid_embedding_type(self):
        """Test handling of invalid embedding types"""
        validator = EmbeddingDimensionValidator()
        
        # Test with invalid type
        result = validator.validate_embedding("not_an_array", "test_invalid")
        
        assert result.is_valid is False
        assert any("Invalid embedding type" in issue for issue in result.issues)
    
    def test_empty_embedding_batch(self):
        """Test handling of empty batch"""
        validator = EmbeddingDimensionValidator()
        
        results = validator.validate_embedding_batch([])
        
        assert len(results) == 0
    
    def test_validation_with_exception(self):
        """Test handling of exceptions during validation"""
        validator = EmbeddingDimensionValidator()
        
        # Mock a validation that raises an exception
        with patch.object(validator, 'metrics') as mock_metrics:
            mock_metrics.total_validations = 0  # This will cause division by zero in avg calculation
            
            # This should still work without crashing
            embedding = np.random.randn(EMBEDDINGS_DIMENSION).astype(np.float32)
            result = validator.validate_embedding(embedding)
            
            assert isinstance(result, EmbeddingValidationResult)


@pytest.fixture
def sample_valid_embedding():
    """Fixture providing a valid normalized embedding"""
    embedding = np.random.randn(EMBEDDINGS_DIMENSION).astype(np.float32)
    return embedding / np.linalg.norm(embedding)


@pytest.fixture
def sample_invalid_embedding():
    """Fixture providing an invalid embedding (wrong dimension)"""
    return np.random.randn(1536).astype(np.float32)


def test_integration_with_constants():
    """Test that validation uses the correct dimension constant"""
    validator = EmbeddingDimensionValidator()
    assert validator.expected_dimension == EMBEDDINGS_DIMENSION == 3072