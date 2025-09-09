"""
Tests for PW-DM-REPLACE-002: Org-scoped social inbox with RBAC

Ensures proper tenant isolation and role-based access control for inbox endpoints.
"""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.db.models import (
    User, Organization, UserOrganizationRole, SocialPlatformConnection,
    SocialInteraction, ResponseTemplate, CompanyKnowledge
)
from backend.main_minimal import app


class TestSocialInboxOrgScoping:
    """Test org-scoped filtering for social inbox endpoints"""
    
    @pytest.fixture
    def setup_multi_tenant_data(self, db_session: Session):
        """Create test data with multiple organizations and users"""
        # Create two organizations
        org1 = Organization(
            id=str(uuid.uuid4()),
            name="Pressure Pro LLC",
            slug="pressure-pro",
            owner_id=1
        )
        org2 = Organization(
            id=str(uuid.uuid4()),
            name="Clean Team Inc",
            slug="clean-team",
            owner_id=2
        )
        
        # Create users
        user1 = User(id=1, email="admin@pressurepro.com", username="admin1")
        user2 = User(id=2, email="admin@cleanteam.com", username="admin2")
        user3 = User(id=3, email="member@pressurepro.com", username="member1")
        
        # Create user-organization relationships
        role1 = UserOrganizationRole(
            user_id=1, organization_id=org1.id, role_id="admin", is_active=True
        )
        role2 = UserOrganizationRole(
            user_id=2, organization_id=org2.id, role_id="admin", is_active=True
        )
        role3 = UserOrganizationRole(
            user_id=3, organization_id=org1.id, role_id="member", is_active=True
        )
        
        # Create social platform connections
        connection1 = SocialPlatformConnection(
            id=1,
            user_id=1,
            organization_id=org1.id,
            platform="facebook",
            platform_user_id="fb_user_1",
            platform_username="pressurepro_fb",
            access_token="encrypted_token_1"
        )
        connection2 = SocialPlatformConnection(
            id=2,
            user_id=2,
            organization_id=org2.id,
            platform="facebook",
            platform_user_id="fb_user_2",
            platform_username="cleanteam_fb",
            access_token="encrypted_token_2"
        )
        
        # Create social interactions
        interaction1 = SocialInteraction(
            id="int_1",
            user_id=1,
            connection_id=1,  # Links to org1
            platform="facebook",
            interaction_type="dm",
            external_id="fb_msg_1",
            author_platform_id="customer_1",
            author_username="customer1",
            content="Need quote for driveway cleaning",
            sentiment="neutral",
            intent="lead",
            priority_score=75.0,
            status="unread",
            received_at=datetime.now(timezone.utc)
        )
        
        interaction2 = SocialInteraction(
            id="int_2",
            user_id=2,
            connection_id=2,  # Links to org2
            platform="facebook",
            interaction_type="dm",
            external_id="fb_msg_2",
            author_platform_id="customer_2",
            author_username="customer2",
            content="What do you charge for house washing?",
            sentiment="neutral",
            intent="lead",
            priority_score=80.0,
            status="unread",
            received_at=datetime.now(timezone.utc)
        )
        
        # Add all to session
        db_session.add_all([
            org1, org2, user1, user2, user3,
            role1, role2, role3,
            connection1, connection2,
            interaction1, interaction2
        ])
        db_session.commit()
        
        return {
            "org1": org1, "org2": org2,
            "user1": user1, "user2": user2, "user3": user3,
            "connection1": connection1, "connection2": connection2,
            "interaction1": interaction1, "interaction2": interaction2
        }
    
    def test_get_interactions_requires_org_context(self, client: TestClient):
        """Test that interactions endpoint requires X-Organization-ID header"""
        with patch('backend.auth.dependencies.get_current_active_user') as mock_auth:
            mock_user = Mock()
            mock_user.id = 1
            mock_auth.return_value = mock_user
            
            # Request without organization header should fail
            response = client.get("/api/inbox/interactions")
            assert response.status_code == 400
            assert "Missing X-Organization-ID header" in response.json()["detail"]
    
    def test_get_interactions_unauthorized_org_access(self, client: TestClient, setup_multi_tenant_data):
        """Test that users cannot access interactions from unauthorized organizations"""
        data = setup_multi_tenant_data
        
        with patch('backend.auth.dependencies.get_current_active_user') as mock_auth:
            mock_user = Mock()
            mock_user.id = 1  # User from org1
            mock_auth.return_value = mock_user
            
            # Try to access org2's interactions
            response = client.get(
                "/api/inbox/interactions",
                headers={"X-Organization-ID": str(data["org2"].id)}
            )
            assert response.status_code == 403
            assert "Access denied" in response.json()["detail"]
    
    def test_get_interactions_org_scoped_filtering(self, client: TestClient, setup_multi_tenant_data):
        """Test that interactions are properly filtered by organization"""
        data = setup_multi_tenant_data
        
        with patch('backend.auth.dependencies.get_current_active_user') as mock_auth:
            mock_user = Mock()
            mock_user.id = 1
            mock_auth.return_value = mock_user
            
            # Access org1's interactions
            response = client.get(
                "/api/inbox/interactions",
                headers={"X-Organization-ID": str(data["org1"].id)}
            )
            assert response.status_code == 200
            
            response_data = response.json()
            assert len(response_data["interactions"]) == 1
            assert response_data["interactions"][0]["id"] == "int_1"
            assert response_data["total_count"] == 1
            assert response_data["unread_count"] == 1
    
    def test_get_interactions_optional_user_filtering(self, client: TestClient, setup_multi_tenant_data):
        """Test optional user filtering within organization"""
        data = setup_multi_tenant_data
        
        with patch('backend.auth.dependencies.get_current_active_user') as mock_auth:
            mock_user = Mock()
            mock_user.id = 3  # Member user in org1
            mock_auth.return_value = mock_user
            
            # Filter by specific user within org
            response = client.get(
                "/api/inbox/interactions?user_id=1",
                headers={"X-Organization-ID": str(data["org1"].id)}
            )
            assert response.status_code == 200
            
            response_data = response.json()
            assert len(response_data["interactions"]) == 1
            assert response_data["interactions"][0]["id"] == "int_1"
    
    def test_update_interaction_requires_member_role(self, client: TestClient, setup_multi_tenant_data):
        """Test that updating interactions requires member role"""
        data = setup_multi_tenant_data
        
        # Create a viewer user (lower than member)
        viewer_user = User(id=4, email="viewer@pressurepro.com", username="viewer1")
        viewer_role = UserOrganizationRole(
            user_id=4, organization_id=data["org1"].id, role_id="viewer", is_active=True
        )
        
        with patch('backend.auth.dependencies.get_current_active_user') as mock_auth:
            mock_user = Mock()
            mock_user.id = 4
            mock_auth.return_value = mock_user
            
            response = client.put(
                f"/api/inbox/interactions/{data['interaction1'].id}",
                json={"status": "read"},
                headers={"X-Organization-ID": str(data["org1"].id)}
            )
            assert response.status_code == 403
            assert "Required role: member" in response.json()["detail"]
    
    def test_update_interaction_org_scoped_access(self, client: TestClient, setup_multi_tenant_data):
        """Test that interaction updates are org-scoped"""
        data = setup_multi_tenant_data
        
        with patch('backend.auth.dependencies.get_current_active_user') as mock_auth:
            mock_user = Mock()
            mock_user.id = 3  # Member in org1
            mock_auth.return_value = mock_user
            
            # Try to update interaction from org2
            response = client.put(
                f"/api/inbox/interactions/{data['interaction2'].id}",
                json={"status": "read"},
                headers={"X-Organization-ID": str(data["org1"].id)}
            )
            assert response.status_code == 404
            assert "Interaction not found" in response.json()["detail"]
    
    def test_archive_interaction_requires_member_role(self, client: TestClient, setup_multi_tenant_data):
        """Test that archiving interactions requires member role"""
        data = setup_multi_tenant_data
        
        with patch('backend.auth.dependencies.get_current_active_user') as mock_auth:
            mock_user = Mock()
            mock_user.id = 3  # Member in org1
            mock_auth.return_value = mock_user
            
            response = client.delete(
                f"/api/inbox/interactions/{data['interaction1'].id}",
                headers={"X-Organization-ID": str(data["org1"].id)}
            )
            assert response.status_code == 200
            assert "Interaction archived successfully" in response.json()["message"]
    
    def test_send_response_requires_member_role(self, client: TestClient, setup_multi_tenant_data):
        """Test that sending responses requires member role"""
        data = setup_multi_tenant_data
        
        with patch('backend.auth.dependencies.get_current_active_user') as mock_auth:
            mock_user = Mock()
            mock_user.id = 3  # Member in org1
            mock_auth.return_value = mock_user
            
            with patch('backend.services.websocket_manager.websocket_service.notify_interaction_responded') as mock_notify:
                mock_notify.return_value = AsyncMock()
                
                response = client.post(
                    "/api/inbox/interactions/respond",
                    json={
                        "interaction_id": data["interaction1"].id,
                        "response_text": "Thank you for your inquiry! We'll send you a quote shortly.",
                        "response_type": "manual"
                    },
                    headers={"X-Organization-ID": str(data["org1"].id)}
                )
                assert response.status_code == 200
                assert "Response queued successfully" in response.json()["message"]
    
    def test_send_response_org_scoped_access(self, client: TestClient, setup_multi_tenant_data):
        """Test that response sending is org-scoped"""
        data = setup_multi_tenant_data
        
        with patch('backend.auth.dependencies.get_current_active_user') as mock_auth:
            mock_user = Mock()
            mock_user.id = 1  # Admin in org1
            mock_auth.return_value = mock_user
            
            # Try to respond to interaction from org2
            response = client.post(
                "/api/inbox/interactions/respond",
                json={
                    "interaction_id": data["interaction2"].id,
                    "response_text": "This should fail",
                    "response_type": "manual"
                },
                headers={"X-Organization-ID": str(data["org1"].id)}
            )
            assert response.status_code == 404
            assert "Interaction not found" in response.json()["detail"]
    
    def test_generate_ai_response_org_context(self, client: TestClient, setup_multi_tenant_data):
        """Test AI response generation with org context"""
        data = setup_multi_tenant_data
        
        with patch('backend.auth.dependencies.get_current_active_user') as mock_auth:
            with patch('backend.services.personality_response_engine.get_personality_engine') as mock_engine:
                mock_user = Mock()
                mock_user.id = 1
                mock_auth.return_value = mock_user
                
                mock_engine_instance = Mock()
                mock_engine_instance.process_interaction = AsyncMock(return_value={
                    "response_text": "Thank you for your inquiry about pressure washing services!",
                    "confidence_score": 0.85,
                    "personality_style": "professional",
                    "response_reasoning": "Customer inquiry about services"
                })
                mock_engine.return_value = mock_engine_instance
                
                with patch('backend.services.websocket_manager.websocket_service.notify_response_generated') as mock_notify:
                    mock_notify.return_value = AsyncMock()
                    
                    response = client.post(
                        "/api/inbox/interactions/generate-response",
                        json={
                            "interaction_id": data["interaction1"].id,
                            "personality_style": "professional"
                        },
                        headers={"X-Organization-ID": str(data["org1"].id)}
                    )
                    assert response.status_code == 200
                    response_data = response.json()
                    assert "suggested_response" in response_data
                    assert response_data["confidence_score"] == 0.85


