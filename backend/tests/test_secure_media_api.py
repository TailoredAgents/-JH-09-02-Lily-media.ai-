"""
Tests for PW-SEC-ADD-001: Secure Media Storage API

Comprehensive test coverage for security, TTL enforcement, authorization,
and audit logging of the secure media storage system.
"""

import pytest
import uuid
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.db.models import (
    User, Organization, UserOrganizationRole, MediaAsset, Lead
)
from backend.main_minimal import app


class TestMediaStorageService:
    """Test the MediaStorageService for security and functionality"""
    
    def test_generate_upload_url_validates_mime_type(self):
        """Test that upload URL generation validates MIME types"""
        from backend.services.media_storage_service import MediaStorageService
        
        with patch('boto3.client'):
            service = MediaStorageService()
            
            # Test valid MIME type
            with patch.object(service.s3_client, 'generate_presigned_url', return_value="http://signed-url"):
                asset_id, url = service.generate_upload_url(
                    organization_id="org-123",
                    filename="test.jpg",
                    mime_type="image/jpeg",
                    file_size=1024
                )
                assert asset_id is not None
                assert "http://signed-url" in url
            
            # Test invalid MIME type
            with pytest.raises(ValueError, match="MIME type.*not allowed"):
                service.generate_upload_url(
                    organization_id="org-123",
                    filename="test.exe",
                    mime_type="application/x-executable",
                    file_size=1024
                )
    
    def test_generate_upload_url_validates_file_size(self):
        """Test that upload URL generation validates file sizes"""
        from backend.services.media_storage_service import MediaStorageService
        
        with patch('boto3.client'):
            service = MediaStorageService()
            
            # Test file too large
            with pytest.raises(ValueError, match="exceeds maximum"):
                service.generate_upload_url(
                    organization_id="org-123",
                    filename="test.jpg",
                    mime_type="image/jpeg",
                    file_size=100 * 1024 * 1024  # 100MB
                )
            
            # Test zero size
            with pytest.raises(ValueError, match="must be positive"):
                service.generate_upload_url(
                    organization_id="org-123",
                    filename="test.jpg",
                    mime_type="image/jpeg",
                    file_size=0
                )
    
    def test_generate_upload_url_enforces_ttl_limits(self):
        """Test that TTL limits are enforced for upload URLs"""
        from backend.services.media_storage_service import MediaStorageService
        
        with patch('boto3.client'):
            service = MediaStorageService()
            
            # Test TTL too long
            with pytest.raises(ValueError, match="TTL must be between"):
                service.generate_upload_url(
                    organization_id="org-123",
                    filename="test.jpg",
                    mime_type="image/jpeg",
                    file_size=1024,
                    ttl_minutes=15  # Exceeds 10-minute limit
                )
            
            # Test zero TTL
            with pytest.raises(ValueError, match="TTL must be between"):
                service.generate_upload_url(
                    organization_id="org-123",
                    filename="test.jpg",
                    mime_type="image/jpeg",
                    file_size=1024,
                    ttl_minutes=0
                )
    
    def test_generate_download_url_enforces_ttl_limits(self):
        """Test that TTL limits are enforced for download URLs"""
        from backend.services.media_storage_service import MediaStorageService
        
        with patch('boto3.client'):
            service = MediaStorageService()
            
            # Test TTL too long
            with pytest.raises(ValueError, match="cannot exceed"):
                service.generate_download_url(
                    asset_id="asset-123",
                    organization_id="org-123",
                    ttl_minutes=10  # Exceeds 5-minute limit
                )
    
    def test_audit_logging_for_operations(self):
        """Test that all operations generate proper audit logs"""
        from backend.services.media_storage_service import MediaStorageService
        
        with patch('boto3.client'):
            with patch('backend.core.audit_logger.get_audit_logger') as mock_audit:
                mock_logger = Mock()
                mock_audit.return_value = mock_logger
                
                service = MediaStorageService()
                
                with patch.object(service.s3_client, 'generate_presigned_url', return_value="http://test-url"):
                    # Test upload URL generation
                    service.generate_upload_url(
                        organization_id="org-123",
                        filename="test.jpg",
                        mime_type="image/jpeg",
                        file_size=1024
                    )
                    
                    # Verify audit log was called
                    mock_logger.log_event.assert_called()
                    call_args = mock_logger.log_event.call_args
                    assert "media_upload_url_generated" in str(call_args)


