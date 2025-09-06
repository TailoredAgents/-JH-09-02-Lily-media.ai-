"""
FAISS Vector Store Implementation
Provides high-performance vector indexing and similarity search for content embeddings.
"""

import os
import json
import uuid
import pickle
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from backend.core.config import get_utc_now
import logging

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    # Suppress the warning at import time - it will be shown only when actually used
    pass

# Get logger (use application's logging configuration)
logger = logging.getLogger(__name__)


class VectorStore:
    """
    High-performance FAISS-based vector store for content embeddings.
    
    Features:
    - FAISS IndexFlatIP for efficient cosine similarity search
    - Persistent storage with automatic loading/saving
    - Batch operations for optimal performance
    - Memory-efficient operations with configurable limits
    """
    
    def __init__(
        self, 
        dimension: int = 3072,
        index_path: str = "data/faiss_indexes",
        index_type: str = "flat_ip",
        max_vectors_in_memory: int = 100000
    ):
        """
        Initialize vector store.
        
        Args:
            dimension: Embedding vector dimension (3072 for OpenAI text-embedding-3-large)
            index_path: Directory to store index files
            index_type: FAISS index type ('flat_ip', 'hnsw', 'ivf')
            max_vectors_in_memory: Maximum vectors to keep in memory
        """
        self.dimension = dimension
        self.index_path = index_path
        self.index_type = index_type
        self.max_vectors_in_memory = max_vectors_in_memory
        
        # File paths
        self.index_file = os.path.join(index_path, "faiss.index")
        self.metadata_file = os.path.join(index_path, "metadata.json")
        self.id_mapping_file = os.path.join(index_path, "id_mapping.json")
        self.vectors_file = os.path.join(index_path, "vectors.npz")  # Store vectors for rebuild
        
        # Create directory if it doesn't exist
        os.makedirs(index_path, exist_ok=True)
        
        # Initialize components
        self._index = self._create_or_load_index()
        self._metadata = self._load_metadata()
        self._id_mapping = self._load_id_mapping()
        self._vectors = self._load_vectors()  # Store vectors for deletion/rebuild
        self._next_internal_id = max([int(k) for k in self._id_mapping.keys()] + [-1]) + 1
        
        logger.info(f"VectorStore initialized with {self.total_vectors} vectors")
    
    def _create_or_load_index(self):
        """Create new FAISS index or load existing one."""
        if not FAISS_AVAILABLE:
            logger.info("FAISS not available, using fallback implementation")
            return None
            
        # Try to load existing index
        if os.path.exists(self.index_file):
            try:
                index = faiss.read_index(self.index_file)
                logger.info(f"Loaded existing FAISS index with {index.ntotal} vectors")
                return index
            except Exception as e:
                logger.error(f"Failed to load index: {e}. Creating new index.")
        
        # Create new index based on type
        if self.index_type == "flat_ip":
            # Inner Product index for normalized vectors (cosine similarity)
            index = faiss.IndexFlatIP(self.dimension)
        elif self.index_type == "hnsw":
            # HNSW index for faster search with approximate results
            index = faiss.IndexHNSWFlat(self.dimension, 32)
            index.hnsw.efConstruction = 40
            index.hnsw.efSearch = 16
        elif self.index_type == "ivf":
            # IVF index for very large datasets
            quantizer = faiss.IndexFlatIP(self.dimension)
            index = faiss.IndexIVFFlat(quantizer, self.dimension, min(100, max(1, self.max_vectors_in_memory // 1000)))
        else:
            raise ValueError(f"Unsupported index type: {self.index_type}")
        
        logger.info(f"Created new {self.index_type} FAISS index")
        return index
    
    def _load_metadata(self) -> Dict[str, Dict]:
        """Load metadata mapping internal IDs to content information."""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load metadata: {e}")
        return {}
    
    def _load_id_mapping(self) -> Dict[str, str]:
        """Load mapping from internal IDs to content IDs."""
        if os.path.exists(self.id_mapping_file):
            try:
                with open(self.id_mapping_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load ID mapping: {e}")
        return {}
    
    def _save_index(self):
        """Save FAISS index to disk."""
        if not FAISS_AVAILABLE or not self._index:
            return
            
        try:
            faiss.write_index(self._index, self.index_file)
            logger.info("FAISS index saved successfully")
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
    
    def _save_metadata(self):
        """Save metadata to disk."""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self._metadata, f, indent=2, default=str, ensure_ascii=False)
            logger.info("Metadata saved successfully")
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
    
    def _save_id_mapping(self):
        """Save ID mapping to disk."""
        try:
            with open(self.id_mapping_file, 'w', encoding='utf-8') as f:
                json.dump(self._id_mapping, f, indent=2)
            logger.info("ID mapping saved successfully")
        except Exception as e:
            logger.error(f"Failed to save ID mapping: {e}")
    
    def _load_vectors(self) -> Dict[str, np.ndarray]:
        """Load stored vectors from disk."""
        if os.path.exists(self.vectors_file):
            try:
                with np.load(self.vectors_file) as data:
                    # Convert numpy arrays back to dictionary
                    vectors = {}
                    for internal_id in data.files:
                        vectors[internal_id] = data[internal_id]
                    logger.info(f"Loaded {len(vectors)} stored vectors")
                    return vectors
            except Exception as e:
                logger.error(f"Failed to load vectors: {e}")
        return {}
    
    def _save_vectors(self):
        """Save vectors to disk for rebuild capability."""
        try:
            # Only save vectors for which we have valid metadata
            valid_vectors = {
                internal_id: vector 
                for internal_id, vector in self._vectors.items() 
                if internal_id in self._metadata
            }
            
            if valid_vectors:
                np.savez_compressed(self.vectors_file, **valid_vectors)
                logger.info(f"Saved {len(valid_vectors)} vectors to disk")
            else:
                # Remove file if no valid vectors
                if os.path.exists(self.vectors_file):
                    os.remove(self.vectors_file)
                    logger.info("Removed empty vectors file")
                    
        except Exception as e:
            logger.error(f"Failed to save vectors: {e}")
    
    def add_vector(
        self, 
        vector: np.ndarray, 
        content_id: str = None, 
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Add a single vector to the index.
        
        Args:
            vector: Normalized embedding vector
            content_id: Unique content identifier (auto-generated if None)
            metadata: Associated metadata
            
        Returns:
            Content ID of the added vector
        """
        if not FAISS_AVAILABLE:
            raise RuntimeError("FAISS not available")
        
        if content_id is None:
            content_id = str(uuid.uuid4())
        
        # Ensure vector is properly shaped and normalized
        if vector.ndim == 1:
            vector = vector.reshape(1, -1)
        
        # Verify vector is normalized for cosine similarity
        norm = np.linalg.norm(vector)
        if abs(norm - 1.0) > 0.001:
            logger.warning(f"Vector norm {norm} != 1.0, normalizing")
            vector = vector / norm
        
        # Add to index
        self._index.add(vector.astype(np.float32))
        
        # Store metadata, mapping, and vector for rebuild capability
        internal_id = str(self._next_internal_id)
        self._id_mapping[internal_id] = content_id
        self._metadata[internal_id] = {
            'content_id': content_id,
            'metadata': metadata or {},
            'created_at': get_utc_now().isoformat(),
            'vector_norm': float(norm)
        }
        
        # Store the vector for potential rebuild operations
        self._vectors[internal_id] = vector.flatten().astype(np.float32)
        
        self._next_internal_id += 1
        
        # Save periodically or when reaching threshold
        if self._next_internal_id % 100 == 0:
            self._save_all()
        
        logger.info(f"Added vector for content_id: {content_id}")
        return content_id
    
    def add_vectors_batch(
        self, 
        vectors: np.ndarray, 
        content_ids: List[str] = None, 
        metadata_list: List[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Add multiple vectors in batch for better performance.
        
        Args:
            vectors: Array of normalized embedding vectors [n_vectors, dimension]
            content_ids: List of content IDs (auto-generated if None)
            metadata_list: List of metadata dicts
            
        Returns:
            List of content IDs for added vectors
        """
        if not FAISS_AVAILABLE:
            raise RuntimeError("FAISS not available")
        
        n_vectors = vectors.shape[0]
        
        if content_ids is None:
            content_ids = [str(uuid.uuid4()) for _ in range(n_vectors)]
        
        if metadata_list is None:
            metadata_list = [{} for _ in range(n_vectors)]
        
        # Normalize vectors if needed
        norms = np.linalg.norm(vectors, axis=1)
        mask = np.abs(norms - 1.0) > 0.001
        if np.any(mask):
            logger.warning(f"Normalizing {np.sum(mask)} vectors")
            vectors[mask] = vectors[mask] / norms[mask].reshape(-1, 1)
        
        # Add to index
        self._index.add(vectors.astype(np.float32))
        
        # Store metadata, mappings, and vectors
        for i, (content_id, metadata) in enumerate(zip(content_ids, metadata_list)):
            internal_id = str(self._next_internal_id + i)
            self._id_mapping[internal_id] = content_id
            self._metadata[internal_id] = {
                'content_id': content_id,
                'metadata': metadata,
                'created_at': get_utc_now().isoformat(),
                'vector_norm': float(norms[i])
            }
            
            # Store the vector for potential rebuild operations
            self._vectors[internal_id] = vectors[i].flatten().astype(np.float32)
        
        self._next_internal_id += n_vectors
        self._save_all()
        
        logger.info(f"Added {n_vectors} vectors in batch")
        return content_ids
    
    def search(
        self, 
        query_vector: np.ndarray, 
        k: int = 5, 
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.
        
        Args:
            query_vector: Query embedding vector
            k: Number of results to return
            threshold: Minimum similarity threshold
            
        Returns:
            List of search results with content_id, score, and metadata
        """
        if not FAISS_AVAILABLE or self.total_vectors == 0:
            return []
        
        # Ensure query vector is properly shaped and normalized
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
        
        norm = np.linalg.norm(query_vector)
        if abs(norm - 1.0) > 0.001:
            query_vector = query_vector / norm
        
        # Search index
        scores, indices = self._index.search(query_vector.astype(np.float32), k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1 or score < threshold:  # Invalid index or below threshold
                continue
                
            internal_id = str(idx)
            if internal_id in self._metadata:
                result = {
                    'content_id': self._id_mapping.get(internal_id),
                    'similarity_score': float(score),
                    'metadata': self._metadata[internal_id]['metadata'],
                    'created_at': self._metadata[internal_id]['created_at']
                }
                results.append(result)
        
        return results
    
    def get_vector_by_content_id(self, content_id: str) -> Optional[np.ndarray]:
        """
        Retrieve vector by content ID.
        Note: This is expensive as FAISS doesn't support direct ID lookup.
        """
        # Find internal ID
        internal_id = None
        for iid, cid in self._id_mapping.items():
            if cid == content_id:
                internal_id = int(iid)
                break
        
        if internal_id is None:
            return None
        
        # FAISS doesn't support direct vector retrieval by ID
        # This would require reconstructing from index, which is expensive
        logger.warning("Direct vector retrieval is expensive with FAISS")
        return None
    
    def remove_vector(self, content_id: str, rebuild_index: bool = True) -> bool:
        """
        Remove vector by content ID with true deletion from index.
        
        Args:
            content_id: Content ID to remove
            rebuild_index: Whether to rebuild the index immediately (default: True)
                          Set to False if doing bulk deletions, then call rebuild_index() once
        
        Returns:
            True if vector was found and removed, False otherwise
        """
        # Find the internal ID for this content
        internal_id = None
        for iid, cid in self._id_mapping.items():
            if cid == content_id:
                internal_id = iid
                break
        
        if internal_id is None:
            logger.warning(f"Content ID {content_id} not found for removal")
            return False
        
        # Remove from all data structures
        self._metadata.pop(internal_id, None)
        self._id_mapping.pop(internal_id, None)
        self._vectors.pop(internal_id, None)
        
        logger.info(f"Removed vector data for content_id: {content_id}")
        
        if rebuild_index:
            # Immediately rebuild index to ensure true deletion
            self.rebuild_index()
            logger.info(f"Index rebuilt after removing content_id: {content_id}")
        else:
            # Just save metadata/mapping changes for now
            self._save_metadata()
            self._save_id_mapping()
            self._save_vectors()
            logger.info(f"Vector marked for deletion: {content_id} (rebuild required)")
        
        return True
    
    def remove_vectors_batch(self, content_ids: List[str]) -> int:
        """
        Remove multiple vectors efficiently with a single index rebuild.
        
        Args:
            content_ids: List of content IDs to remove
            
        Returns:
            Number of vectors successfully removed
        """
        removed_count = 0
        
        logger.info(f"Starting bulk removal of {len(content_ids)} vectors")
        
        # Remove all vectors without rebuilding
        for content_id in content_ids:
            if self.remove_vector(content_id, rebuild_index=False):
                removed_count += 1
        
        # Single rebuild at the end
        if removed_count > 0:
            logger.info(f"Rebuilding index after removing {removed_count} vectors")
            self.rebuild_index()
        
        logger.info(f"Bulk removal complete: {removed_count}/{len(content_ids)} vectors removed")
        return removed_count
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive index statistics."""
        stored_vectors = len(self._vectors)
        metadata_count = len(self._metadata)
        mapping_count = len(self._id_mapping)
        
        # Check for inconsistencies
        inconsistencies = []
        if stored_vectors != metadata_count:
            inconsistencies.append(f"Stored vectors ({stored_vectors}) != metadata ({metadata_count})")
        if metadata_count != mapping_count:
            inconsistencies.append(f"Metadata ({metadata_count}) != ID mapping ({mapping_count})")
        if FAISS_AVAILABLE and self.total_vectors != metadata_count:
            inconsistencies.append(f"FAISS index ({self.total_vectors}) != metadata ({metadata_count})")
        
        return {
            'total_vectors': self.total_vectors,
            'stored_vectors': stored_vectors,
            'metadata_entries': metadata_count,
            'id_mappings': mapping_count,
            'dimension': self.dimension,
            'index_type': self.index_type,
            'memory_usage_mb': self._estimate_memory_usage(),
            'faiss_available': FAISS_AVAILABLE,
            'is_trained': self.is_trained,
            'inconsistencies': inconsistencies,
            'needs_rebuild': len(inconsistencies) > 0
        }
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB."""
        if not FAISS_AVAILABLE or not self._index:
            return 0.0
        
        # Rough estimate: vectors + metadata
        vector_size = self.total_vectors * self.dimension * 4  # float32
        metadata_size = len(json.dumps(self._metadata).encode('utf-8'))
        return (vector_size + metadata_size) / (1024 * 1024)
    
    def rebuild_index(self):
        """
        Rebuild index from scratch (useful after many deletions).
        This is expensive but ensures optimal performance and true vector deletion.
        """
        if not FAISS_AVAILABLE:
            logger.warning("FAISS not available, cannot rebuild index")
            return
        
        logger.info("Rebuilding FAISS index from stored vectors...")
        
        # Get all valid vectors (ones that still have metadata)
        valid_vectors = []
        valid_internal_ids = []
        
        for internal_id in self._metadata.keys():
            if internal_id in self._vectors:
                valid_vectors.append(self._vectors[internal_id])
                valid_internal_ids.append(internal_id)
        
        if not valid_vectors:
            logger.info("No valid vectors to rebuild, creating empty index")
            # Create fresh empty index
            if self.index_type == "flat_ip":
                self._index = faiss.IndexFlatIP(self.dimension)
            elif self.index_type == "hnsw":
                self._index = faiss.IndexHNSWFlat(self.dimension, 32)
                self._index.hnsw.efConstruction = 40
                self._index.hnsw.efSearch = 16
            elif self.index_type == "ivf":
                quantizer = faiss.IndexFlatIP(self.dimension)
                self._index = faiss.IndexIVFFlat(quantizer, self.dimension, 100)
            else:
                self._index = faiss.IndexFlatIP(self.dimension)
                
            self._save_index()
            logger.info("Empty index created and saved")
            return
        
        # Convert vectors to numpy array
        vectors_array = np.array(valid_vectors).astype(np.float32)
        
        # Ensure vectors are properly shaped
        if vectors_array.ndim == 1:
            vectors_array = vectors_array.reshape(1, -1)
        
        logger.info(f"Rebuilding index with {len(valid_vectors)} valid vectors")
        
        # Create fresh index
        if self.index_type == "flat_ip":
            new_index = faiss.IndexFlatIP(self.dimension)
        elif self.index_type == "hnsw":
            new_index = faiss.IndexHNSWFlat(self.dimension, 32)
            new_index.hnsw.efConstruction = 40
            new_index.hnsw.efSearch = 16
        elif self.index_type == "ivf":
            quantizer = faiss.IndexFlatIP(self.dimension)
            new_index = faiss.IndexIVFFlat(quantizer, self.dimension, min(100, len(valid_vectors)))
            # Train the index if needed
            if not new_index.is_trained:
                new_index.train(vectors_array)
        else:
            new_index = faiss.IndexFlatIP(self.dimension)
        
        # Add all valid vectors to new index
        new_index.add(vectors_array)
        
        # Replace the old index
        self._index = new_index
        
        # Clean up ID mapping - rebuild it sequentially for consistency
        new_id_mapping = {}
        for i, internal_id in enumerate(valid_internal_ids):
            new_id_mapping[str(i)] = self._id_mapping[internal_id]
        
        # Update metadata with new internal IDs
        new_metadata = {}
        for i, old_internal_id in enumerate(valid_internal_ids):
            new_internal_id = str(i)
            new_metadata[new_internal_id] = self._metadata[old_internal_id]
        
        # Update vectors dict with new internal IDs
        new_vectors = {}
        for i, old_internal_id in enumerate(valid_internal_ids):
            new_internal_id = str(i)
            new_vectors[new_internal_id] = self._vectors[old_internal_id]
        
        # Replace old data structures
        self._id_mapping = new_id_mapping
        self._metadata = new_metadata
        self._vectors = new_vectors
        self._next_internal_id = len(valid_internal_ids)
        
        # Save everything
        self._save_all()
        
        logger.info(f"Index rebuilt successfully with {self.total_vectors} vectors")
        logger.info(f"Memory usage: {self._estimate_memory_usage():.2f} MB")
    
    def _save_all(self):
        """Save all components to disk."""
        self._save_index()
        self._save_metadata()
        self._save_id_mapping()
        self._save_vectors()
    
    @property
    def total_vectors(self) -> int:
        """Get total number of vectors in index."""
        if not FAISS_AVAILABLE or not self._index:
            return 0
        return self._index.ntotal
    
    @property
    def is_trained(self) -> bool:
        """Check if index is trained (relevant for some index types)."""
        if not FAISS_AVAILABLE or not self._index:
            return False
        return self._index.is_trained
    
    def train(self, training_vectors: np.ndarray):
        """Train index with sample vectors (for IVF and other index types)."""
        if not FAISS_AVAILABLE or not self._index:
            return
        
        if hasattr(self._index, 'train') and not self.is_trained:
            logger.info(f"Training index with {training_vectors.shape[0]} vectors")
            self._index.train(training_vectors.astype(np.float32))
            self._save_index()
    
    async def similarity_search(
        self, 
        query: str, 
        k: int = 5, 
        threshold: float = 0.7,
        filter: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Async wrapper for similarity search with text query.
        
        Args:
            query: Text query to search for
            k: Number of results to return
            threshold: Minimum similarity threshold
            filter: Metadata filter (currently not implemented)
            
        Returns:
            List of search results with content_id, score, and metadata
        """
        try:
            # Get embeddings for the query text
            from backend.services.embedding_service import get_embedding_service
            embedding_service = get_embedding_service()
            query_embedding = await embedding_service.create_embedding_async(query)
            
            if query_embedding is None:
                logger.warning(f"Failed to get embedding for query: {query}")
                return []
            
            # query_embedding is already a normalized numpy array from embedding service
            query_vector = query_embedding
            
            # Call sync search method
            results = self.search(query_vector, k=k, threshold=threshold)
            
            # Apply filter if provided (simple metadata filtering)
            if filter:
                filtered_results = []
                for result in results:
                    metadata = result.get('metadata', {})
                    match = True
                    for key, value in filter.items():
                        if metadata.get(key) != value:
                            match = False
                            break
                    if match:
                        filtered_results.append(result)
                results = filtered_results
            
            return results
            
        except Exception as e:
            logger.error(f"Error in similarity_search: {e}")
            return []
    
    async def add_text(
        self,
        text: str,
        metadata: Dict[str, Any] = None,
        content_id: str = None
    ) -> str:
        """
        Async wrapper to add text content to vector store.
        
        Args:
            text: Text content to add
            metadata: Associated metadata
            content_id: Unique content identifier (auto-generated if None)
            
        Returns:
            Content ID of the added text
        """
        try:
            # Get embeddings for the text
            from backend.services.embedding_service import get_embedding_service
            embedding_service = get_embedding_service()
            text_embedding = await embedding_service.create_embedding_async(text)
            
            if text_embedding is None:
                logger.warning(f"Failed to get embedding for text: {text[:100]}...")
                raise ValueError("Failed to generate embedding for text")
            
            # text_embedding is already a normalized numpy array from embedding service
            text_vector = text_embedding
            
            # Add metadata with the original text
            full_metadata = metadata or {}
            full_metadata['text'] = text
            full_metadata['text_length'] = len(text)
            
            # Call sync add_vector method
            return self.add_vector(
                vector=text_vector,
                content_id=content_id,
                metadata=full_metadata
            )
            
        except Exception as e:
            logger.error(f"Error in add_text: {e}")
            raise
    
    def __del__(self):
        """Ensure data is saved when object is destroyed."""
        try:
            self._save_all()
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug("VectorStore cleanup save failed", 
                                            exc_info=e)

# Global instance - lazy loaded
_vector_store = None

def get_vector_store():
    """Get the global vector store instance (lazy initialization)"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store

# For backward compatibility, create a property-like access
class VectorStoreProxy:
    """Proxy object that provides lazy access to vector store"""
    def __getattr__(self, name):
        return getattr(get_vector_store(), name)

vector_store = VectorStoreProxy()