#!/usr/bin/env python3
"""
Security setup script for generating secure configurations
"""
import secrets
import string
import os
from pathlib import Path

def generate_secret_key(length: int = 64) -> str:
    """Generate a cryptographically secure secret key"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_api_key(length: int = 32) -> str:
    """Generate a secure API key"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def update_env_file():
    """Update .env file with secure configurations"""
    env_path = Path(".env")
    env_example_path = Path(".env.example")
    
    # Read example file
    if not env_example_path.exists():
        print("❌ .env.example file not found")
        return False
    
    with open(env_example_path, 'r') as f:
        content = f.read()
    
    # Generate secure values
    secret_key = generate_secret_key()
    api_key = generate_api_key()
    
    # Replace placeholder values
    replacements = {
        "your_secret_key_here": secret_key,
        "your_openai_api_key_here": "# Add your OpenAI API key here",
        "your_serper_api_key_here": "# Add your Serper API key here",
    }
    
    updated_content = content
    for placeholder, value in replacements.items():
        updated_content = updated_content.replace(placeholder, value)
    
    # Write to .env file
    with open(env_path, 'w') as f:
        f.write(updated_content)
    
    print("✅ .env file created with secure configurations")
    print(f"🔑 Generated SECRET_KEY: {secret_key[:20]}...")
    print("⚠️  Remember to add your actual API keys to the .env file")
    
    return True

def check_security_requirements():
    """Check if security requirements are met"""
    issues = []
    
    # Check if .env exists
    if not Path(".env").exists():
        issues.append("No .env file found")
    else:
        # Check environment variables
        from backend.core.config import get_settings
        settings = get_settings()
        
        if settings.secret_key == "your-secret-key-change-this":
            issues.append("Default SECRET_KEY is being used")
        
        if not settings.openai_api_key:
            issues.append("OpenAI API key not configured")
    
    return issues

# Auth0 configuration removed - system now uses custom JWT authentication

def main():
    """Main security setup function"""
    print("🔐 Security Setup for AI Social Media Agent")
    print("=" * 50)
    
    # Check current security status
    issues = check_security_requirements()
    
    if issues:
        print("⚠️  Security Issues Found:")
        for issue in issues:
            print(f"   - {issue}")
        print()
    
    # Update .env file
    if not Path(".env").exists():
        print("🔄 Creating secure .env file...")
        if update_env_file():
            print("✅ Security configuration completed!")
        else:
            print("❌ Failed to create .env file")
            return False
    else:
        print("📁 .env file already exists")
        response = input("Do you want to regenerate SECRET_KEY? (y/N): ")
        if response.lower() == 'y':
            update_env_file()
    
    print("\n✅ Security setup completed!")
    print("\n📝 Next Steps:")
    print("1. Add your actual API keys to .env file")
    print("2. Test authentication endpoints at /docs")
    print("3. Run: python setup_database.py --sample-data")
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)