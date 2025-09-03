"""
Integration tests for Autonomous Scheduler workflow
Tests the complete autonomous content generation and posting pipeline
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.db.database import get_test_db
from backend.db.models import User, UserSetting, WorkflowExecution, Content
from backend.tasks.autonomous_scheduler import (
    AutonomousScheduler,
    daily_content_generation,
    weekly_report_generation,
    nightly_metrics_collection,
    process_scheduled_content
)


class TestAutonomousSchedulerFlow:
    """Integration tests for autonomous scheduler workflow"""

    @pytest.fixture
    def db_session(self):
        """Create test database session"""
        db = next(get_test_db())
        try:
            yield db
        finally:
            db.close()

    @pytest.fixture
    def test_user_with_autonomous_mode(self, db_session: Session):
        """Create test user with autonomous mode enabled"""
        # Create user
        user = User(
            email="test_autonomous@example.com",
            hashed_password="hashed_test_password",
            is_active=True,
            is_verified=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Create user settings with autonomous mode
        user_setting = UserSetting(
            user_id=user.id,
            enable_autonomous_mode=True,
            preferred_platforms=["twitter", "instagram"],
            content_frequency=3,
            posting_times={"twitter": "09:00", "instagram": "10:00"},
            brand_voice="professional",
            creativity_level=0.7,
            timezone="UTC"
        )
        db_session.add(user_setting)
        db_session.commit()
        
        return user, user_setting

    def test_autonomous_scheduler_init(self):
        """Test AutonomousScheduler initialization"""
        scheduler = AutonomousScheduler()
        assert scheduler is not None
        assert hasattr(scheduler, 'research_service')
        assert scheduler.research_service is not None

    def test_get_active_users_for_autonomous_mode(self, db_session: Session, test_user_with_autonomous_mode):
        """Test getting users with autonomous mode enabled"""
        test_user, test_setting = test_user_with_autonomous_mode
        
        scheduler = AutonomousScheduler()
        
        # Mock the database session in the scheduler method
        with patch('backend.tasks.autonomous_scheduler.get_db') as mock_get_db:
            mock_get_db.return_value = [db_session]
            
            active_users = scheduler.get_active_users_for_autonomous_mode(db_session)
        
        assert len(active_users) == 1
        user_config = active_users[0]
        
        # Verify user configuration
        assert user_config['user_id'] == test_user.id
        assert user_config['email'] == test_user.email
        assert user_config['timezone'] == 'UTC'
        assert user_config['preferred_platforms'] == ["twitter", "instagram"]
        assert user_config['content_frequency'] == 3
        assert user_config['brand_voice'] == "professional"
        assert user_config['creativity_level'] == 0.7

    @patch('backend.tasks.autonomous_scheduler.get_db')
    @patch('backend.tasks.autonomous_scheduler.ProductionMemoryService')
    @patch('backend.tasks.autonomous_scheduler.ContentPersistenceService')
    def test_daily_content_generation_task(self, mock_content_service, mock_memory_service, mock_get_db, 
                                         db_session: Session, test_user_with_autonomous_mode):
        """Test daily content generation task execution"""
        test_user, test_setting = test_user_with_autonomous_mode
        
        # Setup mocks
        mock_get_db.return_value = [db_session]
        mock_content_instance = MagicMock()
        mock_content_service.return_value = mock_content_instance
        mock_memory_instance = MagicMock()
        mock_memory_service.return_value = mock_memory_instance
        
        # Mock content creation
        mock_content_item = MagicMock()
        mock_content_item.id = "test_content_id_123"
        mock_content_instance.create_content.return_value = mock_content_item
        
        # Mock memory service inspiration
        mock_memory_instance.get_content_inspiration.return_value = {
            'similar_content': ['inspiration1', 'inspiration2']
        }
        
        # Execute the task
        result = daily_content_generation()
        
        # Verify result structure
        assert result['status'] == 'completed'
        assert result['users_processed'] == 1
        assert result['successful'] == 1
        assert result['failed'] == 0
        assert len(result['results']) == 1
        
        # Verify user result
        user_result = result['results'][0]
        assert user_result['user_id'] == test_user.id
        assert user_result['status'] == 'success'
        assert 'workflow_id' in user_result
        
        # Verify workflow execution was created
        workflow_executions = db_session.query(WorkflowExecution).filter(
            WorkflowExecution.user_id == test_user.id,
            WorkflowExecution.workflow_type == 'daily_autonomous'
        ).all()
        
        assert len(workflow_executions) >= 1
        latest_workflow = workflow_executions[-1]
        assert latest_workflow.status == 'completed'
        assert 'content_items_created' in latest_workflow.results

    @patch('backend.tasks.autonomous_scheduler.get_db')
    @patch('backend.tasks.autonomous_scheduler.ContentPersistenceService')
    @patch('backend.tasks.autonomous_scheduler.ProductionMemoryService')
    def test_weekly_report_generation_task(self, mock_memory_service, mock_content_service, mock_get_db,
                                         db_session: Session, test_user_with_autonomous_mode):
        """Test weekly report generation task"""
        test_user, test_setting = test_user_with_autonomous_mode
        
        # Setup mocks
        mock_get_db.return_value = [db_session]
        mock_content_instance = MagicMock()
        mock_content_service.return_value = mock_content_instance
        mock_memory_instance = MagicMock()
        mock_memory_service.return_value = mock_memory_instance
        
        # Mock content list
        mock_content_instance.get_content_list.return_value = {
            'content': [
                {'id': '1', 'title': 'Test content 1'},
                {'id': '2', 'title': 'Test content 2'}
            ]
        }
        
        # Create some workflow executions for the past week
        past_workflows = [
            WorkflowExecution(
                user_id=test_user.id,
                workflow_type='daily_autonomous',
                status='completed',
                created_at=datetime.utcnow() - timedelta(days=i)
            ) for i in range(1, 8)  # 7 workflows from past week
        ]
        
        for workflow in past_workflows:
            db_session.add(workflow)
        db_session.commit()
        
        # Execute the task
        result = weekly_report_generation()
        
        # Verify result
        assert result['status'] == 'completed'
        assert result['reports_generated'] == 1
        assert 'timestamp' in result
        
        # Verify memory service was called to store the report
        mock_memory_instance.store_insight_memory.assert_called_once()
        call_args = mock_memory_instance.store_insight_memory.call_args
        assert call_args[1]['user_id'] == test_user.id
        assert 'Weekly Autonomous Report' in call_args[1]['title']
        assert call_args[1]['insight_type'] == 'weekly_report'

    @patch('backend.tasks.autonomous_scheduler.get_db')
    @patch('backend.tasks.autonomous_scheduler.ContentPersistenceService')
    def test_nightly_metrics_collection_task(self, mock_content_service, mock_get_db,
                                            db_session: Session, test_user_with_autonomous_mode):
        """Test nightly metrics collection task"""
        test_user, test_setting = test_user_with_autonomous_mode
        
        # Setup mocks
        mock_get_db.return_value = [db_session]
        mock_content_instance = MagicMock()
        mock_content_service.return_value = mock_content_instance
        
        # Mock recent published content
        yesterday = datetime.utcnow() - timedelta(days=1)
        mock_content_instance.get_content_list.return_value = {
            'content': [
                {
                    'id': 'content_123',
                    'content': 'Test content for metrics',
                    'platform': 'twitter',
                    'published_at': yesterday.isoformat() + 'Z'
                },
                {
                    'id': 'content_456',
                    'content': 'Another test content',
                    'platform': 'instagram',
                    'published_at': yesterday.isoformat() + 'Z'
                }
            ]
        }
        
        # Execute the task
        result = nightly_metrics_collection()
        
        # Verify result
        assert result['status'] == 'completed'
        assert result['metrics_collected'] >= 2
        assert result['users_processed'] == 1
        assert 'timestamp' in result
        
        # Verify metrics were updated for content
        assert mock_content_instance.update_engagement_metrics.call_count >= 2

    @patch('backend.tasks.autonomous_scheduler.get_db')
    @patch('backend.tasks.autonomous_scheduler.ContentPersistenceService')
    def test_process_scheduled_content_task(self, mock_content_service, mock_get_db,
                                          db_session: Session):
        """Test scheduled content posting task"""
        # Setup mocks
        mock_get_db.return_value = [db_session]
        mock_content_instance = MagicMock()
        mock_content_service.return_value = mock_content_instance
        
        # Mock scheduled content
        now = datetime.utcnow()
        mock_content_item_1 = MagicMock()
        mock_content_item_1.id = "scheduled_content_123"
        mock_content_item_1.user_id = "user_123"
        mock_content_item_1.platform = "twitter"
        mock_content_item_1.content = "Scheduled tweet content"
        mock_content_item_1.scheduled_for = now - timedelta(minutes=5)  # Ready to post
        
        mock_content_item_2 = MagicMock()
        mock_content_item_2.id = "scheduled_content_456"
        mock_content_item_2.user_id = "user_456"
        mock_content_item_2.platform = "instagram"
        mock_content_item_2.content = "Scheduled Instagram post"
        mock_content_item_2.scheduled_for = now - timedelta(minutes=10)  # Ready to post
        
        mock_content_instance.get_scheduled_content.return_value = [
            mock_content_item_1,
            mock_content_item_2
        ]
        
        # Execute the task
        result = process_scheduled_content()
        
        # Verify result
        assert result['status'] == 'completed'
        assert result['posts_processed'] == 2
        assert result['successful_posts'] == 2
        assert result['failed_posts'] == 0
        assert 'timestamp' in result
        
        # Verify content was marked as published
        assert mock_content_instance.mark_as_published.call_count == 2

    def test_scheduler_error_handling(self, db_session: Session):
        """Test error handling in scheduler tasks"""
        scheduler = AutonomousScheduler()
        
        # Test with database error
        with patch.object(db_session, 'query', side_effect=Exception("Database error")):
            users = scheduler.get_active_users_for_autonomous_mode(db_session)
            assert users == []  # Should return empty list on error

    @patch('backend.tasks.autonomous_scheduler.get_db')
    def test_task_failure_handling(self, mock_get_db):
        """Test task failure scenarios"""
        # Mock database failure
        mock_get_db.side_effect = Exception("Database connection failed")
        
        # Test daily content generation with database failure
        with pytest.raises(Exception):
            daily_content_generation()
        
        # Test weekly report generation with database failure
        with pytest.raises(Exception):
            weekly_report_generation()
        
        # Test metrics collection with database failure
        with pytest.raises(Exception):
            nightly_metrics_collection()
        
        # Test content posting with database failure
        with pytest.raises(Exception):
            process_scheduled_content()

    def test_content_scheduling_logic(self, db_session: Session, test_user_with_autonomous_mode):
        """Test content scheduling logic in daily content generation"""
        test_user, test_setting = test_user_with_autonomous_mode
        
        scheduler = AutonomousScheduler()
        
        # Test scheduling for different platforms
        with patch('backend.tasks.autonomous_scheduler.get_db') as mock_get_db, \
             patch('backend.tasks.autonomous_scheduler.ContentPersistenceService') as mock_content_service, \
             patch('backend.tasks.autonomous_scheduler.ProductionMemoryService') as mock_memory_service:
            
            mock_get_db.return_value = [db_session]
            mock_content_instance = MagicMock()
            mock_content_service.return_value = mock_content_instance
            mock_memory_instance = MagicMock()
            mock_memory_service.return_value = mock_memory_instance
            
            # Mock content creation to capture scheduling times
            mock_content_item = MagicMock()
            mock_content_item.id = "test_content_id"
            mock_content_instance.create_content.return_value = mock_content_item
            
            mock_memory_instance.get_content_inspiration.return_value = {'similar_content': []}
            
            # Execute task
            result = daily_content_generation()
            
            # Verify create_content was called for each platform
            create_calls = mock_content_instance.create_content.call_args_list
            assert len(create_calls) >= 2  # At least for twitter and instagram
            
            # Verify scheduling times are set for tomorrow
            for call in create_calls:
                call_kwargs = call[1]
                assert 'scheduled_at' in call_kwargs
                scheduled_time = call_kwargs['scheduled_at']
                tomorrow = datetime.utcnow() + timedelta(days=1)
                assert scheduled_time.date() == tomorrow.date()

    def test_task_metadata_and_tracking(self, db_session: Session, test_user_with_autonomous_mode):
        """Test that tasks properly track metadata and execution history"""
        test_user, test_setting = test_user_with_autonomous_mode
        
        with patch('backend.tasks.autonomous_scheduler.get_db') as mock_get_db, \
             patch('backend.tasks.autonomous_scheduler.ContentPersistenceService') as mock_content_service, \
             patch('backend.tasks.autonomous_scheduler.ProductionMemoryService') as mock_memory_service:
            
            mock_get_db.return_value = [db_session]
            mock_content_instance = MagicMock()
            mock_content_service.return_value = mock_content_instance
            mock_memory_instance = MagicMock()
            mock_memory_service.return_value = mock_memory_instance
            
            mock_content_item = MagicMock()
            mock_content_item.id = "test_content_with_metadata"
            mock_content_instance.create_content.return_value = mock_content_item
            
            mock_memory_instance.get_content_inspiration.return_value = {'similar_content': ['inspiration1']}
            
            # Execute task
            result = daily_content_generation()
            
            # Verify workflow execution was created with proper metadata
            workflow_executions = db_session.query(WorkflowExecution).filter(
                WorkflowExecution.user_id == test_user.id,
                WorkflowExecution.workflow_type == 'daily_autonomous'
            ).all()
            
            assert len(workflow_executions) >= 1
            latest_workflow = workflow_executions[-1]
            
            # Verify metadata structure
            assert latest_workflow.results is not None
            assert 'content_items_created' in latest_workflow.results
            assert 'research_quality_score' in latest_workflow.results
            assert 'platforms_processed' in latest_workflow.results
            
            # Verify content metadata
            create_calls = mock_content_instance.create_content.call_args_list
            for call in create_calls:
                call_kwargs = call[1]
                assert 'metadata' in call_kwargs
                metadata = call_kwargs['metadata']
                assert 'generated_by' in metadata
                assert metadata['generated_by'] == 'autonomous_scheduler'
                assert 'research_data' in metadata
                assert 'inspiration_sources' in metadata