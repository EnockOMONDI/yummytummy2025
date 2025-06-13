from django.urls import path
from . import views
from . import offline_views

app_name = 'yummytummy_store'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),

    # Product URLs
    path('products/', views.product_list, name='product_list'),
    path('products/<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),

    # Cart URLs
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/remove/<int:product_id>/', views.cart_remove, name='cart_remove'),

    # Cart URLs with cart key support (for variants)
    path('cart/update/<str:cart_key>/', views.cart_update, name='cart_update'),
    path('cart/remove-item/<str:cart_key>/', views.cart_remove_item, name='cart_remove_item'),

    # Coupon URLs
    path('coupon/apply/', views.coupon_apply, name='coupon_apply'),
    path('coupon/remove/', views.coupon_remove, name='coupon_remove'),

    # Checkout URLs
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/payment/', views.payment, name='payment'),
    path('checkout/confirmation/', views.order_confirmation, name='order_confirmation'),

    # Order Tracking and Authentication URLs
    path('first-login/<str:token>/', views.first_time_login, name='first_time_login'),
    path('account/dashboard/', views.order_tracking_dashboard, name='order_tracking_dashboard'),
    path('account/order/<int:order_id>/', views.order_detail_tracking, name='order_detail_tracking'),
    path('account/profile/', views.account_profile, name='account_profile'),

    # M-Pesa Integration URLs
    path('mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),
    path('mpesa/test-auth/', views.test_mpesa_auth, name='test_mpesa_auth'),

    # Admin Documentation URLs
    path('how-it-works/', views.how_it_works, name='how_it_works'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # Offline Order Management
    path('offline-orders/', offline_views.offline_orders_dashboard, name='offline_orders_dashboard'),
    path('offline-orders/login/', offline_views.sales_login, name='sales_login'),
    path('offline-orders/create/', offline_views.create_offline_order, name='create_offline_order'),
    path('offline-orders/success/<int:order_id>/', offline_views.offline_order_success, name='offline_order_success'),
    path('offline-orders/list/', offline_views.offline_orders_list, name='offline_orders_list'),
    path('api/products/<int:product_id>/variants/', offline_views.get_product_variants, name='get_product_variants'),

    # M-Pesa endpoints
    path('mpesa-callback/', views.mpesa_callback, name='mpesa_callback'),
    path('test-mpesa-auth/', views.test_mpesa_auth, name='test_mpesa_auth'),
]
