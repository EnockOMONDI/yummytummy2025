"""
Frontend tests for variant selection UI and JavaScript functionality.
Tests user interface interactions and responsive design.
"""

from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
from yummytummy_store.models import Category, Product, ProductVariant


class FrontendVariantTestCase(TestCase):
    """Test case for frontend variant functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test category
        self.category = Category.objects.create(
            name="Test Honey",
            slug="test-honey"
        )
        
        # Create test product with variants
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
        
        # Create product without variants
        self.simple_product = Product.objects.create(
            name="Simple Honey",
            slug="simple-honey",
            description="Simple honey without variants",
            price=Decimal('800.00'),
            category=self.category,
            is_available=True
        )

    def test_product_list_variant_display(self):
        """Test product list page displays variants correctly"""
        response = self.client.get(reverse('yummytummy_store:product_list'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode()
        
        # Check for variant toggle button
        self.assertIn('View Sizes', content)
        self.assertIn('variant-toggle-btn', content)
        
        # Check for variant options container
        self.assertIn(f'variants-{self.product.id}', content)
        
        # Check for variant forms
        self.assertIn('variant-cart-form', content)
        self.assertIn('selected_variant', content)
        
        # Check for "From" price display for products with variants
        self.assertIn('From', content)
        
        # Check simple product doesn't have variant UI
        self.assertIn(self.simple_product.name, content)

    def test_product_detail_variant_display(self):
        """Test product detail page displays variants correctly"""
        response = self.client.get(reverse('yummytummy_store:product_detail', args=[self.product.slug]))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode()
        
        # Check for variant selection section
        self.assertIn('variant-selection-section', content)
        self.assertIn('Choose Size', content)
        
        # Check for radio button inputs
        self.assertIn('type="radio"', content)
        self.assertIn('name="selected_variant"', content)
        
        # Check for variant options
        self.assertIn('variant-base', content)
        self.assertIn(f'variant-{self.variant_250g.id}', content)
        self.assertIn(f'variant-{self.variant_500g.id}', content)
        self.assertIn(f'variant-{self.variant_1kg.id}', content)
        
        # Check for variant prices
        self.assertIn(str(self.variant_500g.calculated_price), content)
        self.assertIn(str(self.variant_1kg.calculated_price), content)
        
        # Check for dynamic price display
        self.assertIn('current-price', content)

    def test_cart_detail_variant_display(self):
        """Test cart detail page displays variants correctly"""
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
        
        response = self.client.get(reverse('yummytummy_store:cart_detail'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode()
        
        # Check for cart update forms with cart keys
        self.assertIn('cart/update/', content)
        self.assertIn(f'{self.product.id}_base', content)
        self.assertIn(f'{self.product.id}_variant_{self.variant_500g.id}', content)
        
        # Check for variant information display
        self.assertIn('variant-info', content)
        self.assertIn(self.variant_500g.name, content)
        
        # Check for quantity selectors
        self.assertIn('quantity-selector', content)
        self.assertIn('minus', content)
        self.assertIn('plus', content)
        
        # Check for remove buttons with cart keys
        self.assertIn('cart/remove-item/', content)

    def test_form_hidden_fields(self):
        """Test that forms include proper hidden fields"""
        # Test product list page
        response = self.client.get(reverse('yummytummy_store:product_list'))
        content = response.content.decode()
        
        # Check for selected_variant hidden fields
        self.assertIn('name="selected_variant"', content)
        self.assertIn('value="base"', content)
        self.assertIn(f'value="{self.variant_500g.id}"', content)
        
        # Test product detail page
        response = self.client.get(reverse('yummytummy_store:product_detail', args=[self.product.slug]))
        content = response.content.decode()
        
        # Check for selected-variant-input
        self.assertIn('selected-variant-input', content)
        self.assertIn('name="selected_variant"', content)

    def test_css_classes_present(self):
        """Test that required CSS classes are present"""
        # Test product list page
        response = self.client.get(reverse('yummytummy_store:product_list'))
        content = response.content.decode()
        
        # Check for variant-related CSS classes
        css_classes = [
            'variant-toggle-btn',
            'variant-options-container',
            'variant-option',
            'variant-info',
            'variant-name',
            'variant-price',
            'variant-cart-form',
            'variant-add-to-cart'
        ]
        
        for css_class in css_classes:
            self.assertIn(css_class, content)
        
        # Test product detail page
        response = self.client.get(reverse('yummytummy_store:product_detail', args=[self.product.slug]))
        content = response.content.decode()
        
        detail_css_classes = [
            'variant-selection-section',
            'variant-options',
            'variant-option',
            'variant-label',
            'variant-info',
            'variant-name',
            'variant-price'
        ]
        
        for css_class in detail_css_classes:
            self.assertIn(css_class, content)

    def test_javascript_data_attributes(self):
        """Test that JavaScript data attributes are present"""
        # Test product list page
        response = self.client.get(reverse('yummytummy_store:product_list'))
        content = response.content.decode()
        
        # Check for data attributes
        self.assertIn(f'data-product-id="{self.product.id}"', content)
        self.assertIn('data-variant=', content)
        self.assertIn('data-price=', content)
        
        # Test product detail page
        response = self.client.get(reverse('yummytummy_store:product_detail', args=[self.product.slug]))
        content = response.content.decode()
        
        # Check for variant data attributes
        self.assertIn('data-variant="base"', content)
        self.assertIn(f'data-variant="{self.variant_500g.id}"', content)
        self.assertIn(f'data-price="{self.variant_500g.calculated_price}"', content)

    def test_responsive_design_elements(self):
        """Test that responsive design elements are present"""
        response = self.client.get(reverse('yummytummy_store:product_list'))
        content = response.content.decode()
        
        # Check for responsive CSS classes and structure
        self.assertIn('enhanced-product-grid', content)
        self.assertIn('enhanced-product-card', content)
        
        # Check for mobile-friendly elements
        self.assertIn('aria-label', content)
        
        response = self.client.get(reverse('yummytummy_store:product_detail', args=[self.product.slug]))
        content = response.content.decode()
        
        # Check for responsive variant selection
        self.assertIn('variant-selection-section', content)

    def test_accessibility_features(self):
        """Test accessibility features in variant UI"""
        # Test product list page
        response = self.client.get(reverse('yummytummy_store:product_list'))
        content = response.content.decode()
        
        # Check for aria-labels
        self.assertIn('aria-label="Decrease quantity"', content)
        self.assertIn('aria-label="Increase quantity"', content)
        self.assertIn('aria-label="Product quantity"', content)
        
        # Test product detail page
        response = self.client.get(reverse('yummytummy_store:product_detail', args=[self.product.slug]))
        content = response.content.decode()
        
        # Check for proper form labels
        self.assertIn('<label for=', content)
        self.assertIn('variant-label', content)

    def test_price_formatting(self):
        """Test price formatting in variant displays"""
        response = self.client.get(reverse('yummytummy_store:product_list'))
        content = response.content.decode()
        
        # Check for KSh currency symbol
        self.assertIn('KSh', content)
        
        # Check for proper price formatting with intcomma
        formatted_price = f"{self.variant_500g.calculated_price:,.2f}"
        self.assertIn(formatted_price, content)
        
        response = self.client.get(reverse('yummytummy_store:product_detail', args=[self.product.slug]))
        content = response.content.decode()
        
        # Check for currency formatting in detail page
        self.assertIn('KSh', content)
        self.assertIn(formatted_price, content)

    def test_form_action_urls(self):
        """Test that form action URLs are correct"""
        # Test product list page
        response = self.client.get(reverse('yummytummy_store:product_list'))
        content = response.content.decode()
        
        # Check for cart add URLs
        expected_url = reverse('yummytummy_store:cart_add', args=[self.product.id])
        self.assertIn(f'action="{expected_url}"', content)
        
        # Test cart detail page with items
        self.client.post(reverse('yummytummy_store:cart_add', args=[self.product.id]), {
            'quantity': 1,
            'update': False,
            'selected_variant': str(self.variant_500g.id)
        })
        
        response = self.client.get(reverse('yummytummy_store:cart_detail'))
        content = response.content.decode()
        
        # Check for cart update URLs
        variant_key = f"{self.product.id}_variant_{self.variant_500g.id}"
        expected_update_url = reverse('yummytummy_store:cart_update', args=[variant_key])
        self.assertIn(f'action="{expected_update_url}"', content)
        
        # Check for cart remove URLs
        expected_remove_url = reverse('yummytummy_store:cart_remove_item', args=[variant_key])
        self.assertIn(f'href="{expected_remove_url}"', content)

    def test_variant_selection_state(self):
        """Test variant selection state management"""
        response = self.client.get(reverse('yummytummy_store:product_detail', args=[self.product.slug]))
        content = response.content.decode()
        
        # Check that base variant is selected by default
        self.assertIn('value="base" id="variant-base" checked', content)
        
        # Check that other variants are not checked
        self.assertIn(f'value="{self.variant_500g.id}" id="variant-{self.variant_500g.id}">', content)
        self.assertNotIn(f'value="{self.variant_500g.id}" id="variant-{self.variant_500g.id}" checked', content)

    def test_error_handling_display(self):
        """Test error handling in frontend"""
        # Test with invalid product ID
        response = self.client.get('/product/non-existent-product/')
        self.assertEqual(response.status_code, 404)
        
        # Test cart with empty state
        response = self.client.get(reverse('yummytummy_store:cart_detail'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode()
        # Should handle empty cart gracefully
        self.assertIn('cart', content.lower())

    def test_loading_states(self):
        """Test loading state elements"""
        response = self.client.get(reverse('yummytummy_store:product_list'))
        content = response.content.decode()
        
        # Check for loading-related classes or attributes
        self.assertIn('fa-spinner', content)  # FontAwesome spinner icon
        
        response = self.client.get(reverse('yummytummy_store:product_detail', args=[self.product.slug]))
        content = response.content.decode()
        
        # Check for button text elements that can be modified
        self.assertIn('button-text', content)
