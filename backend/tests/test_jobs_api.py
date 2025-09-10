"""
PW-DM-ADD-001: Comprehensive tests for Jobs API and Job Service

Tests the complete job management system: creation from quotes, direct creation,
status transitions, rescheduling, and organization isolation.
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.db.models import Job, Quote, Lead, User, Organization
from backend.services.job_service import JobService, JobCreationRequest, JobUpdateRequest
from backend.api.jobs import JobCreateRequest, JobCreateFromQuoteRequest, JobUpdateRequest as APIJobUpdateRequest


class TestJobModel:
    """Test the Job ORM model"""
    
    def test_job_creation(self, test_db: Session, test_user: User, test_org: Organization):
        """Test basic job creation"""
        job = Job(
            organization_id=test_org.id,
            service_type="pressure_washing",
            address="123 Main St",
            estimated_cost=Decimal("299.99"),
            customer_name="John Doe",
            customer_email="john@example.com",
            created_by_id=test_user.id
        )
        
        test_db.add(job)
        test_db.commit()
        test_db.refresh(job)
        
        assert job.id is not None
        assert job.organization_id == test_org.id
        assert job.status == "scheduled"  # Default status
        assert job.priority == "normal"  # Default priority
        assert job.currency == "USD"  # Default currency
        assert job.created_at is not None
    
    def test_job_status_transitions(self, test_db: Session, test_user: User, test_org: Organization):
        """Test job status transition validation"""
        job = Job(
            organization_id=test_org.id,
            service_type="pressure_washing",
            address="123 Main St",
            estimated_cost=Decimal("299.99"),
            status="scheduled",
            created_by_id=test_user.id
        )
        
        # Valid transitions from scheduled
        assert job.can_transition_to("in_progress") is True
        assert job.can_transition_to("canceled") is True
        assert job.can_transition_to("rescheduled") is True
        assert job.can_transition_to("completed") is False  # Can't go directly from scheduled to completed
        
        # Test completed state (terminal)
        job.status = "completed"
        assert job.can_transition_to("scheduled") is False
        assert job.can_transition_to("in_progress") is False
        assert job.can_transition_to("canceled") is False
    
    def test_job_is_overdue(self, test_db: Session, test_user: User, test_org: Organization):
        """Test overdue job detection"""
        # Job scheduled in the past
        past_time = datetime.now(timezone.utc) - timedelta(hours=2)
        overdue_job = Job(
            organization_id=test_org.id,
            service_type="pressure_washing",
            address="123 Main St",
            estimated_cost=Decimal("299.99"),
            scheduled_for=past_time,
            status="scheduled",
            created_by_id=test_user.id
        )
        
        assert overdue_job.is_overdue() is True
        
        # Completed job in the past (not overdue)
        overdue_job.status = "completed"
        assert overdue_job.is_overdue() is False
        
        # Future job (not overdue)
        future_time = datetime.now(timezone.utc) + timedelta(hours=2)
        overdue_job.scheduled_for = future_time
        overdue_job.status = "scheduled"
        assert overdue_job.is_overdue() is False
    
    def test_job_to_dict(self, test_db: Session, test_user: User, test_org: Organization):
        """Test job serialization to dictionary"""
        scheduled_time = datetime.now(timezone.utc) + timedelta(days=1)
        job = Job(
            organization_id=test_org.id,
            service_type="house_washing",
            address="456 Oak Ave",
            estimated_cost=Decimal("599.50"),
            scheduled_for=scheduled_time,
            duration_minutes=120,
            customer_name="Jane Smith",
            customer_email="jane@example.com",
            crew={"lead_tech": "Mike", "crew_size": 2},
            created_by_id=test_user.id
        )
        
        job_dict = job.to_dict()
        
        assert job_dict["service_type"] == "house_washing"
        assert job_dict["estimated_cost"] == 599.50
        assert job_dict["scheduled_for"] == scheduled_time.isoformat()
        assert job_dict["duration_minutes"] == 120
        assert job_dict["customer_name"] == "Jane Smith"
        assert job_dict["crew"]["lead_tech"] == "Mike"


class TestJobService:
    """Test the Job Service business logic"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = JobService()
        self.mock_db = Mock()
        self.mock_user = Mock()
        self.mock_user.id = 1
        self.mock_org = Mock()
        self.mock_org.id = "org-123"
    
    def test_generate_job_number(self):
        """Test job number generation"""
        # Mock job count query
        self.mock_db.query.return_value.filter.return_value.count.return_value = 5
        
        job_number = self.service._generate_job_number("test-org-123", self.mock_db)
        
        assert job_number.startswith("JOB-TEST-ORG")
        assert job_number.endswith("0006")  # 5 existing + 1 = 6
    
    def test_extract_primary_service_type(self):
        """Test service type extraction from line items"""
        line_items = [
            {"service": "driveway_cleaning", "total": 150.00},
            {"service": "house_washing", "total": 400.00},
            {"service": "deck_cleaning", "total": 100.00}
        ]
        
        service_type = self.service._extract_primary_service_type(line_items)
        assert service_type == "house_washing"  # Highest cost service
        
        # Test empty line items
        service_type = self.service._extract_primary_service_type([])
        assert service_type == "pressure_washing"  # Default fallback
    
    def test_create_job_from_quote_validation(self):
        """Test job creation from quote with status validation"""
        # Mock quote with wrong status
        mock_quote = Mock()
        mock_quote.status = "draft"
        mock_quote.organization_id = "org-123"
        
        with pytest.raises(ValueError, match="Quote must be accepted"):
            self.service.create_job_from_quote(
                quote=mock_quote,
                scheduled_for=datetime.now(timezone.utc) + timedelta(days=1),
                duration_minutes=120,
                db=self.mock_db,
                user_id=1
            )
    
    @patch('backend.services.job_service.get_audit_logger')
    def test_create_job_from_quote_success(self, mock_audit_logger):
        """Test successful job creation from accepted quote"""
        # Mock accepted quote
        mock_quote = Mock()
        mock_quote.id = "quote-456"
        mock_quote.status = "accepted"
        mock_quote.organization_id = "org-123"
        mock_quote.lead_id = "lead-789"
        mock_quote.total = Decimal("500.00")
        mock_quote.currency = "USD"
        mock_quote.customer_name = "Alice Johnson"
        mock_quote.customer_phone = "+1234567890"
        mock_quote.customer_email = "alice@example.com"
        mock_quote.customer_address = "789 Pine St"
        mock_quote.line_items = [{"service": "house_washing", "total": 500.00}]
        
        # Mock database operations
        mock_job = Mock()
        mock_job.id = "job-123"
        self.mock_db.add.return_value = None
        self.mock_db.commit.return_value = None
        self.mock_db.refresh.return_value = None
        
        # Mock job count for number generation
        self.mock_db.query.return_value.filter.return_value.count.return_value = 0
        
        with patch('backend.services.job_service.Job', return_value=mock_job):
            scheduled_time = datetime.now(timezone.utc) + timedelta(days=1)
            
            result = self.service.create_job_from_quote(
                quote=mock_quote,
                scheduled_for=scheduled_time,
                duration_minutes=180,
                db=self.mock_db,
                user_id=1
            )
        
        # Verify job was created
        assert result == mock_job
        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called_once()
        
        # Verify audit logging
        mock_audit_logger.return_value.log_event.assert_called_once()
    
    def test_update_job_status_transition_validation(self):
        """Test job update with invalid status transition"""
        # Mock job in completed state
        mock_job = Mock()
        mock_job.status = "completed"
        mock_job.can_transition_to.return_value = False
        
        update_request = JobUpdateRequest(status="scheduled")
        
        with pytest.raises(ValueError, match="Cannot transition job"):
            self.service.update_job(mock_job, update_request, self.mock_db, 1)
    
    def test_reschedule_job_validation(self):
        """Test job rescheduling validation"""
        # Mock job that cannot be rescheduled
        mock_job = Mock()
        mock_job.status = "completed"
        
        with pytest.raises(ValueError, match="Cannot reschedule job"):
            self.service.reschedule_job(
                job=mock_job,
                new_scheduled_time=datetime.now(timezone.utc) + timedelta(days=1),
                reason="Customer request",
                db=self.mock_db,
                user_id=1
            )