class TestSecureMediaAPI:
    """Test the secure media API endpoints"""
    
    @pytest.fixture
    def setup_test_data(self, db_session: Session):
        """Create test data for multi-tenant media testing"""
        # Create organizations
        org1 = Organization(
            id=str(uuid.uuid4()),
            name="Test Org 1",
            slug="test-org-1",
            owner_id=1
        )
        org2 = Organization(
            id=str(uuid.uuid4()),
            name="Test Org 2",
            slug="test-org-2",
            owner_id=2
        )
        
        # Create users
        user1 = User(id=1, email="user1@test.com", username="user1")
        user2 = User(id=2, email="user2@test.com", username="user2")
        
        # Create user-org relationships
        role1 = UserOrganizationRole(
            user_id=1, organization_id=org1.id, role_id="admin", is_active=True
        )
        role2 = UserOrganizationRole(
            user_id=2, organization_id=org2.id, role_id="admin", is_active=True
        )
        
        # Create leads
        lead1 = Lead(
            id=str(uuid.uuid4()),
            organization_id=org1.id,
            source_platform="facebook",
            contact_name="John Doe",
            pricing_intent="quote_request",
            status="new",
            created_by_id=1
        )
        
        db_session.add_all([org1, org2, user1, user2, role1, role2, lead1])
        db_session.commit()
        
        return {
            "org1": org1, "org2": org2,
            "user1": user1, "user2": user2,
            "lead1": lead1
        }
    
    def test_create_upload_url_requires_auth(self, client: TestClient):
        """Test that upload URL creation requires authentication"""
        response = client.post(
            "/api/v1/media/uploads",
            json={
                "filename": "test.jpg",
                "mime_type": "image/jpeg",
                "file_size": 1024
            }
        )
        assert response.status_code == 401
    
    def test_create_upload_url_requires_org_context(self, client: TestClient):
        """Test that upload URL creation requires organization context"""
        with patch('backend.auth.dependencies.get_current_active_user') as mock_auth:
            mock_user = Mock()
            mock_user.id = 1
            mock_auth.return_value = mock_user
            
            response = client.post(
                "/api/v1/media/uploads",
                json={
                    "filename": "test.jpg",
                    "mime_type": "image/jpeg",
                    "file_size": 1024
                }
            )
            assert response.status_code == 400
            assert "Missing X-Organization-ID header" in response.json()["detail"]
    
    def test_create_upload_url_validates_input(self, client: TestClient, setup_test_data):
        """Test input validation for upload URL creation"""
        data = setup_test_data
        
        with patch('backend.auth.dependencies.get_current_active_user') as mock_auth:
            mock_user = Mock()
            mock_user.id = 1
            mock_auth.return_value = mock_user
            
            # Test invalid MIME type
            response = client.post(
                "/api/v1/media/uploads",
                json={
                    "filename": "test.exe",
                    "mime_type": "application/x-executable",
                    "file_size": 1024
                },
                headers={"X-Organization-ID": str(data["org1"].id)}
            )
            assert response.status_code == 422
            assert "not allowed" in response.json()["detail"][0]["msg"]
            
            # Test file too large
            response = client.post(
                "/api/v1/media/uploads",
                json={
                    "filename": "test.jpg",
                    "mime_type": "image/jpeg",
                    "file_size": 100 * 1024 * 1024  # 100MB
                },
                headers={"X-Organization-ID": str(data["org1"].id)}
            )
            assert response.status_code == 422
            assert "ensure this value is less than" in response.json()["detail"][0]["msg"]
    
    def test_create_upload_url_validates_lead_ownership(self, client: TestClient, setup_test_data):
        """Test that lead ownership is validated when associating with asset"""
        data = setup_test_data
        
        with patch('backend.auth.dependencies.get_current_active_user') as mock_auth:
            with patch('backend.services.media_storage_service.get_media_storage_service') as mock_storage:
                mock_user = Mock()
                mock_user.id = 2  # User from org2
                mock_auth.return_value = mock_user
                
                # Try to associate with lead from org1
                response = client.post(
                    "/api/v1/media/uploads",
                    json={
                        "filename": "test.jpg",
                        "mime_type": "image/jpeg",
                        "file_size": 1024,
                        "lead_id": data["lead1"].id
                    },
                    headers={"X-Organization-ID": str(data["org2"].id)}
                )
                assert response.status_code == 404
                assert "Lead not found or access denied" in response.json()["detail"]
    
    def test_create_upload_url_success(self, client: TestClient, setup_test_data):
        """Test successful upload URL creation"""
        data = setup_test_data
        
        with patch('backend.auth.dependencies.get_current_active_user') as mock_auth:
            with patch('backend.services.media_storage_service.get_media_storage_service') as mock_storage:
                mock_user = Mock()
                mock_user.id = 1
                mock_auth.return_value = mock_user
                
                mock_service = Mock()
                mock_service.generate_upload_url.return_value = ("asset-123", "http://signed-upload-url")
                mock_storage.return_value = mock_service
                
                response = client.post(
                    "/api/v1/media/uploads",
                    json={
                        "filename": "test.jpg",
                        "mime_type": "image/jpeg",
                        "file_size": 1024,
                        "lead_id": data["lead1"].id,
                        "tags": ["quote", "photo"],
                        "metadata": {"width": 800, "height": 600}
                    },
                    headers={"X-Organization-ID": str(data["org1"].id)}
                )
                
                assert response.status_code == 200
                response_data = response.json()
                assert "asset_id" in response_data
                assert response_data["upload_url"] == "http://signed-upload-url"
                assert "expires_at" in response_data
                assert response_data["max_file_size"] == 50 * 1024 * 1024
    
    def test_get_download_url_org_isolation(self, client: TestClient, setup_test_data):
        """Test that download URLs enforce organization isolation"""
        data = setup_test_data
        
        # Create asset in org1
        asset = MediaAsset(
            id="asset-123",
            organization_id=data["org1"].id,
            storage_key="test/key",
            filename="test.jpg",
            mime_type="image/jpeg",
            file_size=1024,
            sha256_hash="abcd1234",
            status="active",
            upload_completed=True,
            created_by_id=1
        )
        db_session = next(iter([data]))  # Get session from fixture
        db_session.add(asset)
        db_session.commit()
        
        with patch('backend.auth.dependencies.get_current_active_user') as mock_auth:
            mock_user = Mock()
            mock_user.id = 2  # User from org2
            mock_auth.return_value = mock_user
            
            # Try to access asset from different org
            response = client.get(
                "/api/v1/media/asset-123",
                headers={"X-Organization-ID": str(data["org2"].id)}
            )
            assert response.status_code == 404
            assert "not found or access denied" in response.json()["detail"]
    
    def test_get_download_url_checks_upload_completion(self, client: TestClient, setup_test_data):
        """Test that download URLs require completed upload"""
        data = setup_test_data
        
        # Create incomplete asset
        asset = MediaAsset(
            id="asset-456",
            organization_id=data["org1"].id,
            storage_key="test/key",
            filename="test.jpg",
            mime_type="image/jpeg",
            file_size=1024,
            sha256_hash="",
            status="pending",
            upload_completed=False,
            created_by_id=1
        )
        db_session = next(iter([data]))
        db_session.add(asset)
        db_session.commit()
        
        with patch('backend.auth.dependencies.get_current_active_user') as mock_auth:
            mock_user = Mock()
            mock_user.id = 1
            mock_auth.return_value = mock_user
            
            response = client.get(
                "/api/v1/media/asset-456",
                headers={"X-Organization-ID": str(data["org1"].id)}
            )
            assert response.status_code == 409
            assert "upload not completed" in response.json()["detail"]
    
    def test_get_download_url_success_with_audit(self, client: TestClient, setup_test_data):
        """Test successful download URL generation with audit logging"""
        data = setup_test_data
        
        # Create completed asset
        asset = MediaAsset(
            id="asset-789",
            organization_id=data["org1"].id,
            storage_key="test/key",
            filename="test.jpg",
            mime_type="image/jpeg",
            file_size=1024,
            sha256_hash="abcd1234",
            status="active",
            upload_completed=True,
            access_count=0,
            created_by_id=1
        )
        db_session = next(iter([data]))
        db_session.add(asset)
        db_session.commit()
        
        with patch('backend.auth.dependencies.get_current_active_user') as mock_auth:
            with patch('backend.services.media_storage_service.get_media_storage_service') as mock_storage:
                mock_user = Mock()
                mock_user.id = 1
                mock_auth.return_value = mock_user
                
                mock_service = Mock()
                mock_service.generate_download_url.return_value = "http://signed-download-url"
                mock_storage.return_value = mock_service
                
                response = client.get(
                    "/api/v1/media/asset-789",
                    headers={"X-Organization-ID": str(data["org1"].id)}
                )
                
                assert response.status_code == 200
                response_data = response.json()
                assert response_data["download_url"] == "http://signed-download-url"
                assert response_data["filename"] == "test.jpg"
                assert "expires_at" in response_data
                
                # Verify access count was incremented
                db_session.refresh(asset)
                assert asset.access_count == 1
                assert asset.last_accessed_at is not None
    
    def test_revoke_asset_requires_member_role(self, client: TestClient, setup_test_data):
        """Test that asset revocation requires member role"""
        data = setup_test_data
        
        # Create viewer user (lower than member)
        viewer_user = User(id=3, email="viewer@test.com", username="viewer")
        viewer_role = UserOrganizationRole(
            user_id=3, organization_id=data["org1"].id, role_id="viewer", is_active=True
        )
        db_session = next(iter([data]))
        db_session.add_all([viewer_user, viewer_role])
        db_session.commit()
        
        with patch('backend.auth.dependencies.get_current_active_user') as mock_auth:
            mock_user = Mock()
            mock_user.id = 3
            mock_auth.return_value = mock_user
            
            response = client.delete(
                "/api/v1/media/asset-123",
                headers={"X-Organization-ID": str(data["org1"].id)}
            )
            assert response.status_code == 403
            assert "Required role: member" in response.json()["detail"]
    
    def test_revoke_asset_success(self, client: TestClient, setup_test_data):
        """Test successful asset revocation"""
        data = setup_test_data
        
        # Create asset
        asset = MediaAsset(
            id="asset-revoke",
            organization_id=data["org1"].id,
            storage_key="test/key",
            filename="test.jpg",
            mime_type="image/jpeg",
            file_size=1024,
            sha256_hash="abcd1234",
            status="active",
            upload_completed=True,
            created_by_id=1
        )
        db_session = next(iter([data]))
        db_session.add(asset)
        db_session.commit()
        
        with patch('backend.auth.dependencies.get_current_active_user') as mock_auth:
            with patch('backend.services.media_storage_service.get_media_storage_service') as mock_storage:
                mock_user = Mock()
                mock_user.id = 1
                mock_auth.return_value = mock_user
                
                mock_service = Mock()
                mock_service.revoke_asset.return_value = True
                mock_storage.return_value = mock_service
                
                response = client.delete(
                    "/api/v1/media/asset-revoke",
                    headers={"X-Organization-ID": str(data["org1"].id)}
                )
                
                assert response.status_code == 200
                assert "revoked successfully" in response.json()["message"]
                
                # Verify asset is marked as deleted
                db_session.refresh(asset)
                assert asset.status == "deleted"
    
    def test_list_assets_org_scoped(self, client: TestClient, setup_test_data):
        """Test that asset listing is organization-scoped"""
        data = setup_test_data
        
        # Create assets in both orgs
        asset1 = MediaAsset(
            id="asset-org1",
            organization_id=data["org1"].id,
            storage_key="test/key1",
            filename="test1.jpg",
            mime_type="image/jpeg",
            file_size=1024,
            sha256_hash="hash1",
            status="active",
            upload_completed=True,
            created_by_id=1
        )
        asset2 = MediaAsset(
            id="asset-org2",
            organization_id=data["org2"].id,
            storage_key="test/key2",
            filename="test2.jpg",
            mime_type="image/jpeg",
            file_size=2048,
            sha256_hash="hash2",
            status="active",
            upload_completed=True,
            created_by_id=2
        )
        
        db_session = next(iter([data]))
        db_session.add_all([asset1, asset2])
        db_session.commit()
        
        with patch('backend.auth.dependencies.get_current_active_user') as mock_auth:
            mock_user = Mock()
            mock_user.id = 1
            mock_auth.return_value = mock_user
            
            response = client.get(
                "/api/v1/media",
                headers={"X-Organization-ID": str(data["org1"].id)}
            )
            
            assert response.status_code == 200
            response_data = response.json()
            assert len(response_data["assets"]) == 1
            assert response_data["assets"][0]["id"] == "asset-org1"
            assert response_data["total_count"] == 1
    
    def test_complete_upload_validates_ownership(self, client: TestClient, setup_test_data):
        """Test that upload completion validates asset ownership"""
        data = setup_test_data
        
        # Create pending asset in org1
        asset = MediaAsset(
            id="asset-pending",
            organization_id=data["org1"].id,
            storage_key="test/key",
            filename="test.jpg",
            mime_type="image/jpeg",
            file_size=1024,
            sha256_hash="",
            status="pending",
            upload_completed=False,
            created_by_id=1
        )
        db_session = next(iter([data]))
        db_session.add(asset)
        db_session.commit()
        
        with patch('backend.auth.dependencies.get_current_active_user') as mock_auth:
            mock_user = Mock()
            mock_user.id = 2  # User from org2
            mock_auth.return_value = mock_user
            
            response = client.post(
                "/api/v1/media/asset-pending/complete-upload?sha256_hash=abcd1234",
                headers={"X-Organization-ID": str(data["org2"].id)}
            )
            assert response.status_code == 404
            assert "not found" in response.json()["detail"]


