"""
OpenAI Embedding Service for Content Memory System
"""
import asyncio
import numpy as np
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timezone
import time
import hashlib
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI, AsyncOpenAI
# OpenAI v1.x has different error structure - using base exceptions
try:
    from openai import RateLimitError, APIError
except ImportError:
    # Fallback for compatibility
    RateLimitError = Exception
    APIError = Exception

from backend.core.config import get_settings
from backend.core.vector_store import vector_store
from backend.core.embedding_validation import get_embedding_validator, EmbeddingValidationResult
from backend.core.monitoring import monitoring_service

# Get logger (use application's logging configuration)
logger = logging.getLogger(__name__)

settings = get_settings()

@dataclass
class EmbeddingResult:
    """Result of an embedding operation"""
    content_id: str
    content: str
    embedding: Optional[np.ndarray]
    metadata: Dict[str, Any]
    success: bool
    error: Optional[str] = None
    processing_time: float = 0.0

class EmbeddingService:
    """
    OpenAI Embedding Service with batch processing and error handling
    
    Features:
    - Batch embedding generation for efficiency
    - Rate limit handling with exponential backoff
    - Text preprocessing and chunking
    - Embedding normalization and validation
    - Integration with FAISS vector store
    - Async support for better performance
    """
    
    def __init__(self):
        """Initialize the embedding service"""
        self.openai_client = OpenAI(api_key=settings.openai_api_key)
        self.async_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model_name = "text-embedding-3-large"
        from backend.core.constants import EMBEDDINGS_DIMENSION
        self.dimension = EMBEDDINGS_DIMENSION  # text-embedding-3-large uses 3072 dimensions
        self.max_tokens = 8192  # Maximum tokens for text-embedding-3-large
        self.batch_size = 100   # Maximum batch size for OpenAI API
        self.max_retries = 3
        self.base_delay = 1.0   # Base delay for exponential backoff
        
        # Thread pool for CPU-bound operations
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Initialize embedding validator
        self.validator = get_embedding_validator()
        
        logger.info(f"EmbeddingService initialized with model {self.model_name} and dimension validation")
    
    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text for embedding generation
        
        Args:
            text: Raw text content
            
        Returns:
            Preprocessed text
        """
        if not text or not isinstance(text, str):
            return ""
        
        # Basic cleaning
        text = text.strip()
        
        # Remove excessive whitespace
        import re
        text = re.sub(r'\s+', ' ', text)
        
        # Truncate if too long (rough token estimation: 1 token ≈ 4 characters)
        max_chars = self.max_tokens * 3  # Conservative estimate
        if len(text) > max_chars:
            text = text[:max_chars]
            logger.warning(f"Text truncated to {max_chars} characters")
        
        return text
    
    def _chunk_text(self, text: str, chunk_size: int = 2000) -> List[str]:
        """
        Split long text into chunks for embedding
        
        Args:
            text: Text to chunk
            chunk_size: Maximum characters per chunk
            
        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        words = text.split()
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + 1  # +1 for space
            
            if current_length + word_length > chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def _generate_content_id(self, content: str, metadata: Dict[str, Any]) -> str:
        """
        Generate a unique content ID based on content and metadata
        
        Args:
            content: Text content
            metadata: Associated metadata
            
        Returns:
            Unique content ID
        """
        # Create hash from content and key metadata
        hash_input = f"{content}_{metadata.get('platform', '')}_{metadata.get('created_at', '')}"
        content_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
        return f"content_{content_hash}"
    
    def _validate_embedding(self, embedding: List[float], content_id: Optional[str] = None) -> Tuple[bool, Optional[EmbeddingValidationResult]]:
        """
        Validate embedding vector using comprehensive validation system
        
        Args:
            embedding: Embedding vector from OpenAI
            content_id: Optional content identifier for logging
            
        Returns:
            Tuple of (is_valid, validation_result)
        """
        if not embedding:
            return False, None
        
        # Use comprehensive validator
        validation_result = self.validator.validate_embedding(embedding, content_id)
        
        # Send metrics to Prometheus
        try:
            monitoring_service.record_embedding_validation(
                is_valid=validation_result.is_valid,
                dimension=validation_result.dimension,
                duration_seconds=validation_result.validation_time
            )
            
            # Record dimension mismatches specifically
            if validation_result.dimension != validation_result.expected_dimension:
                monitoring_service.record_embedding_dimension_mismatch(
                    expected_dimension=validation_result.expected_dimension,
                    actual_dimension=validation_result.dimension
                )
        except Exception as e:
            logger.debug(f"Failed to record embedding validation metrics: {e}")
        
        if not validation_result.is_valid:
            logger.warning(f"Embedding validation failed for content_id={content_id}: {', '.join(validation_result.issues)}")
        
        return validation_result.is_valid, validation_result
    
    async def _create_embedding_with_retry(self, text: str) -> Optional[List[float]]:
        """
        Create embedding with retry logic for rate limits
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector or None if failed
        """
        for attempt in range(self.max_retries):
            try:
                response = await self.async_client.embeddings.create(
                    model=self.model_name,
                    input=text
                )
                
                embedding = response.data[0].embedding
                
                is_valid, validation_result = self._validate_embedding(embedding, content_id=f"retry_text_{hash(text)}")
                if is_valid:
                    return embedding
                else:
                    logger.error(f"Invalid embedding received for text: {text[:50]}...")
                    if validation_result:
                        logger.error(f"Validation issues: {', '.join(validation_result.issues)}")
                    return None
                    
            except RateLimitError as e:
                wait_time = self.base_delay * (2 ** attempt)
                logger.warning(f"Rate limit hit, waiting {wait_time}s (attempt {attempt + 1})")
                await asyncio.sleep(wait_time)
                
            except APIError as e:
                logger.error(f"OpenAI API error: {e}")
                if attempt == self.max_retries - 1:
                    return None
                await asyncio.sleep(self.base_delay)
                
            except Exception as e:
                logger.error(f"Unexpected error creating embedding: {e}")
                return None
        
        logger.error(f"Failed to create embedding after {self.max_retries} attempts")
        return None
    
    def create_embedding_sync(self, text: str) -> Optional[np.ndarray]:
        """
        Create embedding synchronously
        
        Args:
            text: Text to embed
            
        Returns:
            Normalized embedding vector or None
        """
        try:
            preprocessed_text = self._preprocess_text(text)
            if not preprocessed_text:
                return None
            
            response = self.openai_client.embeddings.create(
                model=self.model_name,
                input=preprocessed_text
            )
            
            embedding = response.data[0].embedding
            
            is_valid, validation_result = self._validate_embedding(embedding, content_id=f"sync_text_{hash(text)}")
            if is_valid:
                # Convert to numpy and normalize using validator
                np_embedding = np.array(embedding, dtype=np.float32)
                normalized, success = self.validator.normalize_embedding(np_embedding)
                if success:
                    return normalized
                else:
                    logger.error("Failed to normalize embedding")
                    return None
            else:
                if validation_result:
                    logger.error(f"Sync embedding validation failed: {', '.join(validation_result.issues)}")
                return None
            
        except Exception as e:
            logger.error(f"Error creating embedding: {e}")
            return None
    
    async def create_embedding_async(self, text: str) -> Optional[np.ndarray]:
        """
        Create embedding asynchronously
        
        Args:
            text: Text to embed
            
        Returns:
            Normalized embedding vector or None
        """
        preprocessed_text = self._preprocess_text(text)
        if not preprocessed_text:
            return None
        
        embedding = await self._create_embedding_with_retry(preprocessed_text)
        if embedding:
            # Convert to numpy and normalize using validator
            np_embedding = np.array(embedding, dtype=np.float32)
            normalized, success = self.validator.normalize_embedding(np_embedding)
            if success:
                return normalized
            else:
                logger.error("Failed to normalize async embedding")
                return None
        
        return None
    
    async def create_batch_embeddings(
        self, 
        texts: List[str],
        batch_size: Optional[int] = None
    ) -> List[Optional[np.ndarray]]:
        """
        Create embeddings for multiple texts efficiently
        
        Args:
            texts: List of texts to embed
            batch_size: Override default batch size
            
        Returns:
            List of embedding vectors (None for failed embeddings)
        """
        if not texts:
            return []
        
        batch_size = batch_size or self.batch_size
        embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = await self._process_batch(batch)
            embeddings.extend(batch_embeddings)
        
        return embeddings
    
    async def _process_batch(self, texts: List[str]) -> List[Optional[np.ndarray]]:
        """
        Process a batch of texts for embedding
        
        Args:
            texts: Batch of texts
            
        Returns:
            List of embeddings
        """
        # Preprocess all texts
        processed_texts = [self._preprocess_text(text) for text in texts]
        
        # Filter out empty texts
        valid_texts = []
        text_indices = []
        for i, text in enumerate(processed_texts):
            if text:
                valid_texts.append(text)
                text_indices.append(i)
        
        if not valid_texts:
            return [None] * len(texts)
        
        try:
            # Create embeddings for valid texts
            response = await self.async_client.embeddings.create(
                model=self.model_name,
                input=valid_texts
            )
            
            # Initialize results array
            results = [None] * len(texts)
            
            # Process response
            for i, embedding_data in enumerate(response.data):
                original_index = text_indices[i]
                embedding = embedding_data.embedding
                
                is_valid, validation_result = self._validate_embedding(
                    embedding, content_id=f"batch_{original_index}"
                )
                if is_valid:
                    np_embedding = np.array(embedding, dtype=np.float32)
                    normalized, success = self.validator.normalize_embedding(np_embedding)
                    if success:
                        results[original_index] = normalized
                    else:
                        logger.warning(f"Failed to normalize batch embedding at index {original_index}")
                else:
                    if validation_result:
                        logger.warning(f"Batch embedding validation failed at index {original_index}: {', '.join(validation_result.issues)}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            return [None] * len(texts)
    
    def store_content_with_embedding(
        self,
        content: str,
        metadata: Dict[str, Any],
        content_id: Optional[str] = None
    ) -> EmbeddingResult:
        """
        Create embedding and store content in vector store
        
        Args:
            content: Text content
            metadata: Associated metadata
            content_id: Optional custom content ID
            
        Returns:
            EmbeddingResult with operation details
        """
        start_time = time.time()
        
        try:
            # Generate content ID if not provided
            if not content_id:
                content_id = self._generate_content_id(content, metadata)
            
            # Create embedding
            embedding = self.create_embedding_sync(content)
            
            if embedding is not None:
                # Add additional metadata
                enhanced_metadata = {
                    **metadata,
                    'content': content,
                    'content_length': len(content),
                    'embedding_model': self.model_name,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'content_hash': hashlib.sha256(content.encode()).hexdigest()[:16]
                }
                
                # Store in vector store
                try:
                    stored_content_id = vector_store.add_vector(
                        vector=embedding,
                        content_id=content_id,
                        metadata=enhanced_metadata
                    )
                    success = bool(stored_content_id)
                except Exception as e:
                    logger.error(f"Error storing vector: {e}")
                    success = False
                
                processing_time = time.time() - start_time
                
                if success:
                    logger.info(f"Successfully stored content {content_id} with embedding")
                    return EmbeddingResult(
                        content_id=content_id,
                        content=content,
                        embedding=embedding,
                        metadata=enhanced_metadata,
                        success=True,
                        processing_time=processing_time
                    )
                else:
                    return EmbeddingResult(
                        content_id=content_id,
                        content=content,
                        embedding=embedding,
                        metadata=metadata,
                        success=False,
                        error="Failed to store in vector store",
                        processing_time=processing_time
                    )
            else:
                return EmbeddingResult(
                    content_id=content_id,
                    content=content,
                    embedding=None,
                    metadata=metadata,
                    success=False,
                    error="Failed to create embedding",
                    processing_time=time.time() - start_time
                )
                
        except Exception as e:
            logger.error(f"Error storing content with embedding: {e}")
            return EmbeddingResult(
                content_id=content_id or "unknown",
                content=content,
                embedding=None,
                metadata=metadata,
                success=False,
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    async def store_batch_content(
        self,
        contents: List[str],
        metadata_list: List[Dict[str, Any]],
        content_ids: Optional[List[str]] = None
    ) -> List[EmbeddingResult]:
        """
        Store multiple content items with embeddings efficiently
        
        Args:
            contents: List of text contents
            metadata_list: List of metadata dictionaries
            content_ids: Optional list of content IDs
            
        Returns:
            List of EmbeddingResults
        """
        if len(contents) != len(metadata_list):
            raise ValueError("Contents and metadata lists must have same length")
        
        start_time = time.time()
        
        # Generate content IDs if not provided
        if not content_ids:
            content_ids = [
                self._generate_content_id(content, metadata)
                for content, metadata in zip(contents, metadata_list)
            ]
        
        # Create embeddings in batch
        embeddings = await self.create_batch_embeddings(contents)
        
        results = []
        valid_vectors = []
        valid_ids = []
        valid_metadata = []
        
        # Process results and prepare for batch storage
        for i, (content, metadata, embedding, content_id) in enumerate(
            zip(contents, metadata_list, embeddings, content_ids)
        ):
            processing_time = time.time() - start_time
            
            if embedding is not None:
                # Enhance metadata
                enhanced_metadata = {
                    **metadata,
                    'content': content,
                    'content_length': len(content),
                    'embedding_model': self.model_name,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'content_hash': hashlib.sha256(content.encode()).hexdigest()[:16]
                }
                
                valid_vectors.append(embedding)
                valid_ids.append(content_id)
                valid_metadata.append(enhanced_metadata)
                
                results.append(EmbeddingResult(
                    content_id=content_id,
                    content=content,
                    embedding=embedding,
                    metadata=enhanced_metadata,
                    success=True,
                    processing_time=processing_time
                ))
            else:
                results.append(EmbeddingResult(
                    content_id=content_id,
                    content=content,
                    embedding=None,
                    metadata=metadata,
                    success=False,
                    error="Failed to create embedding",
                    processing_time=processing_time
                ))
        
        # Store valid embeddings in batch
        if valid_vectors:
            vectors_array = np.array(valid_vectors)
            try:
                stored_content_ids = vector_store.add_vectors_batch(
                    vectors=vectors_array,
                    content_ids=valid_ids,
                    metadata_list=valid_metadata
                )
                success = bool(stored_content_ids) and len(stored_content_ids) == len(valid_vectors)
            except Exception as e:
                logger.error(f"Error storing batch vectors: {e}")
                success = False
            
            if success:
                logger.info(f"Successfully stored {len(valid_vectors)} content items")
            else:
                logger.error("Failed to store embeddings in vector store")
                # Update results to reflect storage failure
                for result in results:
                    if result.success:
                        result.success = False
                        result.error = "Failed to store in vector store"
        
        return results
    
    def search_similar_content(
        self,
        query: str,
        k: int = 5,
        threshold: float = 0.7,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar content using semantic similarity
        
        Args:
            query: Search query text
            k: Number of results to return
            threshold: Minimum similarity threshold
            filter_metadata: Optional metadata filters
            
        Returns:
            List of similar content with metadata
        """
        try:
            # Create query embedding
            query_embedding = self.create_embedding_sync(query)
            if query_embedding is None:
                logger.error("Failed to create query embedding")
                return []
            
            # Search vector store
            results = vector_store.search(
                query_vector=query_embedding,
                k=k,
                threshold=threshold
            )
            
            # Apply metadata filters if provided
            if filter_metadata:
                filtered_results = []
                for result in results:
                    match = True
                    for key, value in filter_metadata.items():
                        if result.get(key) != value:
                            match = False
                            break
                    if match:
                        filtered_results.append(result)
                results = filtered_results
            
            logger.info(f"Found {len(results)} similar content items for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error searching similar content: {e}")
            return []
    
    def get_content_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored content
        
        Returns:
            Dictionary with content statistics
        """
        vector_stats = vector_store.get_statistics()
        validation_metrics = self.validator.get_validation_metrics()
        
        return {
            'vector_store': vector_stats,
            'embedding_validation': validation_metrics
        }
    
    def cleanup_deleted_content(self) -> bool:
        """
        Rebuild vector store to remove deleted content
        
        Returns:
            Success status
        """
        return vector_store.rebuild_index()
    
    def validate_existing_embedding(
        self, 
        embedding: Union[np.ndarray, List[float]], 
        content_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> EmbeddingValidationResult:
        """
        Validate an existing embedding vector
        
        Args:
            embedding: Embedding vector to validate
            content_id: Optional content identifier
            metadata: Optional metadata
            
        Returns:
            EmbeddingValidationResult
        """
        return self.validator.validate_embedding(embedding, content_id, metadata)
    
    def get_validation_metrics(self) -> Dict[str, Any]:
        """
        Get embedding validation metrics
        
        Returns:
            Dictionary with validation statistics
        """
        return self.validator.get_validation_metrics()
    
    def reset_validation_metrics(self) -> None:
        """Reset embedding validation metrics"""
        self.validator.reset_metrics()
    
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
        return self.validator.validate_and_fix_embedding(embedding, content_id, auto_normalize)

# Global embedding service instance - lazy loaded
_embedding_service = None

def get_embedding_service():
    """Get the global embedding service instance (lazy initialization)"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service

# For backward compatibility, create a property-like access
class EmbeddingServiceProxy:
    """Proxy object that provides lazy access to embedding service"""
    def __getattr__(self, name):
        return getattr(get_embedding_service(), name)

embedding_service = EmbeddingServiceProxy()