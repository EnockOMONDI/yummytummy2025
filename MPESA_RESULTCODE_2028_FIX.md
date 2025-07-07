# M-Pesa ResultCode 2028 Fix Documentation

## 🚨 **ISSUE SUMMARY**

**Error**: ResultCode 2028 - "The request is not permitted according to product assignment"  
**Root Cause**: Mismatch between shortcode type and TransactionType in STK Push requests  
**Solution**: Updated TransactionType from `CustomerPayBillOnline` to `CustomerBuyGoodsOnline`

---

## 🔍 **ROOT CAUSE ANALYSIS**

### **The Problem**
M-Pesa shortcodes are configured as either:
1. **Paybill Numbers** - For bill payments (require `CustomerPayBillOnline`)
2. **Till Numbers** - For goods/services (require `CustomerBuyGoodsOnline`)

### **Our Issue**
- **Shortcode**: 6319470 (**CONFIRMED** as a Till Number)
- **Previous Configuration**: `TransactionType: "CustomerPayBillOnline"`
- **Error**: Safaricom rejected requests due to product assignment mismatch

---

## 🛠️ **IMPLEMENTED SOLUTION**

### **1. Updated TransactionType**
**File**: `yummytummy_store/mpesa_service.py`
```python
# Before (causing error)
'TransactionType': 'CustomerPayBillOnline'

# After (fixed)
'TransactionType': getattr(settings, 'MPESA_TRANSACTION_TYPE', 'CustomerBuyGoodsOnline')
```

### **2. Added Configuration Setting**
**File**: `yummytummy_project/settings.py`
```python
# New configurable setting
MPESA_TRANSACTION_TYPE = config('MPESA_TRANSACTION_TYPE', default='CustomerBuyGoodsOnline')
```

### **3. Updated Environment Files**
**Files**: `.env.example`, `render.yaml`
```bash
# Added to environment configuration
MPESA_TRANSACTION_TYPE=CustomerBuyGoodsOnline
```

---

## 📋 **TRANSACTION TYPE GUIDE**

| Shortcode Type | TransactionType | Use Case | Customer Experience |
|----------------|-----------------|----------|-------------------|
| **Paybill Number** | `CustomerPayBillOnline` | Bill payments | Enter Paybill + Account Number |
| **Till Number** | `CustomerBuyGoodsOnline` | Goods/Services | Enter Till Number only |

### **Shortcode Type Verification**
✅ **CONFIRMED**: Shortcode 6319470 is a **Till Number**
- **Configuration**: `MPESA_TRANSACTION_TYPE=CustomerBuyGoodsOnline`
- **Customer Experience**: Customers enter Till Number only (no account number required)

---

## 🚀 **DEPLOYMENT STEPS**

### **1. Verify Local Configuration**
```bash
# Run verification script
python verify_mpesa_transaction_type_fix.py
```

### **2. Deploy to Render.com**
The `render.yaml` file now includes:
```yaml
- key: MPESA_TRANSACTION_TYPE
  value: "CustomerBuyGoodsOnline"
```

### **3. Test M-Pesa Payment**
1. Create a test order with small amount (KSH 1-10)
2. Complete STK Push process
3. Monitor logs for ResultCode 2028 resolution

---

## 🧪 **VERIFICATION CHECKLIST**

- [ ] ✅ Configuration includes `MPESA_TRANSACTION_TYPE`
- [ ] ✅ M-Pesa service uses configurable transaction type
- [ ] ✅ Environment files updated
- [ ] ✅ Render.yaml includes new setting
- [ ] 🔄 Deploy to production
- [ ] 🔄 Test M-Pesa payment
- [ ] 🔄 Verify ResultCode 2028 resolution

---

## 🔧 **TROUBLESHOOTING**

### **If Error Persists After Deployment**
1. **Verify Deployment**: Check Render.com environment variables
2. **Check Configuration**: Ensure `MPESA_TRANSACTION_TYPE=CustomerBuyGoodsOnline`
3. **Contact Safaricom**: Report any remaining issues with Till Number configuration

### **Common Issues**
- **Environment Variable Not Set**: Verify Render.com deployment
- **Wrong Shortcode Type**: Contact Safaricom for confirmation
- **Caching Issues**: Restart application after deployment

---

## 📞 **SAFARICOM SUPPORT CONTACT**

If you need to verify your shortcode configuration:

**Safaricom Developer Support**:
- Email: apisupport@safaricom.co.ke
- Portal: https://developer.safaricom.co.ke/
- Phone: +254 722 000 000

**Status**: ✅ **CONFIRMED** - Shortcode 6319470 is a Till Number
- **Correct Configuration**: `MPESA_TRANSACTION_TYPE=CustomerBuyGoodsOnline`
- **Product Assignment**: Till Number for goods/services payments

---

## 📈 **EXPECTED RESULTS**

### **Before Fix**
```json
{
  "ResultCode": 2028,
  "ResultDesc": "The request is not permitted according to product assignment"
}
```

### **After Fix**
```json
{
  "ResultCode": 0,
  "ResultDesc": "The service request is processed successfully",
  "CallbackMetadata": {
    "Item": [
      {"Name": "Amount", "Value": 1.00},
      {"Name": "MpesaReceiptNumber", "Value": "NLJ7RT61SV"},
      {"Name": "TransactionDate", "Value": 20250707102115},
      {"Name": "PhoneNumber", "Value": 254726436676}
    ]
  }
}
```

---

## 🎯 **SUCCESS CRITERIA**

1. ✅ No more ResultCode 2028 errors
2. ✅ STK Push completes successfully
3. ✅ Callback received with ResultCode 0
4. ✅ Order status updates to "completed"
5. ✅ M-Pesa receipt generated

---

**Last Updated**: 2025-07-07  
**Status**: Ready for Production Deployment
