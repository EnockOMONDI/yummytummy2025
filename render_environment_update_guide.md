# 🚀 Render.com Environment Variables Update Guide
## WWW Domain Redirection & Security Configuration

### 📋 **CRITICAL ENVIRONMENT VARIABLES TO UPDATE**

You need to update these specific environment variables in your Render.com dashboard:

#### 🔒 **1. ALLOWED_HOSTS** (CRITICAL SECURITY UPDATE)
```
Current Value: *
New Value: localhost,127.0.0.1,www.livegreat.co.ke,livegreat.co.ke,.onrender.com
```
**Why:** Removes security vulnerability from wildcard setting

#### 🌐 **2. CSRF_TRUSTED_ORIGINS** (Verify/Update)
```
Recommended Value: https://*.onrender.com,https://www.livegreat.co.ke,https://livegreat.co.ke
```

#### 🔗 **3. SITE_URL** (Verify)
```
Required Value: https://www.livegreat.co.ke
```

---

## 🛠️ **STEP-BY-STEP UPDATE PROCESS**

### Step 1: Access Render Dashboard
1. Go to [https://render.com](https://render.com) and login
2. Find your YummyTummy service (likely "yummytummy-store")
3. Click on the service name
4. Click **"Environment"** tab in the left sidebar

### Step 2: Update Each Variable
For each variable above:
1. **Find the variable** in your environment list
2. **Click the pencil/edit icon** next to it
3. **Replace the value** with the new value shown above
4. **Click "Save"** or "Update"

### Step 3: Add Missing Variables (if needed)
If any variable is missing:
1. Click **"Add Environment Variable"**
2. Enter the variable name and value
3. Click **"Save"**

### Step 4: Trigger Deployment
- Render will automatically redeploy after environment changes
- Or manually click **"Manual Deploy"** > **"Deploy latest commit"**

---

## ✅ **COMPLETE ENVIRONMENT VARIABLES CHECKLIST**

Copy this checklist and verify each variable in your Render dashboard:

```
□ ALLOWED_HOSTS = localhost,127.0.0.1,www.livegreat.co.ke,livegreat.co.ke,.onrender.com
□ CSRF_TRUSTED_ORIGINS = https://*.onrender.com,https://www.livegreat.co.ke,https://livegreat.co.ke
□ SITE_URL = https://www.livegreat.co.ke
□ DEBUG = False
□ SECRET_KEY = (your secure secret key)
□ DATABASE_URL = (your Neon PostgreSQL connection string)
□ MPESA_BUSINESS_SHORT_CODE = 6319470
□ MPESA_PASSKEY = (your M-Pesa passkey)
□ MPESA_CONSUMER_KEY = (your M-Pesa consumer key)
□ MPESA_CONSUMER_SECRET = (your M-Pesa consumer secret)
□ MPESA_ENVIRONMENT = production
□ EMAIL_HOST_USER = (your email)
□ EMAIL_HOST_PASSWORD = (your email password)
□ UPLOADCARE_PUBLIC_KEY = (your Uploadcare key)
□ UPLOADCARE_SECRET_KEY = (your Uploadcare secret)
```

---

## 🧪 **POST-DEPLOYMENT VERIFICATION TESTS**

After deployment completes, test these scenarios:

### Test 1: Domain Redirection
```
Visit: https://livegreat.co.ke
Expected: Redirects to https://www.livegreat.co.ke (301 redirect)
```

### Test 2: WWW Domain (No Redirect)
```
Visit: https://www.livegreat.co.ke
Expected: Loads normally (200 status)
```

### Test 3: Path Preservation
```
Visit: https://livegreat.co.ke/products/
Expected: Redirects to https://www.livegreat.co.ke/products/
```

### Test 4: M-Pesa Callback Accessibility
```
URL: https://www.livegreat.co.ke/mpesa/callback/
Expected: Should be accessible (not redirected)
```

---

## 📊 **MONITORING & TROUBLESHOOTING**

### Check Render Logs
1. Go to **"Logs"** tab in Render dashboard
2. Look for these messages:

**✅ Good Log Messages:**
```
WWW redirect needed: livegreat.co.ke -> www.livegreat.co.ke
Skipping WWW redirect for exempt path: /mpesa/callback/
```

**❌ Bad Log Messages:**
```
DisallowedHost at /
Invalid HTTP_HOST header
```

### Common Issues & Solutions

**Issue 1: DisallowedHost Error**
- **Cause:** ALLOWED_HOSTS not updated correctly
- **Solution:** Double-check the ALLOWED_HOSTS value matches exactly

**Issue 2: M-Pesa Callbacks Failing**
- **Cause:** Callbacks being redirected
- **Solution:** Verify middleware exemptions are working

**Issue 3: Static Files Not Loading**
- **Cause:** Static files need collection
- **Solution:** Run `python manage.py collectstatic` in Render shell

---

## 🎯 **SUCCESS INDICATORS**

Your deployment is successful when:
- ✅ No DisallowedHost errors in logs
- ✅ Apex domain redirects to www subdomain
- ✅ WWW domain loads normally
- ✅ M-Pesa callbacks are accessible
- ✅ Static files load correctly
- ✅ Admin interface works

---

## 🆘 **NEED HELP?**

If you encounter issues:
1. **Check Render Logs** for specific error messages
2. **Verify Environment Variables** match exactly as specified
3. **Test Domain Resolution** using online tools
4. **Share error messages** for specific troubleshooting

---

## 📞 **NEXT STEPS AFTER UPDATE**

1. **Update environment variables** as specified above
2. **Wait for deployment** to complete
3. **Run verification tests** to confirm functionality
4. **Monitor logs** for any issues
5. **Test M-Pesa payment flow** end-to-end

**Ready to proceed? Start with Step 1 above! 🚀**
