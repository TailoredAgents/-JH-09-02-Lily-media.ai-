"""
Simple vector search implementation using NumPy (fallback for FAISS)
"""
import numpy as np
import json
import os
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from openai import OpenAI
from backend.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class SimpleVectorSearch:
    """Simple vector search using NumPy cosine similarity"""
    
    def __init__(self, dimension: int = 1536, index_path: str = "data/memory"):
        self.dimension = dimension
        self.index_path = index_path
        self.vectors_file = os.path.join(index_path, "vectors.npy")
        self.metadata_file = os.path.join(index_path, "metadata.json")
        
        # Initialize OpenAI client
        self.openai_client = OpenAI(api_key=settings.openai_api_key)
        
        # Create directories
        os.makedirs(index_path, exist_ok=True)
        
        # Load or initialize data
        self.vectors = self._load_vectors()
        self.metadata = self._load_metadata()
    
    def _load_vectors(self) -> np.ndarray:
        """Load vectors from disk or create empty array"""
        if os.path.exists(self.vectors_file):
            try:
                return np.load(self.vectors_file)
            except Exception as e:
                logger.error(f"Error loading vectors: {e}")
        return np.empty((0, self.dimension), dtype=np.float32)
    
    def _load_metadata(self) -> Dict:
        """Load metadata from disk or create empty dict"""
        from backend.core.io_utils import load_json_dict
        return load_json_dict(self.metadata_file)
    
    def _save_vectors(self):
        """Save vectors to disk"""
        np.save(self.vectors_file, self.vectors)
    
    def _save_metadata(self):
        """Save metadata to disk"""
        from backend.core.io_utils import save_json_dict
        save_json_dict(self.metadata_file, self.metadata)
    
    def embed_text(self, text: str) -> np.ndarray:
        """Create embedding for text using OpenAI"""
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-large",
                input=text
            )
            embedding = np.array(response.data[0].embedding, dtype=np.float32)
            # Normalize for cosine similarity
            return embedding / np.linalg.norm(embedding)
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return np.zeros(self.dimension, dtype=np.float32)
    
    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        return np.dot(vec1, vec2)
    
    def store_content(self, content: str, metadata: Dict[str, Any]) -> str:
        """Store content with embeddings and metadata"""
        content_id = str(uuid.uuid4())
        
        # Create embedding
        embedding = self.embed_text(content)
        
        if embedding.any():
            # Add to vectors array
            if self.vectors.shape[0] == 0:
                self.vectors = embedding.reshape(1, -1)
            else:
                self.vectors = np.vstack([self.vectors, embedding])
            
            # Store metadata with index
            index = len(self.vectors) - 1
            self.metadata[str(index)] = {
                'content_id': content_id,
                'content': content,
                'metadata': metadata,
                'created_at': datetime.utcnow().isoformat(),
                'embedding_norm': float(np.linalg.norm(embedding))
            }
            
            # Save to disk
            self._save_vectors()
            self._save_metadata()
            
            return content_id
        
        return None
    
    def search_similar(self, query: str, top_k: int = 5, threshold: float = 0.7) -> List[Dict]:
        """Search for similar content using cosine similarity"""
        if len(self.vectors) == 0:
            return []
        
        query_embedding = self.embed_text(query)
        
        if not query_embedding.any():
            return []
        
        # Calculate similarities
        similarities = np.dot(self.vectors, query_embedding)
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            score = similarities[idx]
            if score >= threshold:
                metadata = self.metadata.get(str(idx), {})
                if metadata:
                    results.append({
                        'content_id': metadata.get('content_id'),
                        'content': metadata.get('content', ''),
                        'similarity_score': float(score),
                        'metadata': metadata.get('metadata', {}),
                        'created_at': metadata.get('created_at')
                    })
        
        return results
    
    def get_content_by_type(self, content_type: str, limit: int = 10) -> List[Dict]:
        """Retrieve content by type"""
        results = []
        for idx, meta in self.metadata.items():
            if meta.get('metadata', {}).get('type') == content_type:
                results.append({
                    'content_id': meta.get('content_id'),
                    'content': meta.get('content', ''),
                    'metadata': meta.get('metadata', {}),
                    'created_at': meta.get('created_at')
                })
                if len(results) >= limit:
                    break
        
        return sorted(results, key=lambda x: x['created_at'], reverse=True)
    
    def get_high_performing_content(self, min_engagement: float = 5.0, limit: int = 10) -> List[Dict]:
        """Retrieve high-performing content for learning"""
        results = []
        for idx, meta in self.metadata.items():
            engagement = meta.get('metadata', {}).get('engagement_rate', 0)
            if engagement >= min_engagement:
                results.append({
                    'content_id': meta.get('content_id'),
                    'content': meta.get('content', ''),
                    'engagement_rate': engagement,
                    'metadata': meta.get('metadata', {}),
                    'created_at': meta.get('created_at')
                })
        
        # Sort by engagement rate
        results.sort(key=lambda x: x['engagement_rate'], reverse=True)
        return results[:limit]
    
    def get_content_for_repurposing(self, days_old: int = 30, min_engagement: float = 3.0) -> List[Dict]:
        """Find content suitable for repurposing"""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        results = []
        for idx, meta in self.metadata.items():
            created_at = datetime.fromisoformat(meta.get('created_at', ''))
            engagement = meta.get('metadata', {}).get('engagement_rate', 0)
            
            if created_at < cutoff_date and engagement >= min_engagement:
                results.append({
                    'content_id': meta.get('content_id'),
                    'content': meta.get('content', ''),
                    'engagement_rate': engagement,
                    'age_days': (datetime.utcnow() - created_at).days,
                    'metadata': meta.get('metadata', {}),
                    'created_at': meta.get('created_at')
                })
        
        # Sort by engagement rate
        results.sort(key=lambda x: x['engagement_rate'], reverse=True)
        return results
    
    def analyze_content_patterns(self) -> Dict[str, Any]:
        """Analyze patterns in stored content"""
        if not self.metadata:
            return {'error': 'No content available for analysis'}
        
        patterns = {
            'total_content': len(self.metadata),
            'content_types': {},
            'platforms': {},
            'avg_engagement': 0,
            'top_topics': [],
            'temporal_patterns': {}
        }
        
        engagements = []
        for idx, meta in self.metadata.items():
            metadata = meta.get('metadata', {})
            
            # Content types
            content_type = metadata.get('type', 'unknown')
            patterns['content_types'][content_type] = patterns['content_types'].get(content_type, 0) + 1
            
            # Platforms
            platform = metadata.get('platform', 'unknown')
            patterns['platforms'][platform] = patterns['platforms'].get(platform, 0) + 1
            
            # Engagement
            engagement = metadata.get('engagement_rate', 0)
            if engagement > 0:
                engagements.append(engagement)
            
            # Topics
            topic = metadata.get('topic', 'general')
            patterns['top_topics'].append(topic)
        
        # Calculate averages
        if engagements:
            patterns['avg_engagement'] = sum(engagements) / len(engagements)
        
        # Top topics (simplified)
        from collections import Counter
        topic_counts = Counter(patterns['top_topics'])
        patterns['top_topics'] = [{'topic': topic, 'count': count} 
                                for topic, count in topic_counts.most_common(10)]
        
        return patterns
    
    @property
    def ntotal(self) -> int:
        """Get total number of vectors (compatibility with FAISS API)"""
        return len(self.vectors)

# Global instance
vector_search = SimpleVectorSearch()