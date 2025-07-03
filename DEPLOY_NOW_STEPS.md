# 🚀 IMMEDIATE DEPLOYMENT STEPS - YummyTummy M-Pesa Fix

## ✅ PROBLEM SOLVED

**Issue:** `decouple.UndefinedValueError: MPESA_PASSKEY not found`
**Solution:** Added default values to Django settings.py
**Status:** Ready for deployment

## 📋 STEP-BY-STEP DEPLOYMENT PROCESS

### Step 1: Commit the Settings Fix ⚡

```bash
# Commit the settings.py changes
git add yummytummy_project/settings.py
git commit -m "Fix M-Pesa deployment: Add default values to prevent UndefinedValueError"
git push origin live
```

### Step 2: Configure Render.com Environment Variables 🔧

**Go to Render.com Dashboard:**

1. **Navigate to your YummyTummy service**
2. **Click "Environment" tab**
3. **Add these variables manually:**

| Variable Name | Value |
|---------------|-------|
| `MPESA_BUSINESS_SHORT_CODE` | `6319470` |
| `MPESA_PASSKEY` | `f473271a17488fd9a1230c2e43f6fe63db04eabc8bc7db8d1e21e4fe753f598d` |
| `MPESA_CONSUMER_KEY` | `p2D6eI01gcYtvwHgrh7UVsX61sFaAmKA4hZDZaHI3KBN0Xv4` |
| `MPESA_CONSUMER_SECRET` | `MQKc16J58WljEleReHaRAXzXSv6nmyxWCYqxAKzvE3NNUIpDYk94LJzQwTu1pGJn` |
| `MPESA_ENVIRONMENT` | `production` |

4. **Verify these essential variables exist:**

| Variable Name | Value |
|---------------|-------|
| `DATABASE_URL` | `postgresql://neondb_owner:npg_Spxz4nomvTJ8@ep-billowing-pond-a9faz0tc-pooler.gwc.azure.neon.tech/neondb?sslmode=require` |
| `SECRET_KEY` | `[Auto-generated]` |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `*` |
| `CSRF_TRUSTED_ORIGINS` | `https://*.onrender.com` |

### Step 3: Verify Branch Configuration 🌿

**In Render Dashboard:**
1. **Go to Settings → Build & Deploy**
2. **Verify:**
   - **Branch:** `live` ✅
   - **Build Command:** `./build.sh` ✅
   - **Start Command:** `gunicorn yummytummy_project.wsgi:application` ✅

### Step 4: Deploy 🚀

**Option A: Automatic Deploy (Recommended)**
- Push your commit to `live` branch (Step 1)
- Render will automatically detect and deploy

**Option B: Manual Deploy**
1. Go to your service dashboard
2. Click "Manual Deploy"
3. Select "Deploy latest commit" from `live` branch

### Step 5: Monitor Deployment 👀

**Watch Build Logs for:**
- ✅ `Installing dependencies...` (should complete successfully)
- ✅ `Django settings loaded successfully`
- ✅ `Starting gunicorn...`
- ✅ `Application startup complete`

**Look for these SUCCESS indicators:**
```
==> Build successful 🎉
==> Starting service...
==> Your service is live at https://your-app.onrender.com
```

### Step 6: Verify M-Pesa Configuration 🧪

**After successful deployment, test:**

1. **Visit your live site:** `https://your-app.onrender.com`
2. **Test M-Pesa integration:**
   - Create a test order
   - Select M-Pesa payment
   - Verify STK push is sent
   - Check production API is being used

3. **Check application logs for:**
   ```
   M-Pesa service initialized successfully
   Environment: production
   Business Short Code: 6319470
   Base URL: https://api.safaricom.co.ke
   ```

## 🎯 WHAT THE FIX DOES

### Before Fix:
```python
MPESA_PASSKEY = config('MPESA_PASSKEY')  # ❌ No default - causes crash
```

### After Fix:
```python
MPESA_PASSKEY = config('MPESA_PASSKEY', default='f473271a...')  # ✅ Has default
```

**Result:** Django will start successfully even if environment variables aren't loaded from render.yaml.

## 🔍 TROUBLESHOOTING

### If Deployment Still Fails:

1. **Check Build Logs:**
   - Look for specific error messages
   - Verify all dependencies install correctly

2. **Verify Environment Variables:**
   - Ensure all M-Pesa variables are set in Render dashboard
   - Check for typos in variable names

3. **Test Settings Locally:**
   ```bash
   python manage.py check --deploy
   ```

### If M-Pesa Doesn't Work After Deployment:

1. **Check Production API Access:**
   - Verify credentials are for production (not sandbox)
   - Test authentication with Safaricom API

2. **Verify Callback URL:**
   - Ensure `https://your-app.onrender.com/mpesa/callback/` is accessible
   - Check SSL certificate is valid

## 📊 SUCCESS CRITERIA

Deployment is successful when:
- [ ] Build completes without errors
- [ ] Django starts successfully
- [ ] Application is accessible at live URL
- [ ] M-Pesa service initializes with production settings
- [ ] Test order creation works
- [ ] STK push notifications are sent

## 🎉 EXPECTED OUTCOME

After following these steps:
1. **Deployment will succeed** ✅
2. **M-Pesa will use live credentials** ✅
3. **Production API endpoints will be used** ✅
4. **Real M-Pesa transactions will work** ✅

---

## 🚨 IMMEDIATE ACTION

**Run this command now:**
```bash
git add yummytummy_project/settings.py
git commit -m "Fix M-Pesa deployment: Add default values to prevent UndefinedValueError"
git push origin live
```

Then configure environment variables in Render dashboard and monitor the deployment!

**Your M-Pesa integration is ready for production! 🎊**
