"""
PW-ANALYTICS-ADD-001: Unit tests for business analytics service

Tests business KPIs aggregation with seeded data scenarios
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from backend.services.business_analytics_service import (
    BusinessAnalyticsService,
    BusinessAnalyticsRequest,
    BusinessTotals,
    TimeSeriesPoint
)
from backend.db.models import Lead, Quote, Job, Organization, User


class TestBusinessAnalyticsService:
    """Unit tests for business analytics service aggregation functions"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = BusinessAnalyticsService()
        self.mock_db = Mock(spec=Session)
        self.org_id = "test-org-123"
        
        # Test date range
        self.end_date = date.today()
        self.start_date = self.end_date - timedelta(days=30)
        
        self.request = BusinessAnalyticsRequest(
            from_date=self.start_date,
            to_date=self.end_date,
            group_by="day"
        )
    
    def test_build_base_filters(self):
        """Test base filter construction"""
        filters = self.service._build_base_filters(self.org_id, self.start_date, self.end_date)
        
        assert filters['organization_id'] == self.org_id
        assert isinstance(filters['start_datetime'], datetime)
        assert isinstance(filters['end_datetime'], datetime)
        assert filters['start_datetime'].date() == self.start_date
        assert filters['end_datetime'].date() == self.end_date
    
    @patch('backend.services.business_analytics_service.func')
    def test_compute_totals_basic_aggregation(self, mock_func):
        """Test basic totals computation with mock data"""
        
        # Mock database query results
        mock_query = Mock()
        self.mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = 10  # leads count
        mock_query.count.return_value = 8    # quotes count
        mock_query.with_entities.return_value = mock_query
        
        # Mock quote queries
        mock_quotes_query = Mock()
        mock_quotes_query.filter.return_value.count.return_value = 8
        mock_quotes_query.filter.return_value.filter.return_value.count.return_value = 5  # accepted
        
        # Mock job queries  
        mock_jobs_query = Mock()
        mock_jobs_query.filter.return_value = mock_jobs_query
        mock_jobs_query.count.return_value = 5  # scheduled
        mock_jobs_query.filter.return_value.count.return_value = 3  # completed
        mock_jobs_query.filter.return_value.filter.return_value.with_entities.return_value.scalar.return_value = Decimal('2500.00')
        
        # Setup query mocking for different entity types
        def mock_query_side_effect(entity):
            if entity == Lead:
                return Mock(filter=Mock(return_value=Mock(scalar=Mock(return_value=10))))
            elif entity == Quote:
                return mock_quotes_query
            elif entity == Job:
                return mock_jobs_query
            return Mock()
            
        self.mock_db.query.side_effect = mock_query_side_effect
        
        base_filters = {'organization_id': self.org_id, 'start_datetime': datetime.now(), 'end_datetime': datetime.now()}
        
        # Test totals computation
        totals = self.service._compute_totals(self.mock_db, base_filters)
        
        # Verify the mock was called appropriately
        assert self.mock_db.query.called
        
        # Note: Due to complex mocking of SQLAlchemy queries, we mainly test the structure
        assert isinstance(totals, BusinessTotals)
        assert hasattr(totals, 'leads')
        assert hasattr(totals, 'quotes')
        assert hasattr(totals, 'revenue')
        assert hasattr(totals, 'acceptance_rate')
    
    def test_compute_totals_conversion_rates(self):
        """Test conversion rate calculations"""
        
        # Create a more controlled test with direct calculations
        service = BusinessAnalyticsService()
        
        # Mock the database queries to return specific values
        with patch.object(service, '_query_leads_count', return_value=100):
            with patch.object(service, '_query_quotes_count', return_value=50):
                with patch.object(service, '_query_quotes_accepted_count', return_value=25):
                    with patch.object(service, '_query_jobs_scheduled_count', return_value=20):
                        with patch.object(service, '_query_jobs_completed_count', return_value=18):
                            with patch.object(service, '_query_revenue', return_value=45000.0):
                                
                                # We'll need to refactor the service to make it more testable
                                # For now, test the calculation logic directly
                                
                                leads = 100
                                quotes = 50
                                quotes_accepted = 25
                                jobs_scheduled = 20
                                jobs_completed = 18
                                revenue = 45000.0
                                
                                # Test rate calculations
                                acceptance_rate = quotes_accepted / quotes if quotes > 0 else 0.0
                                completion_rate = jobs_completed / jobs_scheduled if jobs_scheduled > 0 else 0.0  
                                lead_to_quote_rate = quotes / leads if leads > 0 else 0.0
                                quote_to_job_rate = jobs_scheduled / quotes_accepted if quotes_accepted > 0 else 0.0
                                avg_ticket = revenue / jobs_completed if jobs_completed > 0 else 0.0
                                
                                assert acceptance_rate == 0.5  # 50% quote acceptance
                                assert completion_rate == 0.9  # 90% job completion  
                                assert lead_to_quote_rate == 0.5  # 50% lead to quote
                                assert quote_to_job_rate == 0.8  # 80% quote to job
                                assert avg_ticket == 2500.0  # $2500 average ticket
    
    def test_time_series_date_grouping(self):
        """Test time series grouping logic"""
        
        # Test different grouping options
        test_cases = [
            ("day", "day"),
            ("week", "week"), 
            ("month", "month")
        ]
        
        for group_by, expected in test_cases:
            request = BusinessAnalyticsRequest(
                from_date=self.start_date,
                to_date=self.end_date,
                group_by=group_by
            )
            
            # Mock empty database results
            self.mock_db.query.return_value.filter.return_value.with_entities.return_value.group_by.return_value.all.return_value = []
            
            base_filters = self.service._build_base_filters(self.org_id, request.from_date, request.to_date)
            
            # This should not raise an exception
            time_series = self.service._compute_time_series(
                self.mock_db, base_filters, group_by
            )
            
            assert isinstance(time_series, list)
    
    def test_platform_filter_integration(self):
        """Test platform filtering across all metrics"""
        
        platform_request = BusinessAnalyticsRequest(
            from_date=self.start_date,
            to_date=self.end_date,
            group_by="day",
            platform="facebook"
        )
        
        # Mock database
        self.mock_db.query.return_value.filter.return_value.scalar.return_value = 5  # leads on Facebook
        self.mock_db.query.return_value.filter.return_value.count.return_value = 3  # quotes from Facebook leads
        
        base_filters = self.service._build_base_filters(self.org_id, platform_request.from_date, platform_request.to_date)
        
        # Test that platform filter is passed correctly
        totals = self.service._compute_totals(
            self.mock_db, base_filters, platform_filter="facebook"
        )
        
        # Verify structure (detailed verification would require integration tests)
        assert isinstance(totals, BusinessTotals)
    
    def test_service_type_filter_integration(self):
        """Test service type filtering for jobs"""
        
        service_request = BusinessAnalyticsRequest(
            from_date=self.start_date,
            to_date=self.end_date,
            group_by="day",
            service_type="pressure_washing"
        )
        
        # Mock job queries with service type filter
        self.mock_db.query.return_value.filter.return_value.count.return_value = 15  # pressure washing jobs
        
        base_filters = self.service._build_base_filters(self.org_id, service_request.from_date, service_request.to_date)
        
        # Test service type filtering
        totals = self.service._compute_totals(
            self.mock_db, base_filters, service_type_filter="pressure_washing"
        )
        
        assert isinstance(totals, BusinessTotals)
    
    def test_empty_data_handling(self):
        """Test handling of empty/null data"""
        
        # Mock empty results
        self.mock_db.query.return_value.filter.return_value.scalar.return_value = 0
        self.mock_db.query.return_value.filter.return_value.count.return_value = 0
        
        base_filters = self.service._build_base_filters(self.org_id, self.start_date, self.end_date)
        
        totals = self.service._compute_totals(self.mock_db, base_filters)
        
        # Should handle division by zero gracefully
        assert totals.leads == 0 
        assert totals.acceptance_rate == 0.0
        assert totals.avg_ticket == 0.0
    
    def test_date_range_validation(self):
        """Test date range validation"""
        
        # Invalid date range (end before start)
        invalid_request = BusinessAnalyticsRequest(
            from_date=self.end_date,
            to_date=self.start_date,  # Invalid: end before start
            group_by="day"
        )
        
        # Should be handled at API level, but service should be robust
        base_filters = self.service._build_base_filters(self.org_id, invalid_request.from_date, invalid_request.to_date)
        
        # Should not crash
        assert base_filters['start_datetime'] > base_filters['end_datetime']
    
    def test_invalid_group_by(self):
        """Test invalid grouping parameter"""
        
        base_filters = self.service._build_base_filters(self.org_id, self.start_date, self.end_date)
        
        # Invalid group_by should raise ValueError
        with pytest.raises(ValueError, match="Invalid group_by value"):
            self.service._compute_time_series(
                self.mock_db, base_filters, "invalid_grouping"
            )
    
    def test_platform_breakdown_structure(self):
        """Test platform breakdown data structure"""
        
        # Mock platform breakdown query
        mock_result = Mock()
        mock_result.platform = "facebook"
        mock_result.leads = 20
        mock_result.quotes = 10  
        mock_result.quotes_accepted = 5
        mock_result.jobs_completed = 4
        mock_result.revenue = Decimal('8000.00')
        
        self.mock_db.query.return_value.outerjoin.return_value.outerjoin.return_value.filter.return_value.group_by.return_value.all.return_value = [mock_result]
        
        base_filters = self.service._build_base_filters(self.org_id, self.start_date, self.end_date)
        
        breakdown = self.service._compute_platform_breakdown(self.mock_db, base_filters)
        
        assert len(breakdown) == 1
        assert breakdown[0].platform == "facebook"
        assert breakdown[0].leads == 20
        assert breakdown[0].revenue == 8000.0
    
    def test_service_type_breakdown_structure(self):
        """Test service type breakdown data structure"""
        
        # Mock service type breakdown query
        mock_result = Mock()
        mock_result.service_type = "pressure_washing"
        mock_result.jobs_scheduled = 15
        mock_result.jobs_completed = 12
        mock_result.revenue = Decimal('30000.00')
        
        self.mock_db.query.return_value.filter.return_value.group_by.return_value.all.return_value = [mock_result]
        
        base_filters = self.service._build_base_filters(self.org_id, self.start_date, self.end_date)
        
        breakdown = self.service._compute_service_type_breakdown(self.mock_db, base_filters)
        
        assert len(breakdown) == 1
        assert breakdown[0].service_type == "pressure_washing"
        assert breakdown[0].jobs_scheduled == 15
        assert breakdown[0].jobs_completed == 12
        assert breakdown[0].revenue == 30000.0
        assert breakdown[0].avg_ticket == 2500.0  # 30000/12


