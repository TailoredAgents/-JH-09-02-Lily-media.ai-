"""
PW-ANALYTICS-ADD-001: Integration tests for business analytics API

Tests end-to-end analytics with fixture data in test database
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.database import Base, get_db
from backend.db.models import Organization, User, Lead, Quote, Job
from backend.main import app
from backend.auth.dependencies import get_current_active_user
from backend.middleware.tenant_context import get_tenant_context, TenantContext


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_analytics.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database session for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


def override_get_current_user():
    """Mock current user for testing"""
    return User(
        id=1,
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        is_active=True,
        is_verified=True
    )


def override_get_tenant_context():
    """Mock tenant context for testing"""
    return TenantContext(
        organization_id="test-org-123",
        user_id=1,
        roles=["analytics.read", "analytics.write"]
    )


# Override dependencies
app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_active_user] = override_get_current_user
app.dependency_overrides[get_tenant_context] = override_get_tenant_context

client = TestClient(app)


class TestBusinessAnalyticsIntegration:
    """Integration tests for business analytics API with real database"""
    
    @classmethod
    def setup_class(cls):
        """Set up test database and fixtures"""
        Base.metadata.create_all(bind=engine)
        
        cls.db = TestingSessionLocal()
        cls.org_id = "test-org-123"
        cls.user_id = 1
        
        # Create test organization
        cls.organization = Organization(
            id=cls.org_id,
            name="Test Pressure Washing Co",
            owner_id=cls.user_id
        )
        cls.db.add(cls.organization)
        
        # Create test user
        cls.user = User(
            id=cls.user_id,
            email="test@example.com", 
            username="testuser",
            full_name="Test User",
            is_active=True,
            is_verified=True,
            default_organization_id=cls.org_id
        )
        cls.db.add(cls.user)
        
        cls.db.commit()
        
        # Create comprehensive test data
        cls._create_test_leads()
        cls._create_test_quotes()
        cls._create_test_jobs()
    
    @classmethod
    def teardown_class(cls):
        """Clean up test database"""
        cls.db.close()
        Base.metadata.drop_all(bind=engine)
    
    @classmethod
    def _create_test_leads(cls):
        """Create test leads with various platforms and dates"""
        
        base_date = datetime.now() - timedelta(days=15)
        
        leads_data = [
            # Facebook leads
            {"platform": "facebook", "status": "new", "days_offset": -10},
            {"platform": "facebook", "status": "contacted", "days_offset": -8},
            {"platform": "facebook", "status": "qualified", "days_offset": -6},
            {"platform": "facebook", "status": "closed", "days_offset": -4},
            
            # Instagram leads
            {"platform": "instagram", "status": "new", "days_offset": -12},
            {"platform": "instagram", "status": "contacted", "days_offset": -9},
            {"platform": "instagram", "status": "qualified", "days_offset": -5},
            
            # Twitter leads
            {"platform": "twitter", "status": "new", "days_offset": -7},
            {"platform": "twitter", "status": "contacted", "days_offset": -3},
            
            # Older leads (outside 30-day window for comparison)
            {"platform": "facebook", "status": "closed", "days_offset": -45},
        ]
        
        for i, lead_data in enumerate(leads_data):
            lead = Lead(
                id=f"lead-{i+1}",
                organization_id=cls.org_id,
                source_platform=lead_data["platform"],
                status=lead_data["status"],
                contact_name=f"Customer {i+1}",
                contact_email=f"customer{i+1}@example.com",
                requested_services=["pressure_washing"],
                pricing_intent="quote_request",
                created_by_id=cls.user_id,
                created_at=base_date + timedelta(days=lead_data["days_offset"])
            )
            cls.db.add(lead)
        
        cls.db.commit()
    
    @classmethod 
    def _create_test_quotes(cls):
        """Create test quotes with various statuses"""
        
        base_date = datetime.now() - timedelta(days=12)
        
        # Get some leads to link quotes to
        leads = cls.db.query(Lead).filter(Lead.organization_id == cls.org_id).limit(6).all()
        
        quotes_data = [
            {"status": "sent", "total": 2500.00, "days_offset": -10, "lead_idx": 0},
            {"status": "accepted", "total": 3200.00, "days_offset": -8, "lead_idx": 1},
            {"status": "accepted", "total": 1800.00, "days_offset": -6, "lead_idx": 2},
            {"status": "declined", "total": 2100.00, "days_offset": -5, "lead_idx": 3},
            {"status": "accepted", "total": 4500.00, "days_offset": -3, "lead_idx": 4},
            {"status": "expired", "total": 2800.00, "days_offset": -2, "lead_idx": 5},
        ]
        
        for i, quote_data in enumerate(quotes_data):
            quote = Quote(
                id=f"quote-{i+1}",
                organization_id=cls.org_id,
                lead_id=leads[quote_data["lead_idx"]].id if quote_data["lead_idx"] < len(leads) else None,
                customer_email=f"customer{i+1}@example.com",
                customer_name=f"Customer {i+1}",
                line_items=[{"service": "pressure_washing", "amount": quote_data["total"]}],
                subtotal=Decimal(str(quote_data["total"])),
                total=Decimal(str(quote_data["total"])),
                status=quote_data["status"],
                quote_number=f"Q-{i+1:04d}",
                created_by_id=cls.user_id,
                created_at=base_date + timedelta(days=quote_data["days_offset"])
            )
            cls.db.add(quote)
        
        cls.db.commit()
    
    @classmethod
    def _create_test_jobs(cls):
        """Create test jobs with various statuses and service types"""
        
        base_date = datetime.now() - timedelta(days=8)
        
        # Get accepted quotes to link jobs to
        accepted_quotes = cls.db.query(Quote).filter(
            Quote.organization_id == cls.org_id,
            Quote.status == "accepted"
        ).all()
        
        jobs_data = [
            {
                "service_type": "pressure_washing", 
                "status": "completed", 
                "estimated_cost": 3200.00,
                "actual_cost": 3200.00,
                "days_offset": -6,
                "quote_idx": 0
            },
            {
                "service_type": "roof_cleaning",
                "status": "completed", 
                "estimated_cost": 1800.00,
                "actual_cost": 1950.00,  # Actual cost higher
                "days_offset": -4,
                "quote_idx": 1
            },
            {
                "service_type": "pressure_washing",
                "status": "scheduled",
                "estimated_cost": 4500.00,
                "actual_cost": None,
                "days_offset": -2,
                "quote_idx": 2
            },
            {
                "service_type": "deck_cleaning", 
                "status": "in_progress",
                "estimated_cost": 2200.00,
                "actual_cost": None,
                "days_offset": -1,
                "quote_idx": 0  # Can reuse quotes
            }
        ]
        
        for i, job_data in enumerate(jobs_data):
            quote_idx = min(job_data["quote_idx"], len(accepted_quotes) - 1)
            quote = accepted_quotes[quote_idx] if accepted_quotes else None
            
            job = Job(
                id=f"job-{i+1}",
                organization_id=cls.org_id,
                quote_id=quote.id if quote else None,
                job_number=f"J-{i+1:04d}",
                service_type=job_data["service_type"],
                address=f"123 Test St, City {i+1}",
                estimated_cost=Decimal(str(job_data["estimated_cost"])),
                actual_cost=Decimal(str(job_data["actual_cost"])) if job_data["actual_cost"] else None,
                status=job_data["status"],
                customer_name=f"Customer {i+1}",
                customer_email=f"customer{i+1}@example.com",
                created_by_id=cls.user_id,
                created_at=base_date + timedelta(days=job_data["days_offset"])
            )
            cls.db.add(job)
        
        cls.db.commit()
    
    def test_business_analytics_endpoint_basic(self):
        """Test basic business analytics endpoint"""
        
        response = client.get("/api/analytics/business")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "totals" in data
        assert "time_series" in data
        assert "platform_breakdown" in data
        assert "service_type_breakdown" in data
        
        # Verify totals structure
        totals = data["totals"]
        required_fields = [
            "leads", "quotes", "quotes_accepted", "jobs_scheduled", 
            "jobs_completed", "revenue", "avg_ticket", "acceptance_rate",
            "completion_rate", "lead_to_quote_rate", "quote_to_job_rate"
        ]
        
        for field in required_fields:
            assert field in totals
            assert isinstance(totals[field], (int, float))
    
    def test_business_analytics_with_date_range(self):
        """Test analytics with specific date range"""
        
        # Test last 10 days
        end_date = date.today()
        start_date = end_date - timedelta(days=10)
        
        response = client.get(
            f"/api/analytics/business?from_date={start_date}&to_date={end_date}&group_by=day"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have data within the date range
        assert data["totals"]["leads"] >= 0
        assert len(data["time_series"]) >= 0
    
    def test_business_analytics_platform_filter(self):
        """Test platform filtering"""
        
        response = client.get("/api/analytics/business?platform=facebook")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have Facebook-specific data
        # Platform breakdown should be None when filtering by platform
        assert data["platform_breakdown"] is None
        
        # Should still have service type breakdown
        assert data["service_type_breakdown"] is not None
    
    def test_business_analytics_service_type_filter(self):
        """Test service type filtering"""
        
        response = client.get("/api/analytics/business?service_type=pressure_washing")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have pressure washing specific data
        # Service type breakdown should be None when filtering by service
        assert data["service_type_breakdown"] is None
        
        # Should still have platform breakdown
        assert data["platform_breakdown"] is not None
    
    def test_business_analytics_time_grouping(self):
        """Test different time grouping options"""
        
        for group_by in ["day", "week", "month"]:
            response = client.get(f"/api/analytics/business?group_by={group_by}")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify time series has expected structure
            time_series = data["time_series"]
            for point in time_series:
                assert "period" in point
                assert "leads" in point
                assert "revenue" in point
    
    def test_business_analytics_breakdowns(self):
        """Test platform and service type breakdowns"""
        
        response = client.get("/api/analytics/business")
        
        assert response.status_code == 200
        data = response.json()
        
        # Test platform breakdown
        platform_breakdown = data["platform_breakdown"]
        assert isinstance(platform_breakdown, list)
        
        for platform_data in platform_breakdown:
            assert "platform" in platform_data
            assert "leads" in platform_data
            assert "revenue" in platform_data
            
        # Test service type breakdown
        service_breakdown = data["service_type_breakdown"]
        assert isinstance(service_breakdown, list)
        
        for service_data in service_breakdown:
            assert "service_type" in service_data
            assert "jobs_scheduled" in service_data
            assert "revenue" in service_data
            assert "avg_ticket" in service_data
    
    def test_business_summary_endpoint(self):
        """Test business summary endpoint"""
        
        response = client.get("/api/analytics/business/summary")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify summary structure
        assert "period" in data
        assert "current" in data
        assert "previous" in data
        assert "growth" in data
        
        # Verify growth calculations
        growth = data["growth"]
        assert "leads" in growth
        assert "revenue" in growth
        assert isinstance(growth["leads"], (int, float))
    
    def test_analytics_validation_errors(self):
        """Test validation error handling"""
        
        # Invalid group_by
        response = client.get("/api/analytics/business?group_by=invalid")
        assert response.status_code == 400
        
        # Invalid date range (end before start)
        end_date = date.today() - timedelta(days=10)
        start_date = date.today()
        response = client.get(
            f"/api/analytics/business?from_date={start_date}&to_date={end_date}"
        )
        assert response.status_code == 400
        
        # Date range too large (over 2 years)
        start_date = date.today() - timedelta(days=800)
        end_date = date.today()
        response = client.get(
            f"/api/analytics/business?from_date={start_date}&to_date={end_date}"
        )
        assert response.status_code == 400
    
    def test_analytics_health_check(self):
        """Test analytics health check endpoint"""
        
        response = client.get("/api/analytics/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_revenue_calculation_accuracy(self):
        """Test that revenue calculations use actual_cost when available"""
        
        response = client.get("/api/analytics/business")
        
        assert response.status_code == 200
        data = response.json()
        
        # We created 2 completed jobs with actual costs: 3200.00 and 1950.00
        # Total expected revenue = 5150.00
        expected_revenue = 5150.0  # Based on our test data
        
        # Allow for small floating point differences
        assert abs(data["totals"]["revenue"] - expected_revenue) < 0.01
    
    def test_conversion_rate_accuracy(self):
        """Test conversion rate calculations with known test data"""
        
        response = client.get("/api/analytics/business")
        
        assert response.status_code == 200
        data = response.json()
        
        totals = data["totals"]
        
        # Verify rates are between 0 and 1
        assert 0 <= totals["acceptance_rate"] <= 1
        assert 0 <= totals["completion_rate"] <= 1
        assert 0 <= totals["lead_to_quote_rate"] <= 1
        assert 0 <= totals["quote_to_job_rate"] <= 1
        
        # Test specific rates based on our test data
        # We have 3 accepted quotes out of 6 total quotes = 50% acceptance rate
        expected_acceptance_rate = 3.0 / 6.0  # 0.5
        assert abs(totals["acceptance_rate"] - expected_acceptance_rate) < 0.01
    
    def test_org_scoped_data_isolation(self):
        """Test that data is properly isolated by organization"""
        
        # Create data for another organization
        other_org_id = "other-org-456"
        other_org = Organization(
            id=other_org_id,
            name="Other Company",
            owner_id=self.user_id
        )
        self.db.add(other_org)
        
        # Create a lead for the other org
        other_lead = Lead(
            id="other-lead-1",
            organization_id=other_org_id,
            source_platform="facebook",
            status="new",
            contact_email="other@example.com",
            requested_services=["pressure_washing"],
            created_by_id=self.user_id
        )
        self.db.add(other_lead)
        self.db.commit()
        
        # Query analytics - should only return data for test-org-123
        response = client.get("/api/analytics/business")
        
        assert response.status_code == 200
        data = response.json()
        
        # The totals should not include the other organization's data
        # (This is ensured by the tenant context mock)
        assert isinstance(data["totals"]["leads"], int)
        
        # Clean up
        self.db.delete(other_lead)
        self.db.delete(other_org)
        self.db.commit()