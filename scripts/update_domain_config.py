#!/usr/bin/env python3
"""
Domain configuration update script for Cloudflare custom domain setup
Updates CORS origins and allowed hosts for the new custom domain
"""

import os
import sys
from pathlib import Path

def update_backend_config(custom_domain: str):
    """Update backend configuration for custom domain"""
    
    config_path = Path(__file__).parent.parent / "backend" / "core" / "config.py"
    
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        return False
    
    # Read current config
    with open(config_path, 'r') as f:
        content = f.read()
    
    # Define new origins
    new_origins = f'''[
    "https://{custom_domain}",
    "https://www.{custom_domain}",
    "https://app.{custom_domain}",
    "https://socialmedia-frontend-pycc.onrender.com",  # Keep Render URL as backup
    "http://localhost:3000",  # Development
    "http://localhost:5173",  # Vite dev server
]'''
    
    # Update CORS origins
    if "CORS_ALLOWED_ORIGINS" in content:
        # Find and replace existing CORS_ALLOWED_ORIGINS
        import re
        pattern = r'CORS_ALLOWED_ORIGINS\s*=\s*\[.*?\]'
        replacement = f'CORS_ALLOWED_ORIGINS = {new_origins}'
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    else:
        # Add CORS_ALLOWED_ORIGINS if it doesn't exist
        content += f'\n\n# Custom domain CORS configuration\nCORS_ALLOWED_ORIGINS = {new_origins}\n'
    
    # Write updated config
    with open(config_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated backend config for domain: {custom_domain}")
    return True

def create_frontend_env_template(custom_domain: str):
    """Create frontend environment template for production"""
    
    env_path = Path(__file__).parent.parent / "frontend" / ".env.production.template"
    
    env_content = f"""# Production environment variables for custom domain
VITE_API_BASE_URL=https://api.{custom_domain}
VITE_APP_URL=https://{custom_domain}
VITE_APP_NAME=Lily Media AI
VITE_SENTRY_DSN=your_sentry_dsn_here
VITE_FEATURE_PARTNER_OAUTH=true

# Social Media Platform Configuration
VITE_META_CLIENT_ID=your_meta_client_id
VITE_TWITTER_CLIENT_ID=your_twitter_client_id
VITE_INSTAGRAM_CLIENT_ID=your_instagram_client_id
VITE_LINKEDIN_CLIENT_ID=your_linkedin_client_id

# Feature Flags
VITE_FEATURE_AUTONOMOUS_POSTING=true
VITE_FEATURE_DEEP_RESEARCH=true
VITE_FEATURE_BILLING=true
"""
    
    with open(env_path, 'w') as f:
        f.write(env_content)
    
    print(f"✅ Created frontend environment template: {env_path}")
    return True

def create_render_deploy_config(custom_domain: str):
    """Create Render deployment configuration"""
    
    render_config_path = Path(__file__).parent.parent / "render.yaml"
    
    render_config = f"""# Render deployment configuration for custom domain
services:
  - type: web
    name: socialmedia-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: FRONTEND_URL
        value: https://{custom_domain}
      - key: ALLOWED_ORIGINS
        value: https://{custom_domain},https://www.{custom_domain},https://app.{custom_domain}
      - key: CORS_ALLOWED_ORIGINS
        value: https://{custom_domain},https://www.{custom_domain}
      - key: DATABASE_URL
        fromDatabase:
          name: socialmedia-db
          property: connectionString
      - key: SECRET_KEY
        generateValue: true
      - key: OPENAI_API_KEY
        sync: false
      - key: SENTRY_DSN
        sync: false
      - key: REDIS_URL
        fromService:
          type: redis
          name: socialmedia-redis
          property: connectionString

  - type: web
    name: socialmedia-frontend
    env: static
    buildCommand: npm ci && npm run build
    staticPublishPath: ./dist
    envVars:
      - key: VITE_API_BASE_URL
        value: https://api.{custom_domain}
      - key: VITE_APP_URL
        value: https://{custom_domain}

databases:
  - name: socialmedia-db
    databaseName: socialmedia
    user: socialmedia
    region: oregon

services:
  - type: redis
    name: socialmedia-redis
    region: oregon
"""
    
    with open(render_config_path, 'w') as f:
        f.write(render_config)
    
    print(f"✅ Created Render deployment config: {render_config_path}")
    return True

def create_nginx_config(custom_domain: str):
    """Create nginx configuration for custom domain (if self-hosting)"""
    
    nginx_path = Path(__file__).parent.parent / "nginx" / "sites-available" / "lilymedia"
    nginx_path.parent.mkdir(parents=True, exist_ok=True)
    
    nginx_config = f"""# Nginx configuration for {custom_domain}
server {{
    listen 80;
    server_name {custom_domain} www.{custom_domain};
    return 301 https://$server_name$request_uri;
}}

server {{
    listen 443 ssl http2;
    server_name {custom_domain} www.{custom_domain};

    # SSL Configuration (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/{custom_domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{custom_domain}/privkey.pem;
    
    # SSL Security Settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-SHA384;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin-when-cross-origin";
    
    # Frontend (React app)
    location / {{
        proxy_pass http://localhost:3000;  # Or static files location
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }}
    
    # API Backend
    location /api/ {{
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # CORS headers
        add_header Access-Control-Allow-Origin "https://{custom_domain}";
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
        add_header Access-Control-Allow-Headers "Origin, X-Requested-With, Content-Type, Accept, Authorization";
    }}
    
    # WebSocket support
    location /ws/ {{
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
    
    # Static assets caching
    location ~* \\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {{
        expires 1M;
        add_header Cache-Control "public, immutable";
    }}
}}

# API subdomain
server {{
    listen 80;
    server_name api.{custom_domain};
    return 301 https://$server_name$request_uri;
}}

server {{
    listen 443 ssl http2;
    server_name api.{custom_domain};
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/{custom_domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{custom_domain}/privkey.pem;
    
    # Proxy all requests to backend
    location / {{
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }}
}}
"""
    
    with open(nginx_path, 'w') as f:
        f.write(nginx_config)
    
    print(f"✅ Created nginx configuration: {nginx_path}")
    return True

def create_cloudflare_api_script(custom_domain: str):
    """Create script for Cloudflare API automation"""
    
    script_path = Path(__file__).parent / "cloudflare_setup.sh"
    
    script_content = f"""#!/bin/bash
# Cloudflare DNS setup automation script for {custom_domain}
# Requires CLOUDFLARE_API_TOKEN and CLOUDFLARE_ZONE_ID environment variables

set -e

DOMAIN="{custom_domain}"
RENDER_BACKEND="socialmedia-api-wxip.onrender.com"
RENDER_FRONTEND="socialmedia-frontend-pycc.onrender.com"

# Check required environment variables
if [[ -z "$CLOUDFLARE_API_TOKEN" || -z "$CLOUDFLARE_ZONE_ID" ]]; then
    echo "❌ Please set CLOUDFLARE_API_TOKEN and CLOUDFLARE_ZONE_ID environment variables"
    exit 1
fi

echo "🔧 Setting up DNS records for $DOMAIN..."

# Function to create DNS record
create_dns_record() {{
    local name="$1"
    local type="$2"
    local content="$3"
    local proxied="$4"
    
    echo "Creating $type record: $name -> $content"
    
    curl -X POST "https://api.cloudflare.com/client/v4/zones/$CLOUDFLARE_ZONE_ID/dns_records" \\
        -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \\
        -H "Content-Type: application/json" \\
        --data "{{
            \\"type\\": \\"$type\\",
            \\"name\\": \\"$name\\",
            \\"content\\": \\"$content\\",
            \\"proxied\\": $proxied
        }}" | jq '.success'
}}

# Create main domain records
create_dns_record "$DOMAIN" "CNAME" "$RENDER_FRONTEND" "true"
create_dns_record "www.$DOMAIN" "CNAME" "$DOMAIN" "true"
create_dns_record "api.$DOMAIN" "CNAME" "$RENDER_BACKEND" "true"

echo "✅ DNS records created successfully!"
echo "⏳ DNS propagation may take up to 24 hours"
echo "🔗 Test your domains:"
echo "   - https://$DOMAIN"
echo "   - https://www.$DOMAIN"  
echo "   - https://api.$DOMAIN/health"
"""
    
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    # Make script executable
    os.chmod(script_path, 0o755)
    
    print(f"✅ Created Cloudflare automation script: {script_path}")
    return True

def main():
    """Main function to update domain configuration"""
    
    if len(sys.argv) != 2:
        print("Usage: python update_domain_config.py <custom_domain>")
        print("Example: python update_domain_config.py lilymedia.ai")
        sys.exit(1)
    
    custom_domain = sys.argv[1].lower().strip()
    
    if not custom_domain or '.' not in custom_domain:
        print("❌ Please provide a valid domain name")
        sys.exit(1)
    
    print(f"🚀 Updating configuration for custom domain: {custom_domain}")
    print("=" * 60)
    
    # Update configurations
    success = True
    
    try:
        success &= update_backend_config(custom_domain)
        success &= create_frontend_env_template(custom_domain)
        success &= create_render_deploy_config(custom_domain)
        success &= create_nginx_config(custom_domain)
        success &= create_cloudflare_api_script(custom_domain)
        
        if success:
            print("=" * 60)
            print("✅ Domain configuration update completed!")
            print()
            print("Next steps:")
            print("1. Add domain to Cloudflare dashboard")
            print("2. Update nameservers at your domain registrar")
            print("3. Configure DNS records (or run ./scripts/cloudflare_setup.sh)")
            print("4. Update Render environment variables")
            print("5. Redeploy frontend and backend")
            print("6. Test all endpoints")
            print()
            print("Configuration files created:")
            print("- Backend CORS origins updated")
            print("- Frontend .env.production.template")
            print("- render.yaml deployment config")
            print("- nginx configuration (for self-hosting)")
            print("- Cloudflare automation script")
            
        else:
            print("❌ Some configuration updates failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error updating domain configuration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()