class TestJobsAPI:
    """Test the Jobs API endpoints"""
    
    def test_create_job_direct_success(self, test_client: TestClient, test_db: Session, test_user: User, test_org: Organization):
        """Test direct job creation via API"""
        scheduled_time = datetime.now(timezone.utc) + timedelta(days=2)
        
        request_data = {
            "service_type": "driveway_cleaning",
            "address": "123 Test Street",
            "estimated_cost": 250.00,
            "customer_name": "Test Customer",
            "customer_email": "test@example.com",
            "customer_phone": "+1234567890",
            "scheduled_for": scheduled_time.isoformat(),
            "duration_minutes": 90,
            "service_details": {"surfaces": ["driveway"], "square_feet": 1200},
            "crew": {"lead_tech": "John", "crew_size": 2},
            "crew_notes": "Customer has dogs",
            "internal_notes": "Premium customer",
            "priority": "high"
        }
        
        response = test_client.post(
            "/api/v1/jobs",
            json=request_data,
            headers={"X-Organization-ID": test_org.id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["service_type"] == "driveway_cleaning"
        assert data["customer_name"] == "Test Customer"
        assert data["status"] == "scheduled"
        assert data["priority"] == "high"
        assert "JOB-" in data["job_number"]
    
    def test_create_job_from_quote_success(self, test_client: TestClient, test_db: Session, test_user: User, test_org: Organization):
        """Test job creation from accepted quote"""
        # Create accepted quote
        quote = Quote(
            id=str(uuid.uuid4()),
            organization_id=test_org.id,
            customer_email="quote@example.com",
            customer_name="Quote Customer",
            customer_address="456 Quote St",
            line_items=[{"service": "house_washing", "total": 600.00}],
            subtotal=Decimal("600.00"),
            tax_amount=Decimal("48.00"),
            total=Decimal("648.00"),
            status="accepted",
            created_by_id=test_user.id
        )
        test_db.add(quote)
        test_db.commit()
        
        scheduled_time = datetime.now(timezone.utc) + timedelta(days=3)
        
        request_data = {
            "quote_id": quote.id,
            "scheduled_for": scheduled_time.isoformat(),
            "duration_minutes": 240,
            "crew": {"lead_tech": "Sarah", "crew_size": 3},
            "crew_notes": "Bring ladder"
        }
        
        response = test_client.post(
            "/api/v1/jobs/from-quote",
            json=request_data,
            headers={"X-Organization-ID": test_org.id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["quote_id"] == quote.id
        assert data["customer_name"] == "Quote Customer"
        assert data["estimated_cost"] == 648.00
        assert data["crew"]["lead_tech"] == "Sarah"
    
    def test_create_job_from_unaccepted_quote_fails(self, test_client: TestClient, test_db: Session, test_user: User, test_org: Organization):
        """Test that job creation fails for non-accepted quotes"""
        # Create draft quote
        quote = Quote(
            id=str(uuid.uuid4()),
            organization_id=test_org.id,
            customer_email="draft@example.com",
            subtotal=Decimal("300.00"),
            tax_amount=Decimal("24.00"),
            total=Decimal("324.00"),
            status="draft",  # Not accepted
            created_by_id=test_user.id
        )
        test_db.add(quote)
        test_db.commit()
        
        request_data = {
            "quote_id": quote.id,
            "scheduled_for": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        }
        
        response = test_client.post(
            "/api/v1/jobs/from-quote",
            json=request_data,
            headers={"X-Organization-ID": test_org.id}
        )
        
        assert response.status_code == 400
        assert "Quote must be accepted" in response.json()["detail"]
    
    def test_get_job_success(self, test_client: TestClient, test_db: Session, test_user: User, test_org: Organization):
        """Test job retrieval by ID"""
        # Create job
        job = Job(
            id=str(uuid.uuid4()),
            organization_id=test_org.id,
            service_type="patio_cleaning",
            address="789 Patio Lane",
            estimated_cost=Decimal("175.00"),
            customer_name="Patio Owner",
            status="in_progress",
            created_by_id=test_user.id
        )
        test_db.add(job)
        test_db.commit()
        
        response = test_client.get(
            f"/api/v1/jobs/{job.id}",
            headers={"X-Organization-ID": test_org.id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == job.id
        assert data["service_type"] == "patio_cleaning"
        assert data["status"] == "in_progress"
    
    def test_get_job_wrong_org_fails(self, test_client: TestClient, test_db: Session, test_user: User, test_org: Organization):
        """Test job retrieval fails for wrong organization"""
        # Create job for different org
        other_org_id = "other-org-456"
        job = Job(
            id=str(uuid.uuid4()),
            organization_id=other_org_id,
            service_type="deck_cleaning",
            address="999 Other St",
            estimated_cost=Decimal("200.00"),
            created_by_id=test_user.id
        )
        test_db.add(job)
        test_db.commit()
        
        response = test_client.get(
            f"/api/v1/jobs/{job.id}",
            headers={"X-Organization-ID": test_org.id}  # Wrong org
        )
        
        assert response.status_code == 404
        assert "not found or access denied" in response.json()["detail"]
    
    def test_update_job_status_success(self, test_client: TestClient, test_db: Session, test_user: User, test_org: Organization):
        """Test job status update"""
        # Create scheduled job
        job = Job(
            id=str(uuid.uuid4()),
            organization_id=test_org.id,
            service_type="fence_cleaning",
            address="321 Fence Row",
            estimated_cost=Decimal("125.00"),
            status="scheduled",
            created_by_id=test_user.id
        )
        test_db.add(job)
        test_db.commit()
        
        # Update to in_progress
        update_data = {
            "status": "in_progress",
            "completion_notes": "Job started on time",
            "actual_cost": 130.00
        }
        
        response = test_client.patch(
            f"/api/v1/jobs/{job.id}",
            json=update_data,
            headers={"X-Organization-ID": test_org.id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"
        assert data["completion_notes"] == "Job started on time"
        assert data["actual_cost"] == 130.00
        assert data["started_at"] is not None
    
    def test_update_job_invalid_status_transition_fails(self, test_client: TestClient, test_db: Session, test_user: User, test_org: Organization):
        """Test invalid status transition fails"""
        # Create completed job
        job = Job(
            id=str(uuid.uuid4()),
            organization_id=test_org.id,
            service_type="walkway_cleaning",
            address="654 Walk Way",
            estimated_cost=Decimal("85.00"),
            status="completed",  # Terminal state
            created_by_id=test_user.id
        )
        test_db.add(job)
        test_db.commit()
        
        # Try to update to scheduled (invalid)
        update_data = {"status": "scheduled"}
        
        response = test_client.patch(
            f"/api/v1/jobs/{job.id}",
            json=update_data,
            headers={"X-Organization-ID": test_org.id}
        )
        
        assert response.status_code == 400
        assert "Cannot transition job" in response.json()["detail"]
    
    def test_reschedule_job_success(self, test_client: TestClient, test_db: Session, test_user: User, test_org: Organization):
        """Test job rescheduling"""
        # Create scheduled job
        original_time = datetime.now(timezone.utc) + timedelta(days=1)
        job = Job(
            id=str(uuid.uuid4()),
            organization_id=test_org.id,
            service_type="roof_cleaning",
            address="555 Roof Top",
            estimated_cost=Decimal("800.00"),
            scheduled_for=original_time,
            status="scheduled",
            created_by_id=test_user.id
        )
        test_db.add(job)
        test_db.commit()
        
        # Reschedule to new time
        new_time = datetime.now(timezone.utc) + timedelta(days=3)
        reschedule_data = {
            "new_scheduled_time": new_time.isoformat(),
            "reason": "Weather delay"
        }
        
        response = test_client.post(
            f"/api/v1/jobs/{job.id}/reschedule",
            json=reschedule_data,
            headers={"X-Organization-ID": test_org.id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["scheduled_for"] == new_time.isoformat()
        assert data["status"] == "rescheduled"
        assert "Weather delay" in data["internal_notes"]
    
    def test_list_jobs_with_filters(self, test_client: TestClient, test_db: Session, test_user: User, test_org: Organization):
        """Test job listing with various filters"""
        # Create multiple jobs
        jobs = []
        for i in range(3):
            job = Job(
                id=str(uuid.uuid4()),
                organization_id=test_org.id,
                service_type=f"service_{i}",
                address=f"{i} Test St",
                estimated_cost=Decimal(f"{100 + i * 50}.00"),
                status="scheduled" if i % 2 == 0 else "completed",
                priority="high" if i == 0 else "normal",
                customer_email=f"customer{i}@example.com",
                created_by_id=test_user.id
            )
            jobs.append(job)
            test_db.add(job)
        test_db.commit()
        
        # Test status filter
        response = test_client.get(
            "/api/v1/jobs?status=scheduled",
            headers={"X-Organization-ID": test_org.id}
        )
        
        assert response.status_code == 200
        data = response.json()
        scheduled_jobs = [job for job in data["jobs"] if job["status"] == "scheduled"]
        assert len(scheduled_jobs) >= 2  # Jobs 0 and 2
        
        # Test priority filter
        response = test_client.get(
            "/api/v1/jobs?priority=high",
            headers={"X-Organization-ID": test_org.id}
        )
        
        assert response.status_code == 200
        data = response.json()
        high_priority_jobs = [job for job in data["jobs"] if job["priority"] == "high"]
        assert len(high_priority_jobs) >= 1  # Job 0
    
    def test_get_job_stats(self, test_client: TestClient, test_db: Session, test_user: User, test_org: Organization):
        """Test job statistics dashboard"""
        # Create jobs with different statuses
        statuses = ["scheduled", "in_progress", "completed", "canceled"]
        for i, status in enumerate(statuses):
            job = Job(
                id=str(uuid.uuid4()),
                organization_id=test_org.id,
                service_type="test_service",
                address=f"{i} Stats St",
                estimated_cost=Decimal("100.00"),
                actual_cost=Decimal("110.00") if status == "completed" else None,
                status=status,
                created_by_id=test_user.id
            )
            test_db.add(job)
        test_db.commit()
        
        response = test_client.get(
            "/api/v1/jobs/stats/dashboard",
            headers={"X-Organization-ID": test_org.id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["organization_id"] == test_org.id
        assert data["total_jobs"] >= 4
        assert data["scheduled_jobs"] >= 1
        assert data["in_progress_jobs"] >= 1
        assert data["completed_jobs"] >= 1
        assert "completion_rate" in data
        assert "total_estimated_revenue" in data


class TestJobIntegrationFlow:
    """Integration tests for complete job lifecycle"""
    
    def test_complete_job_lifecycle(self, test_db: Session, test_user: User, test_org: Organization):
        """Test complete job lifecycle from quote to completion"""
        # 1. Create accepted quote
        quote = Quote(
            id=str(uuid.uuid4()),
            organization_id=test_org.id,
            customer_email="lifecycle@example.com",
            customer_name="Lifecycle Customer",
            customer_address="123 Lifecycle St",
            line_items=[{"service": "complete_wash", "total": 500.00}],
            subtotal=Decimal("500.00"),
            tax_amount=Decimal("40.00"),
            total=Decimal("540.00"),
            status="accepted",
            created_by_id=test_user.id
        )
        test_db.add(quote)
        test_db.commit()
        
        # 2. Create job from quote
        job_service = JobService()
        scheduled_time = datetime.now(timezone.utc) + timedelta(days=1)
        
        job = job_service.create_job_from_quote(
            quote=quote,
            scheduled_for=scheduled_time,
            duration_minutes=240,
            db=test_db,
            user_id=test_user.id,
            crew={"lead_tech": "Bob", "crew_size": 2}
        )
        
        assert job.status == "scheduled"
        assert job.quote_id == quote.id
        assert job.estimated_cost == Decimal("540.00")
        
        # 3. Start job (scheduled -> in_progress)
        update_request = JobUpdateRequest(status="in_progress")
        updated_job = job_service.update_job(job, update_request, test_db, test_user.id)
        
        assert updated_job.status == "in_progress"
        assert updated_job.started_at is not None
        
        # 4. Complete job with photos and satisfaction rating
        completion_update = JobUpdateRequest(
            status="completed",
            completion_notes="Job completed successfully",
            completion_photos=["photo1.jpg", "photo2.jpg"],
            customer_satisfaction=5,
            actual_cost=550.00
        )
        
        completed_job = job_service.update_job(updated_job, completion_update, test_db, test_user.id)
        
        assert completed_job.status == "completed"
        assert completed_job.completed_at is not None
        assert completed_job.customer_satisfaction == 5
        assert completed_job.actual_cost == Decimal("550.00")
        assert len(completed_job.completion_photos) == 2
        
        # 5. Verify final state
        assert completed_job.can_transition_to("scheduled") is False  # Terminal state
        assert completed_job.is_overdue() is False  # Completed jobs are not overdue


# Test fixtures

@pytest.fixture
def test_quote(test_db: Session, test_user: User, test_org: Organization) -> Quote:
    """Create a test quote"""
    quote = Quote(
        id=str(uuid.uuid4()),
        organization_id=test_org.id,
        customer_email="testquote@example.com",
        customer_name="Test Quote Customer",
        line_items=[{"service": "test_service", "total": 200.00}],
        subtotal=Decimal("200.00"),
        tax_amount=Decimal("16.00"),
        total=Decimal("216.00"),
        status="accepted",
        created_by_id=test_user.id
    )
    test_db.add(quote)
    test_db.commit()
    return quote


@pytest.fixture
def test_job(test_db: Session, test_user: User, test_org: Organization) -> Job:
    """Create a test job"""
    job = Job(
        id=str(uuid.uuid4()),
        organization_id=test_org.id,
        service_type="test_cleaning",
        address="123 Test Address",
        estimated_cost=Decimal("300.00"),
        customer_name="Test Job Customer",
        customer_email="testjob@example.com",
        status="scheduled",
        created_by_id=test_user.id
    )
    test_db.add(job)
    test_db.commit()
    return job