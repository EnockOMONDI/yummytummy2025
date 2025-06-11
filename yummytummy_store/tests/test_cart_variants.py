"""
Comprehensive test suite for cart variant functionality.
Tests all aspects of variant-aware cart operations.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal
from yummytummy_store.models import Category, Product, ProductVariant, Order, OrderItem
from yummytummy_store.forms import CartAddProductForm


class CartVariantTestCase(TestCase):
    """Test case for cart variant functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test category
        self.category = Category.objects.create(
            name="Test Honey",
            slug="test-honey"
        )
        
        # Create test product
        self.product = Product.objects.create(
            name="Premium Honey",
            slug="premium-honey",
            description="Test honey product",
            price=Decimal('1200.00'),
            category=self.category,
            is_available=True,
            is_featured=True
        )
        
        # Create test variants
        self.variant_250g = ProductVariant.objects.create(
            product=self.product,
            name="250g",
            additional_price=Decimal('0.00')
        )
        
        self.variant_500g = ProductVariant.objects.create(
            product=self.product,
            name="500g", 
            additional_price=Decimal('200.00')
        )
        
        self.variant_1kg = ProductVariant.objects.create(
            product=self.product,
            name="1kg",
            additional_price=Decimal('500.00')
        )
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_cart_add_base_product(self):
        """Test adding base product to cart"""
        response = self.client.post(reverse('yummytummy_store:cart_add', args=[self.product.id]), {
            'quantity': 1,
            'update': False,
            'selected_variant': 'base'
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect to cart
        
        # Check session cart
        session = self.client.session
        cart = session.get('cart', {})
        
        # Should have base product with key "4_base"
        base_key = f"{self.product.id}_base"
        self.assertIn(base_key, cart)
        
        cart_item = cart[base_key]
        self.assertEqual(cart_item['product_id'], self.product.id)
        self.assertEqual(cart_item['variant_id'], None)
        self.assertEqual(cart_item['quantity'], 1)
        self.assertEqual(Decimal(cart_item['price']), self.product.price)
        self.assertEqual(cart_item['name'], self.product.name)

    def test_cart_add_variant_product(self):
        """Test adding variant product to cart"""
        response = self.client.post(reverse('yummytummy_store:cart_add', args=[self.product.id]), {
            'quantity': 2,
            'update': False,
            'selected_variant': str(self.variant_500g.id)
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Check session cart
        session = self.client.session
        cart = session.get('cart', {})
        
        # Should have variant with key "4_variant_X"
        variant_key = f"{self.product.id}_variant_{self.variant_500g.id}"
        self.assertIn(variant_key, cart)
        
        cart_item = cart[variant_key]
        self.assertEqual(cart_item['product_id'], self.product.id)
        self.assertEqual(cart_item['variant_id'], self.variant_500g.id)
        self.assertEqual(cart_item['quantity'], 2)
        
        # Check calculated price (base + additional)
        expected_price = self.product.price + self.variant_500g.additional_price
        self.assertEqual(Decimal(cart_item['price']), expected_price)
        
        # Check variant name
        expected_name = f"{self.product.name} - {self.variant_500g.name}"
        self.assertEqual(cart_item['name'], expected_name)

    def test_cart_add_multiple_variants(self):
        """Test adding multiple variants of same product"""
        # Add base product
        self.client.post(reverse('yummytummy_store:cart_add', args=[self.product.id]), {
            'quantity': 1,
            'update': False,
            'selected_variant': 'base'
        })
        
        # Add 500g variant
        self.client.post(reverse('yummytummy_store:cart_add', args=[self.product.id]), {
            'quantity': 2,
            'update': False,
            'selected_variant': str(self.variant_500g.id)
        })
        
        # Add 1kg variant
        self.client.post(reverse('yummytummy_store:cart_add', args=[self.product.id]), {
            'quantity': 1,
            'update': False,
            'selected_variant': str(self.variant_1kg.id)
        })
        
        # Check session cart
        session = self.client.session
        cart = session.get('cart', {})
        
        # Should have 3 separate cart items
        self.assertEqual(len(cart), 3)
        
        # Check each cart key exists
        base_key = f"{self.product.id}_base"
        variant_500g_key = f"{self.product.id}_variant_{self.variant_500g.id}"
        variant_1kg_key = f"{self.product.id}_variant_{self.variant_1kg.id}"
        
        self.assertIn(base_key, cart)
        self.assertIn(variant_500g_key, cart)
        self.assertIn(variant_1kg_key, cart)

    def test_cart_update_variant_quantity(self):
        """Test updating quantity of specific variant"""
        # Add variant to cart
        self.client.post(reverse('yummytummy_store:cart_add', args=[self.product.id]), {
            'quantity': 1,
            'update': False,
            'selected_variant': str(self.variant_500g.id)
        })
        
        # Update quantity
        variant_key = f"{self.product.id}_variant_{self.variant_500g.id}"
        response = self.client.post(reverse('yummytummy_store:cart_update', args=[variant_key]), {
            'quantity': 3,
            'update': True
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Check updated quantity
        session = self.client.session
        cart = session.get('cart', {})
        
        self.assertEqual(cart[variant_key]['quantity'], 3)

    def test_cart_remove_specific_variant(self):
        """Test removing specific variant from cart"""
        # Add multiple variants
        self.client.post(reverse('yummytummy_store:cart_add', args=[self.product.id]), {
            'quantity': 1,
            'update': False,
            'selected_variant': 'base'
        })
        
        self.client.post(reverse('yummytummy_store:cart_add', args=[self.product.id]), {
            'quantity': 1,
            'update': False,
            'selected_variant': str(self.variant_500g.id)
        })
        
        # Remove specific variant
        variant_key = f"{self.product.id}_variant_{self.variant_500g.id}"
        response = self.client.get(reverse('yummytummy_store:cart_remove_item', args=[variant_key]))
        
        self.assertEqual(response.status_code, 302)
        
        # Check cart
        session = self.client.session
        cart = session.get('cart', {})
        
        # Should only have base product left
        self.assertEqual(len(cart), 1)
        base_key = f"{self.product.id}_base"
        self.assertIn(base_key, cart)
        self.assertNotIn(variant_key, cart)

    def test_cart_detail_view_with_variants(self):
        """Test cart detail view displays variants correctly"""
        # Add variants to cart
        self.client.post(reverse('yummytummy_store:cart_add', args=[self.product.id]), {
            'quantity': 1,
            'update': False,
            'selected_variant': 'base'
        })
        
        self.client.post(reverse('yummytummy_store:cart_add', args=[self.product.id]), {
            'quantity': 2,
            'update': False,
            'selected_variant': str(self.variant_500g.id)
        })
        
        # Get cart detail view
        response = self.client.get(reverse('yummytummy_store:cart_detail'))
        
        self.assertEqual(response.status_code, 200)
        
        # Check context
        cart_items = response.context['cart_items']
        self.assertEqual(len(cart_items), 2)
        
        # Check cart items have correct cart_key
        cart_keys = [item['cart_key'] for item in cart_items]
        base_key = f"{self.product.id}_base"
        variant_key = f"{self.product.id}_variant_{self.variant_500g.id}"
        
        self.assertIn(base_key, cart_keys)
        self.assertIn(variant_key, cart_keys)

    def test_cart_form_validation(self):
        """Test cart form validation"""
        # Test valid form
        form = CartAddProductForm({
            'quantity': 1,
            'update': False,
            'selected_variant': 'base'
        })
        self.assertTrue(form.is_valid())
        
        # Test invalid quantity
        form = CartAddProductForm({
            'quantity': 0,
            'update': False,
            'selected_variant': 'base'
        })
        self.assertFalse(form.is_valid())
        
        # Test missing quantity
        form = CartAddProductForm({
            'update': False,
            'selected_variant': 'base'
        })
        self.assertFalse(form.is_valid())

    def test_variant_price_calculation(self):
        """Test variant price calculation"""
        # Test base product price
        self.assertEqual(self.product.price, Decimal('1200.00'))
        
        # Test variant calculated prices
        self.assertEqual(self.variant_250g.calculated_price, Decimal('1200.00'))
        self.assertEqual(self.variant_500g.calculated_price, Decimal('1400.00'))
        self.assertEqual(self.variant_1kg.calculated_price, Decimal('1700.00'))

    def test_cart_key_generation(self):
        """Test cart key generation logic"""
        # Test base product key
        base_key = f"{self.product.id}_base"
        
        # Test variant keys
        variant_250g_key = f"{self.product.id}_variant_{self.variant_250g.id}"
        variant_500g_key = f"{self.product.id}_variant_{self.variant_500g.id}"
        variant_1kg_key = f"{self.product.id}_variant_{self.variant_1kg.id}"
        
        # Verify keys are unique
        keys = [base_key, variant_250g_key, variant_500g_key, variant_1kg_key]
        self.assertEqual(len(keys), len(set(keys)))  # All keys should be unique

    def test_invalid_variant_fallback(self):
        """Test fallback to base product when invalid variant is selected"""
        response = self.client.post(reverse('yummytummy_store:cart_add', args=[self.product.id]), {
            'quantity': 1,
            'update': False,
            'selected_variant': '999'  # Non-existent variant ID
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Should fallback to base product
        session = self.client.session
        cart = session.get('cart', {})
        
        base_key = f"{self.product.id}_base"
        self.assertIn(base_key, cart)
        
        cart_item = cart[base_key]
        self.assertEqual(cart_item['variant_id'], None)
        self.assertEqual(Decimal(cart_item['price']), self.product.price)
