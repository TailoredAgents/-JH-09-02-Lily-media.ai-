"""
Production pgvector service - replaces all mock vector stores
No mock data or fallbacks - production-ready vector search
"""
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json

from sqlalchemy import create_engine, text, Column, Integer, String, Text, DateTime, Float
from sqlalchemy.orm import Session, sessionmaker, declarative_base
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import openai
import numpy as np

from backend.db.database import get_db
from backend.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Ensure OpenAI is configured
if not settings.openai_api_key:
    raise ValueError("OpenAI API key required for production vector embeddings")

openai.api_key = settings.openai_api_key

class PgVectorService:
    """Production vector search service using pgvector"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.embedding_model = "text-embedding-3-large"  # 3072 dimensions
        self.embedding_dimensions = 3072
        
    async def ensure_extension(self):
        """Ensure pgvector extension is enabled"""
        try:
            self.db.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            self.db.commit()
            logger.info("pgvector extension enabled")
        except Exception as e:
            logger.error(f"Failed to enable pgvector extension: {e}")
            raise
    
    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI"""
        try:
            response = openai.embeddings.create(
                model=self.embedding_model,
                input=text,
                encoding_format="float"
            )
            embedding = response.data[0].embedding
            
            if len(embedding) != self.embedding_dimensions:
                raise ValueError(f"Expected {self.embedding_dimensions} dimensions, got {len(embedding)}")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    def store_content_embedding(
        self,
        user_id: int,
        content_id: int,
        content_text: str,
        metadata: Dict[str, Any] = None
    ) -> int:
        """Store content embedding in database"""
        try:
            # Generate embedding
            embedding = self.get_embedding(content_text)
            
            # Store in content_embeddings table
            query = text("""
                INSERT INTO content_embeddings (
                    user_id, content_id, content_text, embedding, 
                    metadata, embedding_model, created_at
                ) VALUES (
                    :user_id, :content_id, :content_text, :embedding,
                    :metadata, :model, NOW()
                ) RETURNING id
            """)
            
            result = self.db.execute(query, {
                'user_id': user_id,
                'content_id': content_id,
                'content_text': content_text,
                'embedding': embedding,
                'metadata': json.dumps(metadata or {}),
                'model': self.embedding_model
            })
            
            embedding_id = result.fetchone()[0]
            self.db.commit()
            
            logger.info(f"Stored embedding {embedding_id} for content {content_id}")
            return embedding_id
            
        except Exception as e:
            logger.error(f"Failed to store content embedding: {e}")
            self.db.rollback()
            raise
    
    def store_memory_embedding(
        self,
        user_id: int,
        title: str,
        content: str,
        memory_type: str = "general",
        metadata: Dict[str, Any] = None
    ) -> int:
        """Store memory embedding in database"""
        try:
            # Combine title and content for embedding
            text_content = f"{title}\n\n{content}".strip()
            embedding = self.get_embedding(text_content)
            
            # Store in memory_embeddings table
            query = text("""
                INSERT INTO memory_embeddings (
                    user_id, title, content, memory_type, embedding,
                    metadata, embedding_model, created_at
                ) VALUES (
                    :user_id, :title, :content, :memory_type, :embedding,
                    :metadata, :model, NOW()
                ) RETURNING id
            """)
            
            result = self.db.execute(query, {
                'user_id': user_id,
                'title': title,
                'content': content,
                'memory_type': memory_type,
                'embedding': embedding,
                'metadata': json.dumps(metadata or {}),
                'model': self.embedding_model
            })
            
            memory_id = result.fetchone()[0]
            self.db.commit()
            
            logger.info(f"Stored memory embedding {memory_id} for user {user_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"Failed to store memory embedding: {e}")
            self.db.rollback()
            raise
    
    def similarity_search_content(
        self,
        user_id: int,
        query_text: str,
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search for similar content using cosine similarity"""
        try:
            # Generate query embedding
            query_embedding = self.get_embedding(query_text)
            
            # Search for similar content
            query = text("""
                SELECT 
                    id, content_id, content_text, metadata,
                    1 - (embedding <=> :query_embedding) as similarity,
                    created_at
                FROM content_embeddings 
                WHERE user_id = :user_id 
                    AND 1 - (embedding <=> :query_embedding) > :threshold
                ORDER BY embedding <=> :query_embedding
                LIMIT :limit
            """)
            
            result = self.db.execute(query, {
                'user_id': user_id,
                'query_embedding': query_embedding,
                'threshold': similarity_threshold,
                'limit': limit
            })
            
            results = []
            for row in result:
                results.append({
                    'id': row.id,
                    'content_id': row.content_id,
                    'content_text': row.content_text,
                    'metadata': json.loads(row.metadata) if row.metadata else {},
                    'similarity': float(row.similarity),
                    'created_at': row.created_at.isoformat()
                })
            
            logger.info(f"Found {len(results)} similar content items for user {user_id}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search similar content: {e}")
            raise
    
    def similarity_search_memories(
        self,
        user_id: int,
        query_text: str,
        memory_type: Optional[str] = None,
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search for similar memories using cosine similarity"""
        try:
            # Generate query embedding
            query_embedding = self.get_embedding(query_text)
            
            # Build query with optional memory_type filter
            where_clause = "WHERE user_id = :user_id AND 1 - (embedding <=> :query_embedding) > :threshold"
            params = {
                'user_id': user_id,
                'query_embedding': query_embedding,
                'threshold': similarity_threshold,
                'limit': limit
            }
            
            if memory_type:
                where_clause += " AND memory_type = :memory_type"
                params['memory_type'] = memory_type
            
            query = text(f"""
                SELECT 
                    id, title, content, memory_type, metadata,
                    1 - (embedding <=> :query_embedding) as similarity,
                    created_at
                FROM memory_embeddings 
                {where_clause}
                ORDER BY embedding <=> :query_embedding
                LIMIT :limit
            """)
            
            result = self.db.execute(query, params)
            
            results = []
            for row in result:
                results.append({
                    'id': row.id,
                    'title': row.title,
                    'content': row.content,
                    'memory_type': row.memory_type,
                    'metadata': json.loads(row.metadata) if row.metadata else {},
                    'similarity': float(row.similarity),
                    'created_at': row.created_at.isoformat()
                })
            
            logger.info(f"Found {len(results)} similar memories for user {user_id}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search similar memories: {e}")
            raise
    
    def delete_content_embedding(self, user_id: int, content_id: int) -> bool:
        """Delete content embedding"""
        try:
            query = text("""
                DELETE FROM content_embeddings 
                WHERE user_id = :user_id AND content_id = :content_id
            """)
            
            result = self.db.execute(query, {
                'user_id': user_id,
                'content_id': content_id
            })
            
            deleted = result.rowcount > 0
            self.db.commit()
            
            if deleted:
                logger.info(f"Deleted content embedding for content {content_id}")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to delete content embedding: {e}")
            self.db.rollback()
            raise
    
    def delete_memory_embedding(self, user_id: int, memory_id: int) -> bool:
        """Delete memory embedding"""
        try:
            query = text("""
                DELETE FROM memory_embeddings 
                WHERE user_id = :user_id AND id = :memory_id
            """)
            
            result = self.db.execute(query, {
                'user_id': user_id,
                'memory_id': memory_id
            })
            
            deleted = result.rowcount > 0
            self.db.commit()
            
            if deleted:
                logger.info(f"Deleted memory embedding {memory_id}")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to delete memory embedding: {e}")
            self.db.rollback()
            raise
    
    def get_embedding_stats(self, user_id: int) -> Dict[str, Any]:
        """Get embedding statistics for user"""
        try:
            content_query = text("""
                SELECT COUNT(*) as count FROM content_embeddings 
                WHERE user_id = :user_id
            """)
            
            memory_query = text("""
                SELECT 
                    COUNT(*) as total_count,
                    COUNT(DISTINCT memory_type) as unique_types
                FROM memory_embeddings 
                WHERE user_id = :user_id
            """)
            
            content_result = self.db.execute(content_query, {'user_id': user_id})
            memory_result = self.db.execute(memory_query, {'user_id': user_id})
            
            content_count = content_result.fetchone().count
            memory_row = memory_result.fetchone()
            
            return {
                'content_embeddings': content_count,
                'memory_embeddings': memory_row.total_count,
                'unique_memory_types': memory_row.unique_types,
                'embedding_model': self.embedding_model,
                'embedding_dimensions': self.embedding_dimensions
            }
            
        except Exception as e:
            logger.error(f"Failed to get embedding stats: {e}")
            raise