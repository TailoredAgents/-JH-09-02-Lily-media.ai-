# Custom Domain Quick Start Guide

## 🚀 One-Command Setup

```bash
# Update all configuration files for your custom domain
python scripts/update_domain_config.py yourdomain.com
```

This script automatically:
- ✅ Updates backend CORS configuration
- ✅ Creates frontend production environment template
- ✅ Generates Render deployment config
- ✅ Creates nginx configuration (if self-hosting)
- ✅ Generates Cloudflare automation script

## 📋 Checklist

### Step 1: Domain Setup
- [ ] Purchase domain name
- [ ] Create Cloudflare account
- [ ] Add domain to Cloudflare
- [ ] Update nameservers at registrar

### Step 2: DNS Configuration  
- [ ] Create A/CNAME records for main domain
- [ ] Create CNAME record for `api.yourdomain.com` → `socialmedia-api-wxip.onrender.com`
- [ ] Create CNAME record for `www.yourdomain.com` → `yourdomain.com`
- [ ] Enable Cloudflare proxy (orange cloud)

### Step 3: SSL & Security
- [ ] Set SSL/TLS mode to "Full (strict)"
- [ ] Enable "Always Use HTTPS" 
- [ ] Enable HSTS
- [ ] Configure firewall rules
- [ ] Set up rate limiting

### Step 4: Application Updates
- [ ] Update Render environment variables:
  ```bash
  # Backend
  FRONTEND_URL=https://yourdomain.com
  ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
  
  # Frontend  
  VITE_API_BASE_URL=https://api.yourdomain.com
  VITE_APP_URL=https://yourdomain.com
  ```
- [ ] Redeploy backend and frontend on Render

### Step 5: Testing
- [ ] Test main domain: `https://yourdomain.com`
- [ ] Test www redirect: `https://www.yourdomain.com`
- [ ] Test API endpoint: `https://api.yourdomain.com/health`
- [ ] Test HTTPS enforcement
- [ ] Verify SSL certificate (A+ rating on SSL Labs)

## 🔧 Automated DNS Setup

If you have Cloudflare API credentials:

```bash
export CLOUDFLARE_API_TOKEN="your_token"
export CLOUDFLARE_ZONE_ID="your_zone_id"
./scripts/cloudflare_setup.sh
```

## 🌐 Current URLs

**Before Custom Domain:**
- Frontend: https://socialmedia-frontend-pycc.onrender.com
- Backend: https://socialmedia-api-wxip.onrender.com

**After Custom Domain:**
- Frontend: https://yourdomain.com
- Backend: https://api.yourdomain.com

## 🔍 Troubleshooting

### SSL Certificate Issues
```bash
# Check certificate status
curl -I https://yourdomain.com
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com
```

### DNS Propagation
```bash
# Check DNS from multiple locations  
dig yourdomain.com @8.8.8.8
dig yourdomain.com @1.1.1.1
nslookup api.yourdomain.com
```

### API Connectivity
```bash
# Test API endpoint
curl https://api.yourdomain.com/health
curl https://api.yourdomain.com/api/monitoring/health
```

## 📞 Support

For issues with:
- **Cloudflare**: Check Cloudflare dashboard and documentation
- **Render**: Check Render deployment logs and support
- **DNS**: Use DNS checker tools online
- **SSL**: Use SSL Labs test and certificate transparency logs

## 🔒 Security Notes

- Custom domain provides additional security through Cloudflare protection
- DDoS protection included automatically
- Web Application Firewall available
- Geographic filtering options
- Bot protection enabled

## 💰 Cost Estimate

- **Domain**: $10-50/year (depending on TLD)
- **Cloudflare Free**: $0/month (sufficient for most use cases)
- **Cloudflare Pro**: $20/month (advanced features)
- **Render**: Same hosting costs as before