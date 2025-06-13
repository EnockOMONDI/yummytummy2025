#!/usr/bin/env python3
"""
Quick test for order creation functionality
"""

import os
import sys
import django
import json

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yummytummy_project.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User, Group
from yummytummy_store.models import Product, Order, OrderTrackingStatus

def test_order_creation():
    """Test order creation with proper debugging"""
    client = Client()
    
    # Login as sales user
    sales_user = User.objects.get(username='sales_demo')
    client.force_login(sales_user)
    
    # Get first product
    product = Product.objects.first()
    print(f"Testing with product: {product.name} (ID: {product.id}, Price: {product.price})")
    
    # Test order data
    order_data = {
        'customer_type': 'individual',
        'first_name': 'Test',
        'last_name': 'Customer',
        'email': 'test@example.com',
        'phone': '0712345678',
        'delivery_address': '123 Test Street',
        'delivery_city': 'Nairobi',
        'delivery_county': 'Nairobi',
        'order_items': json.dumps([{
            'product_id': product.id,
            'variant_id': None,
            'quantity': 1,
            'price': float(product.price)
        }])
    }
    
    print("Order data:", order_data)
    
    # Submit order
    response = client.post('/offline-orders/create/', order_data)
    print(f"Response status: {response.status_code}")

    if response.status_code == 302:
        print("Order creation successful - redirected to success page")
        print(f"Redirect location: {response.get('Location', 'No location header')}")

        # Check if order was created
        order = Order.objects.filter(email='test@example.com').first()
        if order:
            print(f"Order found: {order.get_order_number()}")
            print(f"Order total: {order.total_amount}")
            print(f"Created by: {order.created_by}")

            # Check tracking status
            status = order.tracking_statuses.first()
            if status:
                print(f"Initial status: {status.status}")
            else:
                print("No tracking status found")
        else:
            print("Order not found in database")
            print(f"Total orders in database: {Order.objects.count()}")
            print("All orders:", list(Order.objects.values('id', 'email', 'created_by')))
    else:
        print("Order creation failed")
        if hasattr(response, 'content'):
            print("Response content:", response.content.decode()[:1000])

if __name__ == "__main__":
    test_order_creation()
