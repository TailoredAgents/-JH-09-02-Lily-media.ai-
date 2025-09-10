"""
PW-DM-ADD-002: Comprehensive tests for Leads API

Tests the lead media attachment endpoint and full photo capture flow:
- webhook → lead → upload_url → attach → quote recompute
"""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.db.models import Lead, MediaAsset, Quote, User, Organization, SocialInteraction
from backend.api.leads import MediaAttachmentRequest
from backend.services.notification_service import NotificationType


class TestLeadsAPI:
    """Test suite for Leads API endpoints"""
    
    def test_attach_media_to_lead_success(self, test_client: TestClient, test_db: Session, test_user: User, test_org: Organization):
        """Test successful media attachment to lead"""
        # Create test lead
        lead = Lead(
            id=str(uuid.uuid4()),
            organization_id=test_org.id,
            interaction_id=str(uuid.uuid4()),
            source_platform="facebook",
            contact_name="John Doe",
            contact_email="john@example.com",
            requested_services=["pressure_washing"],
            pricing_intent="quote_request",
            extracted_surfaces={"driveway": {"mentioned": True, "area": 1000.0}},
            status="new",
            priority_score=85.0,
            created_by_id=test_user.id
        )
        test_db.add(lead)
        
        # Create test media asset
        media_asset = MediaAsset(
            id=str(uuid.uuid4()),
            organization_id=test_org.id,
            storage_key=f"media-assets/{test_org.id}/{uuid.uuid4()}/test.jpg",
            filename="driveway_photo.jpg",
            mime_type="image/jpeg",
            file_size=1024000,
            sha256_hash="abc123",
            status="active",
            upload_completed=True,
            created_by_id=test_user.id
        )
        test_db.add(media_asset)
        test_db.commit()
        
        # Mock notification service
        with patch('backend.api.leads.get_notification_service') as mock_notification:
            mock_service = AsyncMock()
            mock_notification.return_value = mock_service
            
            # Mock quote service to return new quote
            with patch('backend.api.leads.get_lead_quote_service') as mock_quote_service:
                mock_quote_instance = Mock()
                mock_new_quote = Quote(
                    id=str(uuid.uuid4()),
                    organization_id=test_org.id,
                    lead_id=lead.id,
                    total=500.00,
                    currency="USD"
                )
                mock_quote_instance.try_auto_quote_for_lead.return_value = mock_new_quote
                mock_quote_service.return_value = mock_quote_instance
                
                # Make API request
                response = test_client.post(
                    f"/api/v1/leads/{lead.id}/media/attach",
                    json={
                        "media_asset_id": media_asset.id,
                        "description": "Photo of driveway stains",
                        "tags": ["before", "stains"]
                    },
                    headers={"X-Organization-ID": test_org.id}
                )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["media_asset_id"] == media_asset.id
        assert data["lead_id"] == lead.id
        assert data["quote_generated"] is True
        assert data["quote_total"] == 500.00
        
        # Verify database changes
        test_db.refresh(media_asset)
        assert media_asset.lead_id == lead.id
        assert "before" in media_asset.tags
        assert "stains" in media_asset.tags
        assert media_asset.asset_metadata["lead_description"] == "Photo of driveway stains"
    
    def test_attach_media_lead_not_found(self, test_client: TestClient, test_org: Organization):
        """Test media attachment with non-existent lead"""
        response = test_client.post(
            f"/api/v1/leads/{uuid.uuid4()}/media/attach",
            json={
                "media_asset_id": str(uuid.uuid4())
            },
            headers={"X-Organization-ID": test_org.id}
        )
        
        assert response.status_code == 404
        assert "Lead not found" in response.json()["detail"]
    
    def test_attach_media_asset_not_found(self, test_client: TestClient, test_db: Session, test_user: User, test_org: Organization):
        """Test media attachment with non-existent media asset"""
        # Create test lead
        lead = Lead(
            id=str(uuid.uuid4()),
            organization_id=test_org.id,
            status="new",
            priority_score=50.0,
            created_by_id=test_user.id
        )
        test_db.add(lead)
        test_db.commit()
        
        response = test_client.post(
            f"/api/v1/leads/{lead.id}/media/attach",
            json={
                "media_asset_id": str(uuid.uuid4())
            },
            headers={"X-Organization-ID": test_org.id}
        )
        
        assert response.status_code == 404
        assert "Media asset not found" in response.json()["detail"]
    
    def test_attach_media_already_attached(self, test_client: TestClient, test_db: Session, test_user: User, test_org: Organization):
        """Test attachment of media asset already attached to same lead"""
        # Create test lead
        lead = Lead(
            id=str(uuid.uuid4()),
            organization_id=test_org.id,
            status="new",
            priority_score=50.0,
            created_by_id=test_user.id
        )
        test_db.add(lead)
        
        # Create media asset already attached to this lead
        media_asset = MediaAsset(
            id=str(uuid.uuid4()),
            organization_id=test_org.id,
            lead_id=lead.id,  # Already attached
            storage_key=f"media-assets/{test_org.id}/{uuid.uuid4()}/test.jpg",
            filename="test.jpg",
            mime_type="image/jpeg",
            file_size=1024,
            status="active",
            upload_completed=True,
            created_by_id=test_user.id
        )
        test_db.add(media_asset)
        test_db.commit()
        
        response = test_client.post(
            f"/api/v1/leads/{lead.id}/media/attach",
            json={
                "media_asset_id": media_asset.id
            },
            headers={"X-Organization-ID": test_org.id}
        )
        
        assert response.status_code == 409
        assert "already attached" in response.json()["detail"]
    
    def test_attach_media_upload_not_completed(self, test_client: TestClient, test_db: Session, test_user: User, test_org: Organization):
        """Test attachment of media asset with incomplete upload"""
        # Create test lead
        lead = Lead(
            id=str(uuid.uuid4()),
            organization_id=test_org.id,
            status="new",
            priority_score=50.0,
            created_by_id=test_user.id
        )
        test_db.add(lead)
        
        # Create media asset with incomplete upload
        media_asset = MediaAsset(
            id=str(uuid.uuid4()),
            organization_id=test_org.id,
            storage_key=f"media-assets/{test_org.id}/{uuid.uuid4()}/test.jpg",
            filename="test.jpg",
            mime_type="image/jpeg",
            file_size=1024,
            status="pending",
            upload_completed=False,  # Not completed
            created_by_id=test_user.id
        )
        test_db.add(media_asset)
        test_db.commit()
        
        response = test_client.post(
            f"/api/v1/leads/{lead.id}/media/attach",
            json={
                "media_asset_id": media_asset.id
            },
            headers={"X-Organization-ID": test_org.id}
        )
        
        assert response.status_code == 409
        assert "upload not completed" in response.json()["detail"]
    
    def test_get_lead_success(self, test_client: TestClient, test_db: Session, test_user: User, test_org: Organization):
        """Test successful lead retrieval"""
        # Create test lead
        lead = Lead(
            id=str(uuid.uuid4()),
            organization_id=test_org.id,
            interaction_id=str(uuid.uuid4()),
            source_platform="instagram",
            contact_name="Jane Smith",
            contact_email="jane@example.com",
            contact_phone="+1234567890",
            requested_services=["house_washing", "deck_cleaning"],
            pricing_intent="price_inquiry",
            extracted_surfaces={"house_siding": {"mentioned": True, "area": 2500.0}},
            status="new",
            priority_score=75.0,
            created_by_id=test_user.id
        )
        test_db.add(lead)
        test_db.commit()
        
        response = test_client.get(
            f"/api/v1/leads/{lead.id}",
            headers={"X-Organization-ID": test_org.id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == lead.id
        assert data["contact_name"] == "Jane Smith"
        assert data["source_platform"] == "instagram"
        assert data["pricing_intent"] == "price_inquiry"
        assert "house_washing" in data["requested_services"]
        assert "deck_cleaning" in data["requested_services"]
    
    def test_get_lead_not_found(self, test_client: TestClient, test_org: Organization):
        """Test lead retrieval with non-existent lead"""
        response = test_client.get(
            f"/api/v1/leads/{uuid.uuid4()}",
            headers={"X-Organization-ID": test_org.id}
        )
        
        assert response.status_code == 404
        assert "Lead not found" in response.json()["detail"]
    
    def test_list_leads_success(self, test_client: TestClient, test_db: Session, test_user: User, test_org: Organization):
        """Test successful leads listing"""
        # Create multiple test leads
        leads = []
        for i in range(3):
            lead = Lead(
                id=str(uuid.uuid4()),
                organization_id=test_org.id,
                contact_name=f"Customer {i+1}",
                source_platform="facebook" if i % 2 == 0 else "instagram",
                status="new",
                priority_score=50.0 + i * 10,
                created_by_id=test_user.id
            )
            leads.append(lead)
            test_db.add(lead)
        test_db.commit()
        
        response = test_client.get(
            "/api/v1/leads",
            headers={"X-Organization-ID": test_org.id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "leads" in data
        assert data["total_count"] >= 3
        assert len(data["leads"]) >= 3
        
        # Verify ordering by priority score desc
        lead_scores = [lead["priority_score"] for lead in data["leads"]]
        assert lead_scores == sorted(lead_scores, reverse=True)
    
    def test_list_leads_with_filters(self, test_client: TestClient, test_db: Session, test_user: User, test_org: Organization):
        """Test leads listing with filters"""
        # Create leads with different platforms
        facebook_lead = Lead(
            id=str(uuid.uuid4()),
            organization_id=test_org.id,
            source_platform="facebook",
            status="new",
            priority_score=60.0,
            created_by_id=test_user.id
        )
        instagram_lead = Lead(
            id=str(uuid.uuid4()),
            organization_id=test_org.id,
            source_platform="instagram",
            status="contacted",
            priority_score=70.0,
            created_by_id=test_user.id
        )
        test_db.add_all([facebook_lead, instagram_lead])
        test_db.commit()
        
        # Filter by platform
        response = test_client.get(
            "/api/v1/leads?source_platform=facebook",
            headers={"X-Organization-ID": test_org.id}
        )
        
        assert response.status_code == 200
        data = response.json()
        facebook_leads = [lead for lead in data["leads"] if lead["source_platform"] == "facebook"]
        assert len(facebook_leads) >= 1
        
        # Filter by status
        response = test_client.get(
            "/api/v1/leads?status=contacted",
            headers={"X-Organization-ID": test_org.id}
        )
        
        assert response.status_code == 200
        data = response.json()
        contacted_leads = [lead for lead in data["leads"] if lead["status"] == "contacted"]
        assert len(contacted_leads) >= 1


class TestLeadPhotoCapureFlow:
    """Integration tests for the complete photo capture flow"""
    
    @patch('backend.services.dm_lead_service._send_platform_response')
    @patch('backend.services.media_storage_service.get_media_storage_service')
    async def test_complete_photo_capture_flow(self, mock_storage_service, mock_platform_response, 
                                             test_db: Session, test_user: User, test_org: Organization):
        """
        Test complete flow: webhook → lead → upload_url → attach → quote recompute
        """
        # 1. Create social interaction (simulating webhook)
        interaction = SocialInteraction(
            id=str(uuid.uuid4()),
            connection_id=str(uuid.uuid4()),
            platform="facebook",
            interaction_type="dm",
            external_id="fb_message_123",
            author_platform_id="user123",
            author_username="johndoe",
            author_display_name="John Doe",
            content="Hi! How much to pressure wash my 1500 sq ft driveway? It has some oil stains.",
            platform_created_at=datetime.now(timezone.utc),
            received_at=datetime.now(timezone.utc),
            status="unread",
            sentiment="neutral",
            priority_score=75.0,
            user_id=test_user.id
        )
        test_db.add(interaction)
        test_db.commit()
        
        # 2. Mock storage service for upload URL generation
        mock_storage_instance = Mock()
        mock_storage_instance.generate_upload_url.return_value = (
            "asset_123", 
            "https://s3.amazonaws.com/bucket/signed-upload-url"
        )
        mock_storage_service.return_value = mock_storage_instance
        
        # 3. Create lead from DM (simulating DM lead service)
        from backend.services.dm_lead_service import get_dm_lead_service
        dm_service = get_dm_lead_service()
        
        lead = dm_service.create_lead_from_dm(
            interaction=interaction,
            organization_id=test_org.id,
            db=test_db,
            user_id=test_user.id
        )
        
        # Verify lead creation and photo upload response
        assert lead is not None
        assert lead.pricing_intent == "quote_request"
        assert "driveway" in lead.extracted_surfaces
        assert lead.extracted_surfaces["driveway"]["area"] == 1500.0
        assert lead.priority_score >= 80.0  # High score due to specific request
        
        # Verify upload URL was generated for photo response
        mock_storage_instance.generate_upload_url.assert_called_once()
        
        # Verify platform response was sent
        mock_platform_response.assert_called_once()
        
        # 4. Simulate media asset creation (after customer uploads photo)
        media_asset = MediaAsset(
            id="asset_123",  # Same as returned from upload URL generation
            organization_id=test_org.id,
            lead_id=lead.id,
            storage_key=f"media-assets/{test_org.id}/asset_123/driveway_photo.jpg",
            filename="driveway_photo.jpg",
            mime_type="image/jpeg",
            file_size=2048000,
            sha256_hash="photo_hash_456",
            status="active",
            upload_completed=True,
            created_by_id=test_user.id
        )
        test_db.add(media_asset)
        test_db.commit()
        
        # 5. Test that quote can be generated with photo
        from backend.services.lead_quote_service import get_lead_quote_service
        quote_service = get_lead_quote_service()
        
        # Lead should now be eligible for quote generation
        can_generate = quote_service.can_generate_quote(lead)
        assert can_generate is True
        
        # 6. Verify notification system integration
        with patch('backend.services.notification_service.get_notification_service') as mock_notification:
            mock_service = AsyncMock()
            mock_notification.return_value = mock_service
            
            # Test leads API media attachment
            from fastapi.testclient import TestClient
            from backend.core.app_factory import create_app
            
            app = create_app()
            client = TestClient(app)
            
            response = client.post(
                f"/api/v1/leads/{lead.id}/media/attach",
                json={
                    "media_asset_id": media_asset.id,
                    "description": "Customer photo of driveway with oil stains"
                },
                headers={"X-Organization-ID": test_org.id}
            )
            
            # Should succeed and trigger notification
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            
            # Verify notification was sent
            mock_service.send_lead_media_notification.assert_called_once_with(
                lead_id=lead.id,
                media_asset_id=media_asset.id,
                organization_id=test_org.id,
                user_id=test_user.id
            )


# Test fixtures and utilities

@pytest.fixture
def test_lead(test_db: Session, test_user: User, test_org: Organization) -> Lead:
    """Create a test lead for testing"""
    lead = Lead(
        id=str(uuid.uuid4()),
        organization_id=test_org.id,
        interaction_id=str(uuid.uuid4()),
        source_platform="facebook",
        contact_name="Test Customer",
        pricing_intent="quote_request",
        extracted_surfaces={"driveway": {"mentioned": True, "area": 1000.0}},
        status="new",
        priority_score=75.0,
        created_by_id=test_user.id
    )
    test_db.add(lead)
    test_db.commit()
    return lead


@pytest.fixture
def test_media_asset(test_db: Session, test_user: User, test_org: Organization) -> MediaAsset:
    """Create a test media asset for testing"""
    asset = MediaAsset(
        id=str(uuid.uuid4()),
        organization_id=test_org.id,
        storage_key=f"media-assets/{test_org.id}/{uuid.uuid4()}/test.jpg",
        filename="test_photo.jpg",
        mime_type="image/jpeg",
        file_size=1024000,
        sha256_hash="test_hash",
        status="active",
        upload_completed=True,
        created_by_id=test_user.id
    )
    test_db.add(asset)
    test_db.commit()
    return asset