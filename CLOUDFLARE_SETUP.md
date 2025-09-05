# Cloudflare Custom Domain Setup Guide

This guide provides step-by-step instructions for setting up a custom domain with Cloudflare for the Lily Media AI platform, including SSL certificates and redirect configuration.

## Prerequisites

1. **Domain Name**: Purchase a domain name (e.g., `lilymedia.ai`)
2. **Cloudflare Account**: Sign up at [cloudflare.com](https://cloudflare.com)
3. **Production Deployments**: Backend and frontend deployed on Render.com

## Current Production URLs

- **Backend API**: https://socialmedia-api-wxip.onrender.com
- **Frontend App**: https://socialmedia-frontend-pycc.onrender.com

## Step 1: Add Domain to Cloudflare

1. **Add Site**:
   - Log into Cloudflare dashboard
   - Click "Add Site"
   - Enter your domain name (e.g., `lilymedia.ai`)
   - Choose the Free plan (or Pro for advanced features)

2. **Verify DNS Records**:
   - Cloudflare will scan your existing DNS records
   - Review and confirm the records

3. **Update Nameservers**:
   - Copy the Cloudflare nameservers provided
   - Update nameservers at your domain registrar
   - Wait for DNS propagation (up to 24 hours)

## Step 2: Configure DNS Records

Set up the following DNS records in Cloudflare:

### Main Domain Records

```
Type: A
Name: @
Content: [Your server IP or use CNAME to Render]
Proxy: Enabled (Orange cloud)
TTL: Auto

Type: CNAME
Name: www
Content: lilymedia.ai
Proxy: Enabled (Orange cloud)
TTL: Auto
```

### API Subdomain

```
Type: CNAME
Name: api
Content: socialmedia-api-wxip.onrender.com
Proxy: Enabled (Orange cloud)
TTL: Auto
```

### App Subdomain (Optional)

```
Type: CNAME
Name: app
Content: socialmedia-frontend-pycc.onrender.com
Proxy: Enabled (Orange cloud)
TTL: Auto
```

## Step 3: SSL/TLS Configuration

1. **SSL/TLS Mode**:
   - Go to SSL/TLS > Overview
   - Set encryption mode to "Full (strict)"
   - This ensures end-to-end encryption

2. **Universal SSL**:
   - Verify Universal SSL certificate is active
   - Should show "Active Certificate" status

3. **Always Use HTTPS**:
   - Go to SSL/TLS > Edge Certificates
   - Enable "Always Use HTTPS"
   - Enable "HTTP Strict Transport Security (HSTS)"

## Step 4: Page Rules for Redirects

Configure Page Rules for proper routing:

### Rule 1: API Redirects
```
URL Pattern: api.lilymedia.ai/*
Settings:
  - SSL: Full (strict)
  - Always Use HTTPS: On
```

### Rule 2: WWW Redirect
```
URL Pattern: www.lilymedia.ai/*
Settings:
  - Forwarding URL: 301 Redirect
  - Destination: https://lilymedia.ai/$1
```

### Rule 3: Root Domain
```
URL Pattern: lilymedia.ai/*
Settings:
  - SSL: Full (strict)
  - Always Use HTTPS: On
```

## Step 5: Security Settings

### Security Level
- Go to Security > Settings
- Set Security Level to "Medium" or "High"
- Enable "Bot Fight Mode"

### Firewall Rules
Create firewall rules for API protection:

```
Rule 1: Rate Limiting
Expression: (http.request.uri.path contains "/api/")
Action: Rate Limit (100 requests per minute per IP)

Rule 2: Geographic Blocking (Optional)
Expression: (ip.geoip.country ne "US" and ip.geoip.country ne "CA")
Action: Block (if restricting to North America)
```

### WAF Custom Rules
```
Rule: API Protection
Expression: (http.request.uri.path contains "/api/" and http.request.method eq "POST" and not cf.verified_bot)
Action: Managed Challenge
```

## Step 6: Performance Optimization

### Speed Settings
- Go to Speed > Optimization
- Enable "Auto Minify" for HTML, CSS, and JavaScript
- Enable "Brotli" compression
- Enable "Early Hints"

### Caching Rules
```
Rule 1: API No Cache
URL Pattern: api.lilymedia.ai/*
Settings:
  - Cache Level: Bypass
  - Edge Cache TTL: Respect Existing Headers

Rule 2: Static Assets Cache
URL Pattern: lilymedia.ai/assets/*
Settings:
  - Cache Level: Cache Everything
  - Edge Cache TTL: 1 month
  - Browser Cache TTL: 1 month
```

## Step 7: Update Application Configuration

### Backend Configuration
Update backend settings to handle the new domain:

```python
# backend/core/config.py
ALLOWED_ORIGINS = [
    "https://lilymedia.ai",
    "https://www.lilymedia.ai",
    "https://app.lilymedia.ai",  # If using app subdomain
    "https://socialmedia-frontend-pycc.onrender.com",  # Keep Render URL as backup
]

CORS_ORIGINS = ALLOWED_ORIGINS
```

### Frontend Configuration
Update frontend environment variables:

```bash
# Production environment
VITE_API_BASE_URL=https://api.lilymedia.ai
VITE_APP_URL=https://lilymedia.ai
```

### Environment Variables
Set these in your Render deployment:

```bash
# Backend
FRONTEND_URL=https://lilymedia.ai
ALLOWED_ORIGINS=https://lilymedia.ai,https://www.lilymedia.ai

# Frontend  
VITE_API_BASE_URL=https://api.lilymedia.ai
```

## Step 8: Testing and Verification

### DNS Propagation
Check DNS propagation:
```bash
# Check A records
dig lilymedia.ai

# Check CNAME records
dig api.lilymedia.ai
dig www.lilymedia.ai

# Check from multiple locations
nslookup lilymedia.ai 8.8.8.8
nslookup lilymedia.ai 1.1.1.1
```

### SSL Certificate Testing
Test SSL configuration:
- Use [SSL Labs](https://www.ssllabs.com/ssltest/) to test your domain
- Should achieve A+ rating with proper configuration

### Functionality Testing
1. **Main Domain**: https://lilymedia.ai should load the frontend
2. **WWW Redirect**: https://www.lilymedia.ai should redirect to https://lilymedia.ai
3. **API Endpoint**: https://api.lilymedia.ai/health should return API health status
4. **HTTPS Enforcement**: http://lilymedia.ai should redirect to https://lilymedia.ai

## Step 9: Monitoring Setup

### Cloudflare Analytics
- Monitor traffic patterns in Cloudflare Analytics
- Set up alerts for high traffic or security events

### Health Checks
Create health check monitors:
```
Monitor 1: Frontend
URL: https://lilymedia.ai
Expected: 200 OK
Frequency: 5 minutes

Monitor 2: API
URL: https://api.lilymedia.ai/health  
Expected: 200 OK with JSON response
Frequency: 1 minute
```

## Troubleshooting

### Common Issues

1. **SSL Certificate Pending**:
   - Wait up to 24 hours for certificate provisioning
   - Ensure DNS is properly configured
   - Check that proxy (orange cloud) is enabled

2. **Redirect Loops**:
   - Verify SSL/TLS mode is "Full (strict)"
   - Check Page Rules for conflicts
   - Ensure backend handles HTTPS properly

3. **CORS Errors**:
   - Update ALLOWED_ORIGINS in backend configuration
   - Redeploy backend with new settings
   - Clear Cloudflare cache if needed

4. **API Not Accessible**:
   - Verify CNAME record for api subdomain
   - Check that Render.com allows custom domains
   - Test direct Render URL first

### Cache Clearing
Clear Cloudflare cache when deploying updates:
- Go to Caching > Purge Cache
- Select "Purge Everything" for major updates
- Use "Custom Purge" for specific files

## Security Best Practices

1. **Enable HSTS**: Force HTTPS for all requests
2. **Bot Protection**: Enable Bot Fight Mode
3. **Rate Limiting**: Protect API endpoints from abuse
4. **Geographic Filtering**: Block requests from unwanted regions
5. **DDoS Protection**: Cloudflare provides automatic DDoS protection
6. **Web Application Firewall**: Enable WAF rules for common attacks

## Cost Considerations

### Free Plan Includes:
- Unlimited bandwidth
- Basic DDoS protection
- SSL certificate
- Basic analytics
- 3 Page Rules

### Pro Plan ($20/month) Adds:
- 20 Page Rules
- Advanced analytics
- Image optimization
- Mobile optimization
- Custom SSL certificates

## Maintenance

### Regular Tasks
1. **Monitor SSL expiry**: Cloudflare handles renewal automatically
2. **Review analytics**: Weekly traffic and security reports
3. **Update firewall rules**: As needed for new threats
4. **Cache optimization**: Adjust rules based on performance data

### Emergency Procedures
1. **DDoS Attack**: Cloudflare auto-protects, monitor dashboard
2. **SSL Issues**: Check certificate status, contact Cloudflare support
3. **High Traffic**: Monitor origin server capacity, consider caching rules