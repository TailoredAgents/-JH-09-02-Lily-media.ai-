"""
Embedding Dimension Validation System
Provides comprehensive validation for embedding vectors to ensure consistency with OpenAI text-embedding-3-large model.
"""
import numpy as np
import logging
from typing import Optional, List, Dict, Any, Tuple, Union
from dataclasses import dataclass
from datetime import datetime, timezone
from backend.core.constants import EMBEDDINGS_DIMENSION

logger = logging.getLogger(__name__)

@dataclass
class EmbeddingValidationResult:
    """Result of embedding validation"""
    is_valid: bool
    dimension: int
    expected_dimension: int
    norm: float
    issues: List[str]
    metadata: Dict[str, Any]
    validation_time: float

@dataclass
class EmbeddingDimensionMetrics:
    """Metrics for embedding dimension validation"""
    total_validations: int = 0
    valid_embeddings: int = 0
    invalid_embeddings: int = 0
    dimension_mismatches: int = 0
    normalization_issues: int = 0
    zero_vector_issues: int = 0
    nan_issues: int = 0
    validation_errors: int = 0
    last_validation_at: Optional[datetime] = None
    avg_validation_time_ms: float = 0.0

class EmbeddingDimensionValidator:
    """
    Comprehensive embedding dimension validator for production-ready validation
    
    Features:
    - Dimension consistency checking (3072-dimensional vectors)
    - Vector normalization validation for cosine similarity
    - NaN and infinity detection
    - Zero vector detection
    - Batch validation for performance
    - Detailed metrics and monitoring
    - Real-time alerting for critical issues
    """
    
    def __init__(self, expected_dimension: int = EMBEDDINGS_DIMENSION):
        """
        Initialize the embedding validator
        
        Args:
            expected_dimension: Expected embedding dimension (default: 3072)
        """
        self.expected_dimension = expected_dimension
        self.metrics = EmbeddingDimensionMetrics()
        self._validation_threshold_norm_min = 0.95  # Minimum norm for normalized vectors
        self._validation_threshold_norm_max = 1.05  # Maximum norm for normalized vectors
        self._zero_vector_threshold = 1e-10  # Threshold for detecting zero vectors
        
        logger.info(f"EmbeddingDimensionValidator initialized for {expected_dimension}-dimensional vectors")
    
    def validate_embedding(
        self, 
        embedding: Union[np.ndarray, List[float]], 
        content_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> EmbeddingValidationResult:
        """
        Validate a single embedding vector
        
        Args:
            embedding: Embedding vector to validate
            content_id: Optional content identifier for logging
            metadata: Optional metadata for context
            
        Returns:
            EmbeddingValidationResult with validation details
        """
        start_time = datetime.now(timezone.utc)
        issues = []
        
        try:
            self.metrics.total_validations += 1
            
            # Convert to numpy array if needed
            if isinstance(embedding, list):
                embedding = np.array(embedding, dtype=np.float32)
            elif not isinstance(embedding, np.ndarray):
                issues.append(f"Invalid embedding type: {type(embedding)}")
                return self._create_invalid_result(embedding, issues, start_time, metadata)
            
            # Check dimension
            if embedding.ndim != 1:
                if embedding.ndim == 2 and embedding.shape[0] == 1:
                    embedding = embedding.flatten()
                else:
                    issues.append(f"Invalid embedding shape: {embedding.shape}, expected 1D vector")
            
            actual_dimension = embedding.shape[0] if embedding.ndim == 1 else 0
            if actual_dimension != self.expected_dimension:
                issues.append(f"Dimension mismatch: got {actual_dimension}, expected {self.expected_dimension}")
                self.metrics.dimension_mismatches += 1
            
            # Check for NaN or infinity values
            if np.any(np.isnan(embedding)):
                issues.append("Embedding contains NaN values")
                self.metrics.nan_issues += 1
            
            if np.any(np.isinf(embedding)):
                issues.append("Embedding contains infinite values")
                self.metrics.nan_issues += 1
            
            # Check for zero vector
            norm = np.linalg.norm(embedding)
            if norm < self._zero_vector_threshold:
                issues.append(f"Zero or near-zero vector detected (norm: {norm:.2e})")
                self.metrics.zero_vector_issues += 1
            
            # Check normalization for cosine similarity
            if norm < self._validation_threshold_norm_min or norm > self._validation_threshold_norm_max:
                issues.append(f"Vector not properly normalized (norm: {norm:.6f}, expected: ~1.0)")
                self.metrics.normalization_issues += 1
            
            # Check for suspicious patterns
            if actual_dimension == self.expected_dimension:
                self._check_embedding_patterns(embedding, issues)
            
            is_valid = len(issues) == 0
            
            if is_valid:
                self.metrics.valid_embeddings += 1
            else:
                self.metrics.invalid_embeddings += 1
                logger.warning(f"Embedding validation failed for content_id={content_id}: {', '.join(issues)}")
            
            validation_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self.metrics.last_validation_at = datetime.now(timezone.utc)
            
            # Update average validation time
            if self.metrics.total_validations > 0:
                self.metrics.avg_validation_time_ms = (
                    (self.metrics.avg_validation_time_ms * (self.metrics.total_validations - 1) + 
                     validation_time * 1000) / self.metrics.total_validations
                )
            
            return EmbeddingValidationResult(
                is_valid=is_valid,
                dimension=actual_dimension,
                expected_dimension=self.expected_dimension,
                norm=float(norm),
                issues=issues,
                metadata=metadata or {},
                validation_time=validation_time
            )
            
        except Exception as e:
            self.metrics.validation_errors += 1
            logger.error(f"Embedding validation error for content_id={content_id}: {e}")
            issues.append(f"Validation error: {str(e)}")
            return self._create_invalid_result(embedding, issues, start_time, metadata)
    
    def validate_embedding_batch(
        self, 
        embeddings: Union[np.ndarray, List[List[float]]], 
        content_ids: Optional[List[str]] = None,
        metadata_list: Optional[List[Dict[str, Any]]] = None
    ) -> List[EmbeddingValidationResult]:
        """
        Validate multiple embedding vectors efficiently
        
        Args:
            embeddings: Batch of embedding vectors
            content_ids: Optional list of content identifiers
            metadata_list: Optional list of metadata dictionaries
            
        Returns:
            List of EmbeddingValidationResults
        """
        if isinstance(embeddings, list):
            embeddings = np.array(embeddings, dtype=np.float32)
        
        if embeddings.ndim != 2:
            logger.error(f"Invalid embeddings batch shape: {embeddings.shape}, expected 2D array")
            return []
        
        batch_size = embeddings.shape[0]
        content_ids = content_ids or [None] * batch_size
        metadata_list = metadata_list or [{}] * batch_size
        
        results = []
        for i in range(batch_size):
            embedding = embeddings[i]
            content_id = content_ids[i] if i < len(content_ids) else None
            metadata = metadata_list[i] if i < len(metadata_list) else {}
            
            result = self.validate_embedding(embedding, content_id, metadata)
            results.append(result)
        
        # Log batch summary
        valid_count = sum(1 for r in results if r.is_valid)
        logger.info(f"Batch validation complete: {valid_count}/{len(results)} embeddings valid")
        
        return results
    
    def _check_embedding_patterns(self, embedding: np.ndarray, issues: List[str]) -> None:
        """Check for suspicious patterns in embedding vectors"""
        
        # Check for constant values
        if np.allclose(embedding, embedding[0]):
            issues.append("Embedding has constant values (suspicious pattern)")
        
        # Check for extreme sparsity
        zero_count = np.sum(np.abs(embedding) < 1e-6)
        sparsity = zero_count / len(embedding)
        if sparsity > 0.95:  # More than 95% zeros
            issues.append(f"Embedding is too sparse ({sparsity:.1%} zeros)")
        
        # Check for extreme values
        max_val = np.max(np.abs(embedding))
        if max_val > 10.0:  # Unusually large values for normalized embeddings
            issues.append(f"Embedding contains extreme values (max abs: {max_val:.3f})")
    
    def _create_invalid_result(
        self, 
        embedding: Any, 
        issues: List[str], 
        start_time: datetime,
        metadata: Optional[Dict[str, Any]]
    ) -> EmbeddingValidationResult:
        """Create an invalid validation result"""
        validation_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        try:
            if isinstance(embedding, (np.ndarray, list)):
                embedding_array = np.array(embedding) if isinstance(embedding, list) else embedding
                dimension = embedding_array.shape[0] if embedding_array.ndim == 1 else 0
                norm = float(np.linalg.norm(embedding_array)) if embedding_array.size > 0 else 0.0
            else:
                dimension = 0
                norm = 0.0
        except:
            dimension = 0
            norm = 0.0
        
        self.metrics.invalid_embeddings += 1
        self.metrics.last_validation_at = datetime.now(timezone.utc)
        
        return EmbeddingValidationResult(
            is_valid=False,
            dimension=dimension,
            expected_dimension=self.expected_dimension,
            norm=norm,
            issues=issues,
            metadata=metadata or {},
            validation_time=validation_time
        )
    
    def normalize_embedding(self, embedding: np.ndarray) -> Tuple[np.ndarray, bool]:
        """
        Normalize embedding vector for cosine similarity
        
        Args:
            embedding: Input embedding vector
            
        Returns:
            Tuple of (normalized_embedding, success_flag)
        """
        try:
            norm = np.linalg.norm(embedding)
            if norm < self._zero_vector_threshold:
                logger.warning("Cannot normalize zero vector")
                return embedding, False
            
            normalized = embedding / norm
            return normalized, True
            
        except Exception as e:
            logger.error(f"Error normalizing embedding: {e}")
            return embedding, False
    
    def get_validation_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive validation metrics
        
        Returns:
            Dictionary with validation statistics
        """
        success_rate = 0.0
        if self.metrics.total_validations > 0:
            success_rate = self.metrics.valid_embeddings / self.metrics.total_validations
        
        return {
            'total_validations': self.metrics.total_validations,
            'valid_embeddings': self.metrics.valid_embeddings,
            'invalid_embeddings': self.metrics.invalid_embeddings,
            'success_rate': success_rate,
            'dimension_mismatches': self.metrics.dimension_mismatches,
            'normalization_issues': self.metrics.normalization_issues,
            'zero_vector_issues': self.metrics.zero_vector_issues,
            'nan_issues': self.metrics.nan_issues,
            'validation_errors': self.metrics.validation_errors,
            'expected_dimension': self.expected_dimension,
            'last_validation_at': self.metrics.last_validation_at.isoformat() if self.metrics.last_validation_at else None,
            'avg_validation_time_ms': self.metrics.avg_validation_time_ms
        }
    
    def reset_metrics(self) -> None:
        """Reset validation metrics"""
        self.metrics = EmbeddingDimensionMetrics()
        logger.info("Embedding validation metrics reset")
    
    def validate_and_fix_embedding(
        self, 
        embedding: Union[np.ndarray, List[float]],
        content_id: Optional[str] = None,
        auto_normalize: bool = True
    ) -> Tuple[Optional[np.ndarray], EmbeddingValidationResult]:
        """
        Validate embedding and attempt to fix common issues
        
        Args:
            embedding: Input embedding
            content_id: Optional content identifier
            auto_normalize: Whether to automatically normalize the vector
            
        Returns:
            Tuple of (fixed_embedding or None, validation_result)
        """
        # Initial validation
        result = self.validate_embedding(embedding, content_id)
        
        if result.is_valid:
            return np.array(embedding, dtype=np.float32), result
        
        try:
            # Convert to numpy array
            fixed_embedding = np.array(embedding, dtype=np.float32)
            
            # Fix dimension issues by reshaping if possible
            if fixed_embedding.ndim == 2 and fixed_embedding.shape[0] == 1:
                fixed_embedding = fixed_embedding.flatten()
            
            # Check if dimension is still wrong
            if fixed_embedding.shape[0] != self.expected_dimension:
                logger.error(f"Cannot fix dimension mismatch: {fixed_embedding.shape[0]} != {self.expected_dimension}")
                return None, result
            
            # Fix NaN or infinity values
            if np.any(np.isnan(fixed_embedding)) or np.any(np.isinf(fixed_embedding)):
                logger.warning(f"Replacing NaN/Inf values in embedding for content_id={content_id}")
                fixed_embedding = np.nan_to_num(fixed_embedding, nan=0.0, posinf=1.0, neginf=-1.0)
            
            # Normalize if requested and vector is not zero
            if auto_normalize:
                norm = np.linalg.norm(fixed_embedding)
                if norm >= self._zero_vector_threshold:
                    fixed_embedding = fixed_embedding / norm
                else:
                    logger.warning(f"Cannot normalize zero vector for content_id={content_id}")
                    return None, result
            
            # Re-validate the fixed embedding
            fixed_result = self.validate_embedding(fixed_embedding, content_id)
            
            if fixed_result.is_valid:
                logger.info(f"Successfully fixed embedding for content_id={content_id}")
                return fixed_embedding, fixed_result
            else:
                logger.warning(f"Could not fix embedding for content_id={content_id}: {fixed_result.issues}")
                return None, fixed_result
                
        except Exception as e:
            logger.error(f"Error fixing embedding for content_id={content_id}: {e}")
            return None, result

# Global validator instance
_embedding_validator = None

def get_embedding_validator() -> EmbeddingDimensionValidator:
    """Get the global embedding validator instance (lazy initialization)"""
    global _embedding_validator
    if _embedding_validator is None:
        _embedding_validator = EmbeddingDimensionValidator()
    return _embedding_validator

def validate_embedding_dimension(
    embedding: Union[np.ndarray, List[float]],
    content_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> EmbeddingValidationResult:
    """
    Convenience function for validating embedding dimensions
    
    Args:
        embedding: Embedding vector to validate
        content_id: Optional content identifier
        metadata: Optional metadata
        
    Returns:
        EmbeddingValidationResult
    """
    validator = get_embedding_validator()
    return validator.validate_embedding(embedding, content_id, metadata)