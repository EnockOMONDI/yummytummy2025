# Custom Domain Setup for YummyTummy Django App

## Overview
This guide explains how to configure your YummyTummy Django application to work with your own custom domain while maintaining Render.com deployment compatibility.

## ALLOWED_HOSTS Configuration

### Current Setup
The application is configured to handle both Render.com subdomains and custom domains through environment variables.

### Environment Variable Examples

#### 1. Render.com Only (Initial Deployment)
```bash
ALLOWED_HOSTS=*.onrender.com
CSRF_TRUSTED_ORIGINS=https://*.onrender.com
```

#### 2. Custom Domain + Render.com (Recommended)
```bash
ALLOWED_HOSTS=*.onrender.com,yummytummy.com,www.yummytummy.com
CSRF_TRUSTED_ORIGINS=https://*.onrender.com,https://yummytummy.com,https://www.yummytummy.com
```

#### 3. Multiple Domains + Subdomains
```bash
ALLOWED_HOSTS=*.onrender.com,yummytummy.com,www.yummytummy.com,api.yummytummy.com,shop.yummytummy.com
CSRF_TRUSTED_ORIGINS=https://*.onrender.com,https://yummytummy.com,https://www.yummytummy.com,https://api.yummytummy.com,https://shop.yummytummy.com
```

## Steps to Add Your Custom Domain

### Step 1: Purchase and Configure Domain
1. Purchase your domain (e.g., `yummytummy.com`)
2. Access your domain registrar's DNS settings

### Step 2: Configure DNS Records
Add these DNS records in your domain registrar:

```
Type: CNAME
Name: www
Value: your-app-name.onrender.com

Type: A (or ALIAS/ANAME if supported)
Name: @ (root domain)
Value: [Render.com IP address - check Render docs for current IP]
```

### Step 3: Update Render.com Environment Variables
In your Render.com dashboard:

1. Go to your service settings
2. Update environment variables:
   ```
   ALLOWED_HOSTS=*.onrender.com,yummytummy.com,www.yummytummy.com
   CSRF_TRUSTED_ORIGINS=https://*.onrender.com,https://yummytummy.com,https://www.yummytummy.com
   ```

### Step 4: Configure Custom Domain in Render
1. In Render.com dashboard, go to your service
2. Click "Settings" → "Custom Domains"
3. Add your domains:
   - `yummytummy.com`
   - `www.yummytummy.com`
4. Render will automatically provision SSL certificates

### Step 5: Test Your Setup
1. Visit `https://yummytummy.com` - should work
2. Visit `https://www.yummytummy.com` - should work
3. Visit `https://your-app-name.onrender.com` - should still work

## Security Considerations

### ✅ Best Practices
- Always include `*.onrender.com` for deployment compatibility
- Use specific domain names, avoid wildcards like `*`
- Include both `domain.com` and `www.domain.com`
- Always use HTTPS in CSRF_TRUSTED_ORIGINS

### ❌ Avoid These
```bash
# DON'T use wildcard for all domains
ALLOWED_HOSTS=*

# DON'T forget HTTPS in CSRF_TRUSTED_ORIGINS
CSRF_TRUSTED_ORIGINS=yummytummy.com  # Missing https://

# DON'T use HTTP in production
CSRF_TRUSTED_ORIGINS=http://yummytummy.com
```

## Troubleshooting

### Common Issues

1. **"Invalid HTTP_HOST header"**
   - Check ALLOWED_HOSTS includes your domain
   - Ensure no typos in domain name

2. **CSRF verification failed**
   - Check CSRF_TRUSTED_ORIGINS includes `https://` prefix
   - Ensure domain matches exactly

3. **SSL certificate issues**
   - Wait for Render to provision certificates (can take up to 24 hours)
   - Check DNS propagation with tools like `dig` or online DNS checkers

### Testing Commands
```bash
# Test DNS resolution
dig yummytummy.com
dig www.yummytummy.com

# Test HTTPS
curl -I https://yummytummy.com
curl -I https://www.yummytummy.com
```

## Example Domain Configurations

### E-commerce Store (yummytummy.com)
```bash
ALLOWED_HOSTS=*.onrender.com,yummytummy.com,www.yummytummy.com,shop.yummytummy.com
CSRF_TRUSTED_ORIGINS=https://*.onrender.com,https://yummytummy.com,https://www.yummytummy.com,https://shop.yummytummy.com
```

### Multi-brand Setup
```bash
ALLOWED_HOSTS=*.onrender.com,yummytummy.com,www.yummytummy.com,tastytreats.com,www.tastytreats.com
CSRF_TRUSTED_ORIGINS=https://*.onrender.com,https://yummytummy.com,https://www.yummytummy.com,https://tastytreats.com,https://www.tastytreats.com
```

## Notes
- Changes to environment variables require a redeploy
- DNS changes can take up to 48 hours to propagate globally
- Always test both `domain.com` and `www.domain.com`
- Keep Render.com subdomain for admin access and backups
