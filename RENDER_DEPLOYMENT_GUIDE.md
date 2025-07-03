# YummyTummy M-Pesa Live Deployment Guide for Render.com

## 🚨 CRITICAL ISSUE IDENTIFIED

**Problem:** Your render.yaml was configured to deploy from `yummymain` branch, but you're using `yummy2` branch.

**Solution:** Updated render.yaml to use `yummy2` branch and live M-Pesa credentials.

## 📋 STEP-BY-STEP DEPLOYMENT SOLUTION

### Step 1: Update M-Pesa Credentials in render.yaml

I've updated your `render.yaml` file with the correct configuration. You need to replace the placeholder values with your actual live Safaricom credentials:

```yaml
# M-Pesa Configuration (Live Safaricom Credentials)
- key: MPESA_BUSINESS_SHORT_CODE
  value: "6319470"  # ✅ Already updated
- key: MPESA_PASSKEY
  value: "YOUR_LIVE_MPESA_PASSKEY_HERE"  # ❌ REPLACE WITH ACTUAL VALUE
- key: MPESA_CONSUMER_KEY
  value: "YOUR_LIVE_MPESA_CONSUMER_KEY_HERE"  # ❌ REPLACE WITH ACTUAL VALUE
- key: MPESA_CONSUMER_SECRET
  value: "YOUR_LIVE_MPESA_CONSUMER_SECRET_HERE"  # ❌ REPLACE WITH ACTUAL VALUE
- key: MPESA_ENVIRONMENT
  value: "production"  # ✅ Set to production
```

### Step 2: Required M-Pesa Environment Variables

**All Required Variables (must be set in Render.com):**

1. **MPESA_BUSINESS_SHORT_CODE** = `6319470` ✅
2. **MPESA_PASSKEY** = Your live Safaricom passkey ❌
3. **MPESA_CONSUMER_KEY** = Your live Safaricom consumer key ❌
4. **MPESA_CONSUMER_SECRET** = Your live Safaricom consumer secret ❌
5. **MPESA_ENVIRONMENT** = `production` ✅

### Step 3: Setting Environment Variables in Render.com Dashboard

**Option A: Update render.yaml (Recommended)**
1. Replace the placeholder values in `render.yaml` with your actual credentials
2. Commit and push to `yummy2` branch
3. Render will automatically redeploy

**Option B: Manual Dashboard Configuration**
1. Go to your Render.com dashboard
2. Select your YummyTummy service
3. Go to "Environment" tab
4. Add/Update these variables:
   - `MPESA_PASSKEY` = [Your live passkey]
   - `MPESA_CONSUMER_KEY` = [Your live consumer key]
   - `MPESA_CONSUMER_SECRET` = [Your live consumer secret]
   - `MPESA_ENVIRONMENT` = `production`
   - `MPESA_BUSINESS_SHORT_CODE` = `6319470`

### Step 4: Verify Branch Configuration

**Current Issue:** render.yaml was set to `yummymain` branch
**Solution:** Updated to `yummy2` branch

Verify in Render dashboard:
1. Go to Settings → Build & Deploy
2. Ensure "Branch" is set to `yummy2`
3. If not, change it manually

### Step 5: Complete Deployment Checklist

**Before Deployment:**
- [ ] Update M-Pesa credentials in render.yaml
- [ ] Verify branch is set to `yummy2`
- [ ] Commit all changes to `yummy2` branch
- [ ] Push to GitHub

**During Deployment:**
- [ ] Monitor build logs for M-Pesa variable errors
- [ ] Check that all environment variables are loaded
- [ ] Verify Django starts without UndefinedValueError

**After Deployment:**
- [ ] Test M-Pesa payment flow
- [ ] Verify callback URL is accessible
- [ ] Test order creation and tracking
- [ ] Verify email notifications work

## 🔧 IMMEDIATE ACTION REQUIRED

### 1. Update render.yaml with Live Credentials

Replace these lines in `render.yaml`:

```yaml
- key: MPESA_PASSKEY
  value: "YOUR_ACTUAL_LIVE_PASSKEY_FROM_SAFARICOM"
- key: MPESA_CONSUMER_KEY
  value: "YOUR_ACTUAL_LIVE_CONSUMER_KEY_FROM_SAFARICOM"
- key: MPESA_CONSUMER_SECRET
  value: "YOUR_ACTUAL_LIVE_CONSUMER_SECRET_FROM_SAFARICOM"
```

### 2. Commit and Deploy

```bash
git add render.yaml
git commit -m "Update M-Pesa live credentials and fix branch configuration"
git push origin yummy2
```

### 3. Monitor Deployment

Watch the build logs in Render dashboard for:
- ✅ All environment variables loaded successfully
- ✅ Django starts without errors
- ✅ M-Pesa service initializes correctly

## 🚨 SECURITY CONSIDERATIONS

### Production M-Pesa Settings

**Environment:** `production`
**Base URL:** `https://api.safaricom.co.ke`
**Callback URL:** Will use your live domain (not localhost)

### Callback URL Configuration

The system automatically configures callback URLs:
- **Development:** Uses webhook.site placeholder
- **Production:** Uses your live domain + `/mpesa/callback/`

Example production callback: `https://your-app.onrender.com/mpesa/callback/`

## 🧪 POST-DEPLOYMENT TESTING

### 1. Test M-Pesa Integration

```bash
# Test order creation
curl -X POST https://your-app.onrender.com/checkout/payment/ \
  -H "Content-Type: application/json" \
  -d '{"payment_method": "mpesa", "mpesa_phone": "254712345678"}'
```

### 2. Verify Environment Variables

Check Django admin or logs to confirm:
- M-Pesa service initializes with live credentials
- Business short code is 6319470
- Environment is set to production

### 3. Test Payment Flow

1. Create test order
2. Initiate M-Pesa payment
3. Verify STK push is sent
4. Check callback handling
5. Confirm order status updates

## 📞 TROUBLESHOOTING

### Common Issues:

**1. UndefinedValueError: MPESA_PASSKEY not found**
- Solution: Update render.yaml with actual passkey value

**2. Wrong branch deployed**
- Solution: Change branch to `yummy2` in Render dashboard

**3. M-Pesa API errors**
- Check credentials are for production environment
- Verify business short code is correct
- Ensure callback URL is accessible

**4. SSL/HTTPS issues**
- Render automatically provides HTTPS
- Verify CSRF_TRUSTED_ORIGINS includes your domain

## 🎯 SUCCESS CRITERIA

Deployment is successful when:
- [ ] Django starts without environment variable errors
- [ ] M-Pesa service initializes with live credentials
- [ ] Payment flow works end-to-end
- [ ] Callback URL receives M-Pesa responses
- [ ] Order tracking and emails function correctly

## 📧 SUPPORT

If you encounter issues:
1. Check Render build logs for specific errors
2. Verify all M-Pesa credentials are correct
3. Test with small amounts first (KSh 1-10)
4. Monitor Django logs for M-Pesa API responses

---

**Next Steps:** Replace the placeholder M-Pesa credentials in render.yaml with your actual live Safaricom values, then commit and push to trigger redeployment.