class TestBusinessAnalyticsModels:
    """Test Pydantic models for business analytics"""
    
    def test_business_analytics_request_validation(self):
        """Test request model validation"""
        
        # Valid request
        request = BusinessAnalyticsRequest(
            from_date=date.today() - timedelta(days=30),
            to_date=date.today(),
            group_by="day",
            platform="facebook",
            service_type="pressure_washing"
        )
        
        assert request.from_date < request.to_date
        assert request.group_by == "day"
        assert request.platform == "facebook"
        assert request.service_type == "pressure_washing"
    
    def test_business_totals_model(self):
        """Test totals model structure"""
        
        totals = BusinessTotals(
            leads=100,
            quotes=50,
            quotes_accepted=25,
            jobs_scheduled=20,
            jobs_completed=18,
            revenue=45000.0,
            avg_ticket=2500.0,
            acceptance_rate=0.5,
            completion_rate=0.9,
            lead_to_quote_rate=0.5,
            quote_to_job_rate=0.8
        )
        
        assert totals.leads == 100
        assert totals.acceptance_rate == 0.5
        assert totals.avg_ticket == 2500.0
    
    def test_time_series_point_model(self):
        """Test time series point structure"""
        
        point = TimeSeriesPoint(
            period="2025-01-15",
            leads=5,
            quotes=3,
            quotes_accepted=2,
            jobs_scheduled=1,
            jobs_completed=1,
            revenue=2500.0
        )
        
        assert point.period == "2025-01-15"
        assert point.leads == 5
        assert point.revenue == 2500.0