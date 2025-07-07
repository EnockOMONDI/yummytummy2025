# 🔧 Environment Variables Checklist for Render.com

## 🚨 **CRITICAL UPDATES NEEDED**

Based on your local `.env` file, here are the environment variables that need to be updated in your Render.com dashboard:

### **1. ALLOWED_HOSTS** (CRITICAL SECURITY UPDATE)
```
❌ Current (Render): *
✅ Required: localhost,127.0.0.1,www.livegreat.co.ke,livegreat.co.ke,.onrender.com
```
**Impact:** Removes security vulnerability from wildcard setting

### **2. CSRF_TRUSTED_ORIGINS** (SECURITY)
```
✅ Required: https://*.onrender.com,https://www.livegreat.co.ke,https://livegreat.co.ke
```
**Impact:** Ensures CSRF protection works with new domain structure

### **3. SITE_URL** (FUNCTIONALITY)
```
✅ Required: https://www.livegreat.co.ke
```
**Impact:** Ensures all generated URLs use www subdomain

---

## 📋 **COMPLETE ENVIRONMENT VARIABLES REFERENCE**

Copy this list and verify each variable in your Render.com dashboard:

### **Django Core Settings**
- [ ] `SECRET_KEY` = `dabjrforofhiohergbergpprod-key-2ehghoertgnge-in-prger`
- [ ] `DEBUG` = `False`
- [ ] `DJANGO_LOG_LEVEL` = `INFO`

### **Domain & Security Settings** ⚠️ **CRITICAL UPDATES**
- [ ] `ALLOWED_HOSTS` = `localhost,127.0.0.1,www.livegreat.co.ke,livegreat.co.ke,.onrender.com`
- [ ] `CSRF_TRUSTED_ORIGINS` = `https://*.onrender.com,https://www.livegreat.co.ke,https://livegreat.co.ke`
- [ ] `SITE_URL` = `https://www.livegreat.co.ke`
- [ ] `SECURE_SSL_REDIRECT` = `True`
- [ ] `SECURE_PROXY_SSL_HEADER` = `HTTP_X_FORWARDED_PROTO,https`

### **Database**
- [ ] `DATABASE_URL` = `postgresql://neondb_owner:npg_Spxz4nomvTJ8@ep-billowing-pond-a9faz0tc-pooler.gwc.azure.neon.tech/neondb?sslmode=require`

### **Email Configuration**
- [ ] `EMAIL_BACKEND` = `django.core.mail.backends.smtp.EmailBackend`
- [ ] `EMAIL_HOST` = `smtp.gmail.com`
- [ ] `EMAIL_PORT` = `587`
- [ ] `EMAIL_USE_TLS` = `True`
- [ ] `EMAIL_HOST_USER` = `dedeexpeditions@gmail.com`
- [ ] `EMAIL_HOST_PASSWORD` = `roqu frlt wvof rqxk`
- [ ] `DEFAULT_FROM_EMAIL` = `YummyTummy Goodies`

### **Uploadcare (Image Management)**
- [ ] `UPLOADCARE_PUBLIC_KEY` = `1528b06f591935e6491d`
- [ ] `UPLOADCARE_SECRET_KEY` = `d3980def5fa035e7eed2`

### **M-Pesa Configuration**
- [ ] `MPESA_BUSINESS_SHORT_CODE` = `6319470`
- [ ] `MPESA_PASSKEY` = `f473271a17488fd9a1230c2e43f6fe63db04eabc8bc7db8d1e21e4fe753f598d`
- [ ] `MPESA_CONSUMER_KEY` = `p2D6eI01gcYtvwHgrh7UVsX61sFaAmKA4hZDZaHI3KBN0Xv4`
- [ ] `MPESA_CONSUMER_SECRET` = `MQKc16J58WljEleReHaRAXzXSv6nmyxWCYqxAKzvE3NNUIpDYk94LJzQwTu1pGJn`
- [ ] `MPESA_ENVIRONMENT` = `production`
- [ ] `MPESA_TRANSACTION_TYPE` = `CustomerBuyGoodsOnline` *(Till Number - Confirmed)*

---

## 🎯 **PRIORITY UPDATE ORDER**

Update these variables in this order for maximum safety:

### **Phase 1: Critical Security (Update First)**
1. `ALLOWED_HOSTS` - Fixes security vulnerability
2. `CSRF_TRUSTED_ORIGINS` - Ensures CSRF protection
3. `SITE_URL` - Ensures correct URL generation

### **Phase 2: Verify Existing (Check These)**
4. `DEBUG` - Should be `False`
5. `SECRET_KEY` - Should be secure
6. `DATABASE_URL` - Should be your Neon PostgreSQL URL

### **Phase 3: Functionality (Verify These Work)**
7. M-Pesa credentials - Should be production values
8. Email settings - Should be working Gmail configuration
9. Uploadcare keys - Should be your image management keys

---

## 🚀 **QUICK UPDATE STEPS**

1. **Login to Render.com**
2. **Go to your YummyTummy service**
3. **Click "Environment" tab**
4. **Update the 3 critical variables first:**
   - `ALLOWED_HOSTS`
   - `CSRF_TRUSTED_ORIGINS` 
   - `SITE_URL`
5. **Save changes** (Render will auto-deploy)
6. **Wait for deployment** to complete
7. **Run verification script** to test

---

## ✅ **VERIFICATION COMMANDS**

After updating environment variables, run these commands:

### **1. Run Post-Deployment Verification**
```bash
python post_deployment_verification.py
```

### **2. Test Domain Redirection Manually**
```bash
# Test apex domain redirect
curl -I https://livegreat.co.ke

# Test www domain loads
curl -I https://www.livegreat.co.ke

# Test M-Pesa callback accessibility
curl -X POST https://www.livegreat.co.ke/mpesa/callback/
```

### **3. Check Render Logs**
- Go to Render dashboard > Logs tab
- Look for successful startup messages
- Watch for any DisallowedHost errors

---

## 🆘 **TROUBLESHOOTING**

### **Common Issues After Update**

**Issue 1: DisallowedHost Error**
```
Error: Invalid HTTP_HOST header
Solution: Double-check ALLOWED_HOSTS value is exactly correct
```

**Issue 2: CSRF Verification Failed**
```
Error: CSRF verification failed
Solution: Verify CSRF_TRUSTED_ORIGINS includes your domain
```

**Issue 3: M-Pesa Callbacks Failing**
```
Error: M-Pesa callbacks not working
Solution: Verify middleware exemptions are working correctly
```

---

## 📞 **READY TO UPDATE?**

1. ✅ **Review this checklist**
2. 🔧 **Update the 3 critical variables in Render**
3. ⏳ **Wait for deployment to complete**
4. 🧪 **Run verification script**
5. 📊 **Monitor logs for issues**

**Start with the critical security updates first! 🚀**
