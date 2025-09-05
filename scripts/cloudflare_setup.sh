#!/bin/bash
# Cloudflare DNS setup automation script for lilymedia.ai
# Requires CLOUDFLARE_API_TOKEN and CLOUDFLARE_ZONE_ID environment variables

set -e

DOMAIN="lilymedia.ai"
RENDER_BACKEND="socialmedia-api-wxip.onrender.com"
RENDER_FRONTEND="socialmedia-frontend-pycc.onrender.com"

# Check required environment variables
if [[ -z "$CLOUDFLARE_API_TOKEN" || -z "$CLOUDFLARE_ZONE_ID" ]]; then
    echo "❌ Please set CLOUDFLARE_API_TOKEN and CLOUDFLARE_ZONE_ID environment variables"
    exit 1
fi

echo "🔧 Setting up DNS records for $DOMAIN..."

# Function to create DNS record
create_dns_record() {
    local name="$1"
    local type="$2"
    local content="$3"
    local proxied="$4"
    
    echo "Creating $type record: $name -> $content"
    
    curl -X POST "https://api.cloudflare.com/client/v4/zones/$CLOUDFLARE_ZONE_ID/dns_records" \
        -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
        -H "Content-Type: application/json" \
        --data "{
            \"type\": \"$type\",
            \"name\": \"$name\",
            \"content\": \"$content\",
            \"proxied\": $proxied
        }" | jq '.success'
}

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