class TestMediaAssetModel:
    """Test the MediaAsset ORM model"""
    
    def test_asset_expiration_check(self):
        """Test asset expiration logic"""
        # Create non-expiring asset
        asset = MediaAsset(
            id="test-asset",
            organization_id="org-123",
            storage_key="test/key",
            filename="test.jpg",
            mime_type="image/jpeg",
            file_size=1024,
            sha256_hash="hash",
            status="active",
            created_by_id=1
        )
        assert not asset.is_expired()
        
        # Create expired asset
        asset.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        assert asset.is_expired()
        
        # Create future expiring asset
        asset.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        assert not asset.is_expired()
    
    def test_access_control(self):
        """Test access control logic"""
        asset = MediaAsset(
            id="test-asset",
            organization_id="org-123",
            storage_key="test/key",
            filename="test.jpg",
            mime_type="image/jpeg",
            file_size=1024,
            sha256_hash="hash",
            status="active",
            created_by_id=1
        )
        
        # Test correct org access
        assert asset.can_access("org-123")
        
        # Test wrong org access
        assert not asset.can_access("org-456")
        
        # Test deleted asset
        asset.status = "deleted"
        assert not asset.can_access("org-123")
        
        # Test expired asset
        asset.status = "active"
        asset.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        assert not asset.can_access("org-123")
    
    def test_to_dict_redacts_sensitive_data(self):
        """Test that to_dict() method properly redacts sensitive information"""
        asset = MediaAsset(
            id="test-asset",
            organization_id="org-123",
            storage_key="sensitive/storage/key",
            filename="test.jpg",
            mime_type="image/jpeg",
            file_size=1024,
            sha256_hash="hash",
            status="active",
            created_by_id=1
        )
        
        data = asset.to_dict()
        
        # Should include basic info
        assert data["id"] == "test-asset"
        assert data["filename"] == "test.jpg"
        assert data["file_size"] == 1024
        
        # Should not include sensitive storage key
        assert "storage_key" not in data
        assert "encryption_key" not in data


if __name__ == "__main__":
    pytest.main([__file__])