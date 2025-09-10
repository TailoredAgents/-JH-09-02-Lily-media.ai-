"""
PW-DM-ADD-001: Unit tests for Job Service

Focused unit tests for job service business logic, status transitions,
and quote-to-job conversion workflows.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock

from backend.services.job_service import JobService, JobCreationRequest, JobUpdateRequest
from backend.db.models import Job, Quote


class TestJobService:
    """Unit tests for JobService business logic"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = JobService()
        self.mock_db = Mock()
    
    def test_generate_job_number_sequential(self):
        """Test job number generation is sequential per organization"""
        org_id = "test-org-12345"
        
        # Mock job count query for first job
        self.mock_db.query.return_value.filter.return_value.count.return_value = 0
        job_number_1 = self.service._generate_job_number(org_id, self.mock_db)
        
        # Mock job count query for second job  
        self.mock_db.query.return_value.filter.return_value.count.return_value = 1
        job_number_2 = self.service._generate_job_number(org_id, self.mock_db)
        
        assert job_number_1 == "JOB-TEST-ORG-0001"
        assert job_number_2 == "JOB-TEST-ORG-0002"
    
    def test_extract_primary_service_from_line_items(self):
        """Test extracting primary service from quote line items"""
        line_items = [
            {"service": "driveway_cleaning", "total": 150.00},
            {"service": "house_washing", "total": 450.00},  # Highest
            {"service": "deck_staining", "total": 200.00}
        ]
        
        primary_service = self.service._extract_primary_service_type(line_items)
        assert primary_service == "house_washing"
    
    def test_extract_primary_service_empty_fallback(self):
        """Test fallback when no line items provided"""
        primary_service = self.service._extract_primary_service_type([])
        assert primary_service == "pressure_washing"
    
    def test_extract_service_details(self):
        """Test service details extraction from line items"""
        line_items = [
            {"service": "patio_cleaning", "total": 100.00, "area": 200},
            {"service": "walkway_cleaning", "total": 75.00}
        ]
        
        details = self.service._extract_service_details(line_items)
        
        assert details["total_line_items"] == 2
        assert "patio_cleaning" in details["services_included"]
        assert "walkway_cleaning" in details["services_included"]
        assert details["line_items"] == line_items
    
    def test_get_valid_transitions(self):
        """Test valid status transition mappings"""
        # Test scheduled state transitions
        scheduled_transitions = self.service._get_valid_transitions("scheduled")
        assert set(scheduled_transitions) == {"in_progress", "canceled", "rescheduled"}
        
        # Test in_progress state transitions
        in_progress_transitions = self.service._get_valid_transitions("in_progress")
        assert set(in_progress_transitions) == {"completed", "canceled"}
        
        # Test completed state (terminal)
        completed_transitions = self.service._get_valid_transitions("completed")
        assert completed_transitions == []
        
        # Test canceled state (terminal)
        canceled_transitions = self.service._get_valid_transitions("canceled")
        assert canceled_transitions == []
    
    @patch('backend.services.job_service.Job')
    @patch('backend.services.job_service.get_audit_logger')
    def test_create_job_from_quote_success(self, mock_audit_logger, mock_job_class):
        """Test successful job creation from accepted quote"""
        # Mock accepted quote
        mock_quote = Mock(spec=Quote)
        mock_quote.id = "quote-123"
        mock_quote.status = "accepted"
        mock_quote.organization_id = "org-456"
        mock_quote.lead_id = "lead-789" 
        mock_quote.total = Decimal("350.00")
        mock_quote.currency = "USD"
        mock_quote.customer_name = "John Smith"
        mock_quote.customer_phone = "+1555123456"
        mock_quote.customer_email = "john@example.com"
        mock_quote.customer_address = "123 Main St"
        mock_quote.line_items = [
            {"service": "driveway_wash", "total": 200.00},
            {"service": "sidewalk_wash", "total": 150.00}
        ]
        
        # Mock job instance
        mock_job_instance = Mock()
        mock_job_instance.id = "job-abc"
        mock_job_class.return_value = mock_job_instance
        
        # Mock database operations
        self.mock_db.add.return_value = None
        self.mock_db.commit.return_value = None
        self.mock_db.refresh.return_value = None
        
        # Mock job count for number generation
        self.mock_db.query.return_value.filter.return_value.count.return_value = 5
        
        # Execute
        scheduled_time = datetime.now(timezone.utc) + timedelta(days=2)
        result = self.service.create_job_from_quote(
            quote=mock_quote,
            scheduled_for=scheduled_time,
            duration_minutes=120,
            db=self.mock_db,
            user_id=42,
            crew={"tech": "Mike", "size": 2},
            internal_notes="Priority customer"
        )
        
        # Verify job creation
        assert result == mock_job_instance
        mock_job_class.assert_called_once()
        
        # Verify job properties
        job_kwargs = mock_job_class.call_args.kwargs
        assert job_kwargs["organization_id"] == "org-456"
        assert job_kwargs["quote_id"] == "quote-123" 
        assert job_kwargs["lead_id"] == "lead-789"
        assert job_kwargs["service_type"] == "driveway_wash"  # Primary (highest cost)
        assert job_kwargs["estimated_cost"] == Decimal("350.00")
        assert job_kwargs["customer_name"] == "John Smith"
        assert job_kwargs["scheduled_for"] == scheduled_time
        assert job_kwargs["duration_minutes"] == 120
        assert job_kwargs["crew"] == {"tech": "Mike", "size": 2}
        assert job_kwargs["status"] == "scheduled"
        assert job_kwargs["created_by_id"] == 42
        
        # Verify database operations
        self.mock_db.add.assert_called_once_with(mock_job_instance)
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once_with(mock_job_instance)
        
        # Verify audit logging
        mock_audit_logger.return_value.log_event.assert_called_once()
    
    def test_create_job_from_quote_wrong_status(self):
        """Test job creation fails with non-accepted quote"""
        mock_quote = Mock()
        mock_quote.status = "draft"
        
        with pytest.raises(ValueError) as exc_info:
            self.service.create_job_from_quote(
                quote=mock_quote,
                scheduled_for=datetime.now(timezone.utc) + timedelta(days=1),
                duration_minutes=60,
                db=self.mock_db,
                user_id=1
            )
        
        assert "Quote must be accepted" in str(exc_info.value)
        self.mock_db.rollback.assert_called_once()
    
    @patch('backend.services.job_service.Job')
    @patch('backend.services.job_service.get_audit_logger')
    def test_create_job_direct_success(self, mock_audit_logger, mock_job_class):
        """Test direct job creation (not from quote)"""
        # Mock job instance
        mock_job_instance = Mock()
        mock_job_instance.id = "job-direct-123"
        mock_job_class.return_value = mock_job_instance
        
        # Mock database operations
        self.mock_db.add.return_value = None
        self.mock_db.commit.return_value = None
        self.mock_db.refresh.return_value = None
        
        # Mock job count for number generation
        self.mock_db.query.return_value.filter.return_value.count.return_value = 10
        
        # Create request
        scheduled_time = datetime.now(timezone.utc) + timedelta(hours=24)
        request = JobCreationRequest(
            organization_id="org-direct",
            service_type="roof_cleaning",
            address="456 Oak Avenue",
            estimated_cost=750.00,
            customer_name="Sarah Jones",
            customer_email="sarah@example.com",
            customer_phone="+1555987654",
            scheduled_for=scheduled_time,
            duration_minutes=300,
            service_details={"roof_type": "shingle", "stories": 2},
            crew={"lead": "Tom", "helpers": 3},
            crew_notes="Bring safety equipment",
            internal_notes="Repeat customer",
            priority="high"
        )
        
        # Execute
        result = self.service.create_job_direct(request, self.mock_db, 99)
        
        # Verify result
        assert result == mock_job_instance
        
        # Verify job creation parameters
        job_kwargs = mock_job_class.call_args.kwargs
        assert job_kwargs["organization_id"] == "org-direct"
        assert job_kwargs["service_type"] == "roof_cleaning"
        assert job_kwargs["address"] == "456 Oak Avenue"
        assert job_kwargs["estimated_cost"] == 750.00
        assert job_kwargs["customer_name"] == "Sarah Jones"
        assert job_kwargs["scheduled_for"] == scheduled_time
        assert job_kwargs["priority"] == "high"
        assert job_kwargs["created_by_id"] == 99
        
        # Verify database operations
        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called_once()
        
        # Verify audit logging
        mock_audit_logger.return_value.log_event.assert_called_once()
    
    def test_update_job_status_change_with_timestamps(self):
        """Test job update with status change sets appropriate timestamps"""
        # Mock job
        mock_job = Mock()
        mock_job.status = "scheduled"
        mock_job.can_transition_to.return_value = True
        mock_job.scheduled_for = None
        mock_job.duration_minutes = None
        mock_job.crew = {}
        mock_job.actual_cost = None
        mock_job.priority = "normal"
        
        # Mock database operations
        self.mock_db.commit.return_value = None
        self.mock_db.refresh.return_value = None
        
        # Create update request
        update_request = JobUpdateRequest(
            status="in_progress",
            completion_notes="Starting work now"
        )
        
        # Execute update
        with patch('backend.services.job_service.datetime') as mock_datetime:
            mock_now = datetime.now(timezone.utc)
            mock_datetime.now.return_value = mock_now
            mock_datetime.timezone = timezone
            
            result = self.service.update_job(mock_job, update_request, self.mock_db, 15)
        
        # Verify status and timestamp were set
        assert mock_job.status == "in_progress"
        assert mock_job.started_at == mock_now
        assert mock_job.completion_notes == "Starting work now"
        assert mock_job.updated_by_id == 15
        
        # Verify database operations
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once()
    
    def test_update_job_invalid_status_transition(self):
        """Test job update fails with invalid status transition"""
        # Mock job that doesn't allow transition
        mock_job = Mock()
        mock_job.status = "completed"
        mock_job.can_transition_to.return_value = False
        
        update_request = JobUpdateRequest(status="scheduled")
        
        with pytest.raises(ValueError) as exc_info:
            self.service.update_job(mock_job, update_request, self.mock_db, 1)
        
        assert "Cannot transition job" in str(exc_info.value)
        self.mock_db.rollback.assert_called_once()
    
    def test_update_job_customer_satisfaction_validation(self):
        """Test customer satisfaction rating validation"""
        mock_job = Mock()
        mock_job.status = "completed"
        mock_job.actual_cost = None
        
        # Invalid rating (too high)
        update_request = JobUpdateRequest(customer_satisfaction=6)
        
        with pytest.raises(ValueError) as exc_info:
            self.service.update_job(mock_job, update_request, self.mock_db, 1)
        
        assert "Customer satisfaction must be between 1 and 5" in str(exc_info.value)
    
    def test_reschedule_job_success(self):
        """Test successful job rescheduling"""
        # Mock job that can be rescheduled
        old_time = datetime.now(timezone.utc) + timedelta(days=1)
        mock_job = Mock()
        mock_job.id = "job-reschedule-123"
        mock_job.status = "scheduled"
        mock_job.scheduled_for = old_time
        mock_job.internal_notes = "Previous notes"
        
        # Mock database operations
        self.mock_db.commit.return_value = None
        self.mock_db.refresh.return_value = None
        
        # Execute reschedule
        new_time = datetime.now(timezone.utc) + timedelta(days=3)
        result = self.service.reschedule_job(
            job=mock_job,
            new_scheduled_time=new_time,
            reason="Customer requested change",
            db=self.mock_db,
            user_id=88
        )
        
        # Verify updates
        assert mock_job.scheduled_for == new_time
        assert mock_job.status == "rescheduled"
        assert mock_job.updated_by_id == 88
        assert "Customer requested change" in mock_job.internal_notes
        assert "Rescheduled from" in mock_job.internal_notes
        
        # Verify database operations
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once()
    
    def test_reschedule_job_wrong_status_fails(self):
        """Test rescheduling fails for jobs in wrong status"""
        mock_job = Mock()
        mock_job.status = "completed"  # Cannot reschedule completed jobs
        
        with pytest.raises(ValueError) as exc_info:
            self.service.reschedule_job(
                job=mock_job,
                new_scheduled_time=datetime.now(timezone.utc) + timedelta(days=1),
                reason="Test",
                db=self.mock_db,
                user_id=1
            )
        
        assert "Cannot reschedule job with status 'completed'" in str(exc_info.value)
        self.mock_db.rollback.assert_called_once()
    
    @patch('backend.services.job_service.asyncio.create_task')
    def test_update_job_sends_status_notification(self, mock_create_task):
        """Test that status changes trigger notifications"""
        # Mock job
        mock_job = Mock()
        mock_job.status = "in_progress"
        mock_job.can_transition_to.return_value = True
        mock_job.organization_id = "org-notify"
        mock_job.id = "job-notify-123"
        mock_job.job_number = "JOB-TEST-0001"
        mock_job.address = "123 Notify St"
        mock_job.customer_name = "Notify Customer"
        
        # Mock database operations
        self.mock_db.commit.return_value = None
        self.mock_db.refresh.return_value = None
        
        # Update to completed
        update_request = JobUpdateRequest(status="completed")
        
        with patch('backend.services.job_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.now(timezone.utc)
            mock_datetime.timezone = timezone
            
            self.service.update_job(mock_job, update_request, self.mock_db, 77)
        
        # Verify notification task was created
        mock_create_task.assert_called_once()


class TestJobCreationRequest:
    """Test JobCreationRequest data class"""
    
    def test_creation_request_defaults(self):
        """Test JobCreationRequest with default values"""
        request = JobCreationRequest(
            organization_id="org-123",
            service_type="test_service", 
            address="Test Address",
            estimated_cost=100.0
        )
        
        assert request.organization_id == "org-123"
        assert request.service_type == "test_service"
        assert request.estimated_cost == 100.0
        assert request.service_details == {}
        assert request.crew == {}
        assert request.priority == "normal"
        assert request.currency == "USD"
        assert request.customer_name is None
        assert request.scheduled_for is None


class TestJobUpdateRequest:
    """Test JobUpdateRequest data class"""
    
    def test_update_request_all_none_by_default(self):
        """Test JobUpdateRequest defaults to None for all fields"""
        request = JobUpdateRequest()
        
        assert request.scheduled_for is None
        assert request.status is None
        assert request.completion_notes is None
        assert request.customer_satisfaction is None
        assert request.actual_cost is None
        assert request.crew is None
        assert request.priority is None