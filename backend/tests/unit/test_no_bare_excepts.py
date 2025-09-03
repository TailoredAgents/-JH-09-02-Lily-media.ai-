"""
Test for Bare Except Block Fixes

Ensures that bare except blocks have been properly replaced with 
typed exception handling and logging.
"""
import logging
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.main import app

def test_partner_oauth_audit_exception_is_logged(caplog, monkeypatch):
    """Test that partner OAuth audit exceptions are logged properly"""
    client = TestClient(app)
    
    # Mock the database to force an audit write failure
    with patch('backend.api.partner_oauth.get_db') as mock_db:
        mock_session = MagicMock()
        mock_session.commit.side_effect = Exception("DB commit failed")
        mock_db.return_value = mock_session
        
        with caplog.at_level(logging.ERROR):
            # This should trigger the audit failure path
            resp = client.post("/api/v1/partner/oauth/meta/connect", 
                             json={"page_id": "test_page"}, 
                             headers={"Authorization": "Bearer fake_token"})
            
            # Verify that the exception was logged, not swallowed
            logged_messages = [rec.message for rec in caplog.records]
            assert any("audit write failed" in msg.lower() or 
                      "partner oauth" in msg.lower() 
                      for msg in logged_messages), f"No audit error logged. Messages: {logged_messages}"

def test_no_bare_except_blocks_remain():
    """Verify no bare except blocks remain in critical files"""
    import os
    import re
    
    critical_files = [
        'backend/api/partner_oauth.py',
        'backend/middleware/error_tracking.py', 
        'backend/tasks/x_polling_tasks.py',
        'backend/core/vector_store.py',
        'backend/services/image_processing_service.py'
    ]
    
    bare_except_pattern = re.compile(r'except:\s*\n\s*pass')
    
    for file_path in critical_files:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
                
            matches = bare_except_pattern.findall(content)
            assert len(matches) == 0, f"Found {len(matches)} bare except blocks in {file_path}"
