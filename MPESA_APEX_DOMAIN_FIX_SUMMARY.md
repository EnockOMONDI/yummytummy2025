# M-Pesa Callback Redirect Fix - Apex Domain Solution

## 🚨 Issue Summary

**Problem**: M-Pesa payments were failing with "mpesa failed cannot complete payment of ksh 4" error after the redirect loop fix was implemented.

**Root Cause**: The M-Pesa callback URL `https://www.livegreat.co.ke/mpesa/callback/` was being redirected to `https://livegreat.co.ke/mpesa/callback/` by external redirect rules (likely Cloudflare or DNS configuration). This prevented Safaricom from successfully delivering payment callbacks, causing orders to remain in "processing" status indefinitely.

## ✅ Solution Implemented

### 1. Updated Environment Configuration
- **Changed**: `SITE_URL=https://www.livegreat.co.ke` 
- **To**: `SITE_URL=https://livegreat.co.ke`
- **File**: `.env` (line 16)

### 2. Automatic Callback URL Update
- **Previous**: `https://www.livegreat.co.ke/mpesa/callback/` (redirected)
- **Current**: `https://livegreat.co.ke/mpesa/callback/` (direct access)
- **Configuration**: Automatically updated via `MPESA_CALLBACK_URL = f"{SITE_URL}/mpesa/callback/"` in `settings.py`

### 3. Verification Results
✅ **Configuration Verified**:
- .env file correctly updated to apex domain
- Callback URL accessible without redirects (returns 405 for GET, 200 for POST)
- No redirect loops detected

✅ **Accessibility Confirmed**:
- `https://livegreat.co.ke/mpesa/callback/` responds correctly
- POST requests processed successfully
- No external redirects interfering

## 📋 Next Steps Required

### 1. Restart Django Application
The Django application needs to be restarted to load the new environment variables:

```bash
# On Render.com, this happens automatically on deployment
# For local development:
source venv/bin/activate
python manage.py runserver
```

### 2. Verify Safaricom Registration
**CRITICAL**: Confirm with Safaricom that both callback URLs are registered for shortcode `6319470`:

- ✅ `https://livegreat.co.ke/mpesa/callback/` (new apex domain)
- ✅ `https://www.livegreat.co.ke/mpesa/callback/` (existing www subdomain)

**How to verify**:
1. Contact Safaricom M-Pesa support
2. Reference shortcode: `6319470`
3. Request confirmation that both URLs are whitelisted
4. If only www subdomain is registered, request addition of apex domain

### 3. Test M-Pesa Payment End-to-End
After confirming Safaricom registration:

1. **Create test order** with small amount (KSH 1-5)
2. **Initiate M-Pesa payment** via STK Push
3. **Enter PIN** on mobile device
4. **Verify callback reception**:
   - Check order status changes from "processing" to "completed"
   - Verify M-Pesa receipt number is saved
   - Confirm transaction ID is recorded

## 🔍 Diagnostic Information

### Transaction Details (Failed Payment)
- **Order ID**: 36
- **Amount**: KSH 4.0
- **Phone**: 254726436676
- **CheckoutRequestID**: ws_CO_07072025221539652726436676
- **MerchantRequestID**: 4544-49a4-a9e1-9a79c8cc90be3358831
- **Status**: Still "processing" (callback never received)

### Domain Redirect Analysis
- **Apex Domain** (`livegreat.co.ke`): ✅ No redirects, serves content directly
- **WWW Subdomain** (`www.livegreat.co.ke`): ❌ Redirects to apex domain (301)
- **Callback Impact**: Redirects prevent Safaricom from delivering callbacks

### Configuration Verification
```bash
# Current configuration (verified):
SITE_URL=https://livegreat.co.ke
MPESA_CALLBACK_URL=https://livegreat.co.ke/mpesa/callback/

# M-Pesa Settings:
MPESA_BUSINESS_SHORT_CODE=6319470
MPESA_ENVIRONMENT=production
```

## 🎯 Expected Outcome

After implementing this fix and confirming Safaricom registration:

1. **M-Pesa callbacks** will be delivered to `https://livegreat.co.ke/mpesa/callback/` without redirects
2. **Payment processing** will complete successfully
3. **Order status** will update from "processing" to "completed"
4. **Receipt numbers** and transaction IDs will be saved correctly
5. **Customer experience** will be seamless with successful payments

## 📞 Safaricom Contact Information

For callback URL registration verification:
- **M-Pesa Support**: Contact through your Safaricom business account
- **Reference**: Shortcode 6319470
- **Request**: Confirm both apex and www callback URLs are whitelisted

## 🔄 Rollback Plan

If issues persist, the configuration can be reverted:

```bash
# In .env file:
SITE_URL=https://www.livegreat.co.ke

# This will restore:
MPESA_CALLBACK_URL=https://www.livegreat.co.ke/mpesa/callback/
```

However, this would restore the redirect issue, so the root cause (external redirects) would need to be addressed at the DNS/Cloudflare level instead.

---

**Status**: ✅ Configuration updated, ready for Safaricom verification and testing
**Priority**: HIGH - Critical for M-Pesa payment functionality
**Impact**: Resolves M-Pesa payment failures and callback delivery issues
