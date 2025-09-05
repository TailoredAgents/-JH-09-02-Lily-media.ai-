#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix Bare Except Blocks Script

Replaces all bare 'except:' blocks with proper exception handling and logging
as identified in the testing & reliability PDF.
"""
import os
import re
from pathlib import Path

def fix_bare_excepts():
    """Fix bare except blocks in critical files"""
    
    fixes = [
        # backend/api/partner_oauth.py - Multiple bare excepts in audit blocks
        {
            'file': 'backend/api/partner_oauth.py',
            'fixes': [
                {
                    'old': '''        except:
            pass''',
                    'new': '''        except Exception as audit_err:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("Partner OAuth audit write failed", 
                           exc_info=audit_err)'''
                }
            ]
        },
        
        # backend/middleware/error_tracking.py
        {
            'file': 'backend/middleware/error_tracking.py', 
            'fixes': [
                {
                    'old': '''        except:
            pass''',
                    'new': '''        except Exception as parse_err:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug("Failed to parse request body in error tracker", 
                        exc_info=parse_err)'''
                }
            ]
        },
        
        # backend/tasks/x_polling_tasks.py
        {
            'file': 'backend/tasks/x_polling_tasks.py',
            'fixes': [
                {
                    'old': '''                            except:
                                pass  # Don't fail the whole task for audit errors''',
                    'new': '''                            except Exception as audit_err:
                                import logging
                                logger = logging.getLogger(__name__)
                                logger.warning("Audit write failed in X mentions polling",
                                             extra={"err": str(audit_err)}, exc_info=audit_err)'''
                }
            ]
        },
        
        # backend/core/vector_store.py
        {
            'file': 'backend/core/vector_store.py',
            'fixes': [
                {
                    'old': '''        try:
            self._save_all()
        except:
            pass  # Ignore errors during cleanup''',
                    'new': '''        try:
            self._save_all()
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug("VectorStore cleanup save failed", 
                                            exc_info=e)'''
                }
            ]
        },
        
        # backend/services/image_processing_service.py
        {
            'file': 'backend/services/image_processing_service.py',
            'fixes': [
                {
                    'old': '''            except:
                # Fallback to default font
                font = ImageFont.load_default()''',
                    'new': '''            except Exception as font_err:
                # Fallback to default font
                font = ImageFont.load_default()
                import logging
                logger = logging.getLogger(__name__)
                logger.debug("Falling back to default font for watermark", 
                           exc_info=font_err)'''
                }
            ]
        }
    ]
    
    for fix_info in fixes:
        file_path = Path(fix_info['file'])
        if not file_path.exists():
            print(f"⚠️  File not found: {file_path}")
            continue
            
        print(f"🔧 Fixing bare except blocks in {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            original_content = content
            
            for fix in fix_info['fixes']:
                old_pattern = fix['old']
                new_replacement = fix['new']
                
                if old_pattern in content:
                    content = content.replace(old_pattern, new_replacement)
                    print(f"   ✅ Fixed bare except block")
                else:
                    # Try to find similar patterns
                    if 'except:' in content and 'pass' in content:
                        print(f"   ⚠️  Found except: and pass, but exact pattern didn't match")
            
            # Only write if content changed
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"   💾 Updated {file_path}")
            else:
                print(f"   ℹ️  No changes needed in {file_path}")
                
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")

def create_test_for_bare_excepts():
    """Create test to verify bare except fixes"""
    
    test_content = '''"""
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
    
    bare_except_pattern = re.compile(r'except:\\s*\\n\\s*pass')
    
    for file_path in critical_files:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
                
            matches = bare_except_pattern.findall(content)
            assert len(matches) == 0, f"Found {len(matches)} bare except blocks in {file_path}"
'''
    
    test_dir = Path('backend/tests/unit')
    test_dir.mkdir(exist_ok=True, parents=True)
    
    test_file = test_dir / 'test_no_bare_excepts.py'
    with open(test_file, 'w') as f:
        f.write(test_content)
    
    print(f"✅ Created test file: {test_file}")

if __name__ == "__main__":
    print("🚀 Fixing Bare Except Blocks...")
    print("=" * 50)
    
    fix_bare_excepts()
    create_test_for_bare_excepts()
    
    print("\n✅ Bare except block fixes completed!")
    print("\nNext steps:")
    print("1. Run: pytest backend/tests/unit/test_no_bare_excepts.py -v")
    print("2. Test error scenarios to verify logging works")