class TestSocialInboxPagination:
    """Test that org-scoped filtering doesn't affect pagination"""
    
    def test_pagination_with_org_scoping(self, client: TestClient, setup_multi_tenant_data):
        """Test pagination works correctly with org-scoped queries"""
        data = setup_multi_tenant_data
        
        # Create additional interactions for org1
        additional_interactions = []
        for i in range(5):
            interaction = SocialInteraction(
                id=f"int_1_{i}",
                user_id=1,
                connection_id=1,  # Links to org1
                platform="facebook",
                interaction_type="dm",
                external_id=f"fb_msg_1_{i}",
                author_platform_id=f"customer_1_{i}",
                author_username=f"customer1_{i}",
                content=f"Test message {i}",
                sentiment="neutral",
                intent="general",
                priority_score=50.0 + i,
                status="unread",
                received_at=datetime.now(timezone.utc)
            )
            additional_interactions.append(interaction)
        
        # Add to database
        db_session = next(iter([data]))  # Get session from fixture
        db_session.add_all(additional_interactions)
        db_session.commit()
        
        with patch('backend.auth.dependencies.get_current_active_user') as mock_auth:
            mock_user = Mock()
            mock_user.id = 1
            mock_auth.return_value = mock_user
            
            # Test pagination
            response = client.get(
                "/api/inbox/interactions?limit=3&offset=0",
                headers={"X-Organization-ID": str(data["org1"].id)}
            )
            assert response.status_code == 200
            
            response_data = response.json()
            assert len(response_data["interactions"]) == 3
            assert response_data["total_count"] == 6  # Original + 5 additional


