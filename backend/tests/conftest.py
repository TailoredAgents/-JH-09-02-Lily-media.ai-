import pytest
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Import application components
from backend.main import app
from backend.db.database import get_db, Base
from backend.db.models import User, ContentItem, Goal, GoalProgress, Memory
from backend.auth.dependencies import get_current_user, get_optional_user

# Import multi-tenancy fixtures
from backend.tests.fixtures.multi_tenant_fixtures import *

# Import Redis test fixtures
from backend.tests.fixtures.redis_fixtures import *

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    echo=False
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def test_db():
    """Create test database and tables"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(test_db):
    """Create a fresh database session for each test"""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def override_get_db(db_session):
    """Override the get_db dependency to use test database"""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass
    return _override_get_db

@pytest.fixture
def client(override_get_db):
    """Create a test client with database override"""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

# User fixtures
@pytest.fixture
def test_user_data():
    """Sample user data for testing"""
    return {
        "user_id": "test_user_123",
        "email": "test@example.com",
        "name": "Test User",
        "auth_provider": "auth0",
        "profile_data": {
            "picture": "https://example.com/avatar.jpg",
            "verified": True
        }
    }

@pytest.fixture
def test_user(db_session, test_user_data):
    """Create a test user in the database"""
    user = User(**test_user_data)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def auth_headers(test_user):
    """Generate auth headers for API requests"""
    return {
        "Authorization": f"Bearer test_token_{test_user.user_id}",
        "Content-Type": "application/json"
    }

# Mock fixtures for external services
@pytest.fixture
def mock_openai():
    """Mock OpenAI API calls"""
    with patch('openai.embeddings.create') as mock_embedding:
        mock_embedding.return_value = Mock()
        mock_embedding.return_value.data = [Mock()]
        mock_embedding.return_value.data[0].embedding = [0.1] * 1536
        yield mock_embedding

@pytest.fixture
def mock_faiss():
    """Mock FAISS vector store operations"""
    with patch('backend.core.vector_store.VectorStore') as mock_vector_store:
        mock_instance = Mock()
        mock_instance.add_vectors.return_value = ['test_id_1']
        mock_instance.search.return_value = [
            {'id': 'test_id_1', 'score': 0.95, 'metadata': {'content': 'test'}}
        ]
        mock_vector_store.return_value = mock_instance
        yield mock_instance

# Additional fixtures for comprehensive testing
@pytest.fixture
def mock_celery():
    """Mock Celery task execution"""
    with patch('backend.tasks.celery_app.celery') as mock_celery_app:
        mock_task = Mock()
        mock_task.delay.return_value = Mock(id='test_task_id', status='SUCCESS')
        mock_celery_app.send_task.return_value = mock_task.delay.return_value
        yield mock_celery_app

@pytest.fixture
def mock_social_media_apis():
    """Mock all social media API calls"""
    mocks = {}
    
    # Twitter API mock
    with patch('backend.integrations.twitter_client.TwitterAPIClient') as mock_twitter:
        mock_twitter_instance = Mock()
        mock_twitter_instance.post_tweet.return_value = {'id': 'tweet_123', 'created_at': '2025-07-25T10:00:00Z'}
        mock_twitter_instance.get_metrics.return_value = {'likes': 10, 'retweets': 5, 'replies': 2}
        mock_twitter.return_value = mock_twitter_instance
        mocks['twitter'] = mock_twitter_instance
        
        # LinkedIn API mock
        with patch('backend.integrations.LinkedInAPIClient') as mock_linkedin:
            mock_linkedin_instance = Mock()
            mock_linkedin_instance.create_post.return_value = {'id': 'post_456', 'created_at': '2025-07-25T10:00:00Z'}
            mock_linkedin_instance.get_post_metrics.return_value = {'likes': 15, 'comments': 3, 'shares': 8}
            mock_linkedin.return_value = mock_linkedin_instance
            mocks['linkedin'] = mock_linkedin_instance
            
            # Instagram API mock
            with patch('backend.integrations.instagram_client.InstagramAPIClient') as mock_instagram:
                mock_instagram_instance = Mock()
                mock_instagram_instance.create_media.return_value = {'id': 'media_789', 'created_at': '2025-07-25T10:00:00Z'}
                mock_instagram_instance.get_media_insights.return_value = {'likes': 25, 'comments': 8, 'saves': 5}
                mock_instagram.return_value = mock_instagram_instance
                mocks['instagram'] = mock_instagram_instance
                
                yield mocks

@pytest.fixture
def mock_auth0_user():
    """Mock Auth0 user authentication"""
    def _override_auth_user():
        return {
            'sub': 'auth0|test_user_123',
            'email': 'test@example.com',
            'name': 'Test User',
            'email_verified': True,
            'picture': 'https://example.com/avatar.jpg'
        }
    
    with patch('backend.auth.dependencies.get_current_user', return_value=_override_auth_user()):
        yield _override_auth_user()

@pytest.fixture
def authenticated_client(client, mock_auth0_user):
    """Test client with authenticated user"""
    app.dependency_overrides[get_current_user] = lambda: mock_auth0_user
    yield client
    app.dependency_overrides.clear()

@pytest.fixture
def sample_content_data():
    """Sample content data for testing"""
    return {
        "title": "Test Content Title",
        "content": "This is test content for social media posting.",
        "platform": "twitter",
        "content_type": "text",
        "metadata": {
            "hashtags": ["#test", "#socialmedia"],
            "mentions": ["@testuser"],
            "target_audience": "general",
            "tone": "professional"
        },
        "scheduled_time": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    }

@pytest.fixture
def sample_goal_data():
    """Sample goal data for testing"""
    return {
        "title": "Increase Twitter Followers",
        "description": "Grow Twitter following to 10,000 followers by end of year",
        "target_metric": "followers",
        "target_value": 10000,
        "current_value": 5000,
        "target_date": (datetime.now(timezone.utc) + timedelta(days=180)).isoformat(),
        "category": "growth",
        "priority": "high"
    }

@pytest.fixture(scope="session")
def performance_test_data():
    """Large dataset for performance testing"""
    return {
        'users': 100,
        'content_per_user': 50,
        'goals_per_user': 5,
        'memories_per_user': 20
    }