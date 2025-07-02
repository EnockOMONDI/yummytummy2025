--update user profile page to have features like affiliate, donate to kibra children, 
Instead of sending account created email, send them a welcome email with a link to track their order, and with account logins to view order status, do not inform them that they have an account, also in the /checkout/confirmation/ page after a successfull order creation in the section "Thank You for Your Order!
Your order has been received and is now being processed.

ive noticed that when an mpesa failed, the order is not cancelled, it still beign created and no email notification is sent also when payment fails the user should be asked to try again or their cart session kept, order should be created only after paynebt is confirmed  and account created

Order #MSL-000013 " add a button for track your order beside the Order number and replace the sentence "Your order has been received and is now being processed." with "Your order has been received and is now being processed. you can track the status of you order below " the track your order button should take them to the order tracking page with their order tracking number which can be copied and pasted to track their order its not a must they log in to track, but rememder they can also log in to view their order status and history 

-CSR page and link livegreat foundation activities
- add an inventory system
-ADD OTHER PAYMENT METHODS or update the trmplate to say not available at the moment 
- finish with recipes page gallery
-policy etc 
- the offline addmin should only be able to create orders and to view orders they created 
- make this to be the main landing page for admin admin-dashboard/
 remove the admin links for noemal users in the nav bar and change the django admin to superadmin (only templates) not the logic, views or anything
 i the http://127.0.0.1:8000/admin/yummytummy_store/order/ make the order list be clickable to the detail page http://127.0.0.1:8000/admin/yummytummy_store/order/12/change/ 



 #documentation how it works update 
 For Customers
✅ No Account Pressure: Can track orders without feeling forced to create accounts
✅ Easy Access: Simple order number + email tracking
✅ Multiple Options: Choose between guest tracking or account access
✅ Mobile Friendly: Track orders on any device
For Business
✅ Reduced Support: Customers can self-serve order tracking
✅ Better Experience: Professional, customer-focused communication
✅ Account Adoption: Subtle encouragement without pressure
✅ Brand Consistency: Professional appearance across all touchpoints
✅ Unified System: Same experience for online and offline orders


✅ Cart Preservation: SUCCESS
✅ Payment Retry Workflow: SUCCESS
✅ Model Structure Verification: SUCCESS
✅ All comprehensive tests: PASSED
🚀 Current Status
The M-Pesa payment failure handling system is now fully functional:

Email notifications for failed M-Pesa payments ✅
Cart preservation for payment retry attempts ✅
Automatic cart restoration during retry ✅
Checkout data preservation and restoration ✅
Payment retry URL with order restoration ✅
M-Pesa callback failure processing ✅