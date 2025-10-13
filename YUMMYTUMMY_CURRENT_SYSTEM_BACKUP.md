# YummyTummy Current System Architecture - BACKUP DOCUMENTATION

**Created**: 2025-10-13  
**Purpose**: Complete backup documentation before Recipe integration to ensure no existing functionality is broken

## 🔄 Current Cart & Checkout Flow

### 1. Cart Session Structure
```python
# Current cart session format
request.session['cart'] = {
    'product_id_base': {
        'product_id': int,
        'variant_id': None,
        'quantity': int,
        'price': str,
        'name': str,
        'variant_name': None
    },
    'product_id_variant_X': {
        'product_id': int,
        'variant_id': int,
        'quantity': int,
        'price': str,
        'name': str,
        'variant_name': str
    }
}
```

### 2. Cart Operations (views.py)
- **cart_add(product_id)**: Adds products with variant support
- **cart_remove(product_id)**: Removes all variants of a product
- **cart_update(cart_key)**: Updates quantity for specific cart item
- **cart_remove_item(cart_key)**: Removes specific cart item
- **cart_detail()**: Displays cart contents

### 3. Checkout Process Flow
1. **checkout()** - Shipping address form
   - Validates cart not empty
   - Calculates totals with coupon support
   - Stores checkout_data in session
   
2. **payment()** - Payment method selection
   - Auto-creates user accounts for new customers
   - Creates Order with pending status
   - Creates OrderItems from cart
   - Initiates M-Pesa STK Push for mpesa payments
   - Clears cart on success

3. **confirmation()** - Order confirmation page
   - Shows order details
   - Provides tracking links

### 4. M-Pesa Integration
- **MPesaService**: Handles STK Push and callbacks
- **mpesa_callback()**: Processes payment confirmations
- **Order Model**: Tracks mpesa_checkout_request_id
- **Payment Flow**: pending → paid → confirmed

### 5. Email System (OrderTrackingEmailService)
- **Auto Account Creation**: Creates accounts for new customers
- **Order Confirmation**: Sends welcome emails with login details
- **Status Updates**: Notifies on order status changes
- **Templates**: 
  - order_confirmation_with_account.html
  - order_confirmation_guest.html
  - payment_confirmation_with_account.html

## 📊 Current Models

### Order Model
```python
class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    # Customer details
    first_name, last_name, email, phone
    address, area, estate, building, landmark
    # Payment
    payment_method, payment_status, mpesa_phone, mpesa_checkout_request_id
    # Amounts
    subtotal_amount, discount_amount, total_amount
    # Tracking
    created, updated, auto_created_account
```

### OrderItem Model
```python
class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items')
    product = models.ForeignKey(Product)
    variant = models.ForeignKey(ProductVariant, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField()  # Price at time of purchase
```

## 🎯 Critical Integration Points

### 1. Cart Session Compatibility
- Must preserve existing product cart structure
- Add recipe support without breaking product functionality
- Maintain cart_key format for products

### 2. Checkout Form Logic
- Current CheckoutForm requires full address
- Need conditional form for recipe-only orders
- Preserve existing validation

### 3. Order Creation Process
- Must create both OrderItems (products) and RecipePurchase (recipes)
- Maintain existing M-Pesa flow
- Preserve auto-account creation

### 4. Email Integration
- Extend existing email templates
- Add recipe download links
- Maintain current email service patterns

### 5. M-Pesa Callback
- Must handle mixed product/recipe orders
- Create RecipePurchase records on payment success
- Preserve existing callback logic

## 🔒 Critical Preservation Requirements

### 1. Existing URLs Must Work
- All current cart URLs must remain functional
- Product checkout flow unchanged
- M-Pesa callback URL unchanged

### 2. Database Integrity
- No changes to existing Order/OrderItem models
- RecipePurchase as separate model
- Maintain foreign key relationships

### 3. Session Management
- Preserve cart session structure
- Maintain coupon functionality
- Keep existing cart operations

### 4. Email Templates
- Extend, don't replace existing templates
- Maintain current email service methods
- Preserve auto-account creation flow

## 🧪 Testing Requirements

### Before Implementation
1. Test current product checkout flow
2. Verify M-Pesa integration works
3. Confirm email notifications send
4. Validate cart operations

### After Implementation
1. Test product-only orders (unchanged)
2. Test recipe-only orders (new)
3. Test mixed product+recipe orders (new)
4. Verify M-Pesa works for all scenarios
5. Confirm emails include recipes
6. Validate no regressions in existing functionality

## 📁 Key Files to Modify Carefully

### High Risk (Core Functionality)
- `yummytummy_store/views.py` - checkout(), payment(), mpesa_callback()
- `yummytummy_store/templates/yummytummy_store/cart/detail.html`
- `yummytummy_store/services.py` - OrderTrackingEmailService

### Medium Risk (Extensions)
- Email templates (extend existing)
- Checkout forms (conditional logic)
- Cart display logic

### Low Risk (New Features)
- Recipe PDF generation
- Recipe email templates
- Recipe-specific views

## 🚨 Red Flags to Avoid

1. **Don't modify existing Order/OrderItem models**
2. **Don't change cart session structure for products**
3. **Don't alter M-Pesa callback signature**
4. **Don't break existing email service methods**
5. **Don't modify existing URL patterns**
6. **Don't change existing form validation**

## ✅ Safe Implementation Strategy

1. **Add, don't modify** - Extend existing functionality
2. **Conditional logic** - Check for recipes vs products
3. **Separate models** - RecipePurchase independent of OrderItem
4. **Template inheritance** - Extend existing email templates
5. **Backward compatibility** - All existing flows must work unchanged

This documentation serves as a safety net to ensure the Recipe integration doesn't break any existing YummyTummy functionality.