class TestTemplateAndKnowledgeOrgScoping:
    """Test org scoping for templates and knowledge base (with TODOs for full implementation)"""
    
    def test_templates_require_org_context(self, client: TestClient):
        """Test that template endpoints require organization context"""
        with patch('backend.auth.dependencies.get_current_active_user') as mock_auth:
            mock_user = Mock()
            mock_user.id = 1
            mock_auth.return_value = mock_user
            
            response = client.get("/api/inbox/templates")
            assert response.status_code == 400
            assert "Missing X-Organization-ID header" in response.json()["detail"]
    
    def test_knowledge_base_require_org_context(self, client: TestClient):
        """Test that knowledge base endpoints require organization context"""
        with patch('backend.auth.dependencies.get_current_active_user') as mock_auth:
            mock_user = Mock()
            mock_user.id = 1
            mock_auth.return_value = mock_user
            
            response = client.get("/api/inbox/knowledge-base")
            assert response.status_code == 400
            assert "Missing X-Organization-ID header" in response.json()["detail"]
    
    def test_create_template_requires_member_role(self, client: TestClient, setup_multi_tenant_data):
        """Test that creating templates requires member role"""
        data = setup_multi_tenant_data
        
        with patch('backend.auth.dependencies.get_current_active_user') as mock_auth:
            mock_user = Mock()
            mock_user.id = 3  # Member in org1
            mock_auth.return_value = mock_user
            
            response = client.post(
                "/api/inbox/templates",
                json={
                    "name": "Standard Quote Response",
                    "trigger_type": "intent",
                    "response_text": "Thank you for your interest in our pressure washing services!",
                    "personality_style": "professional"
                },
                headers={"X-Organization-ID": str(data["org1"].id)}
            )
            assert response.status_code == 200
            assert "Template created successfully" in response.json()["message"]
    
    def test_create_knowledge_entry_requires_member_role(self, client: TestClient, setup_multi_tenant_data):
        """Test that creating knowledge entries requires member role"""
        data = setup_multi_tenant_data
        
        with patch('backend.auth.dependencies.get_current_active_user') as mock_auth:
            mock_user = Mock()
            mock_user.id = 3  # Member in org1
            mock_auth.return_value = mock_user
            
            response = client.post(
                "/api/inbox/knowledge-base",
                json={
                    "title": "Pressure Washing Services",
                    "topic": "services",
                    "content": "We offer driveway, house, and deck pressure washing services.",
                    "keywords": ["pressure washing", "cleaning", "services"]
                },
                headers={"X-Organization-ID": str(data["org1"].id)}
            )
            assert response.status_code == 200
            assert "Knowledge entry created successfully" in response.json()["message"]


class TestWebhookOrgIsolation:
    """Test that webhook processing maintains org isolation"""
    
    def test_webhook_processing_maintains_org_context(self):
        """Test that webhook background processing respects org boundaries"""
        # Note: Webhook processing uses connection-based org detection
        # This test would verify that webhooks only create interactions
        # for the correct organization based on the connection
        pass  # Implementation would require more complex setup


if __name__ == "__main__":
    pytest.main([__file__])