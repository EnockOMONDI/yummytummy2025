from django import template
from django.templatetags.static import static
import logging

register = template.Library()
logger = logging.getLogger(__name__)


@register.filter
def product_image_url(product, size="400x400"):
    """
    Get product image URL with optional size transformation.
    Usage: {{ product|product_image_url:"800x800" }}
    """
    if not product:
        logger.warning("product_image_url called with None product")
        return static('yummytummy_store/img/product-1.png')

    # Try Uploadcare image first
    try:
        if hasattr(product, 'image') and product.image:
            # Check if the image field has a value (not empty string or None)
            if str(product.image).strip():
                cdn_url = product.image.cdn_url
                if cdn_url:
                    return f"{cdn_url}/-/preview/{size}/"
    except (AttributeError, ValueError, TypeError) as e:
        logger.debug(f"Uploadcare image error for product {product.id}: {e}")

    # Fallback to legacy image
    try:
        if hasattr(product, 'legacy_image') and product.legacy_image:
            if product.legacy_image.name:  # Check if file actually exists
                return product.legacy_image.url
    except (AttributeError, ValueError, TypeError) as e:
        logger.debug(f"Legacy image error for product {product.id}: {e}")

    # Final fallback to placeholder
    return static('yummytummy_store/img/product-1.png')


@register.filter
def product_image_thumbnail(product):
    """
    Get product image thumbnail (100x100) for admin or small displays.
    Usage: {{ product|product_image_thumbnail }}
    """
    return product_image_url(product, "100x100")


@register.filter
def product_image_detail(product):
    """
    Get product image for detail view (800x800).
    Usage: {{ product|product_image_detail }}
    """
    return product_image_url(product, "800x800")


@register.filter
def product_image_list(product):
    """
    Get product image for list view (400x400).
    Usage: {{ product|product_image_list }}
    """
    return product_image_url(product, "400x400")


@register.simple_tag
def get_product_image(product, transform="/-/preview/400x400/"):
    """
    Get product image URL with custom transformation.
    Usage: {% get_product_image product "/-/preview/800x800/" %}
    """
    if not product:
        logger.warning("get_product_image called with None product")
        return static('yummytummy_store/img/product-1.png')

    # Try Uploadcare image first
    try:
        if hasattr(product, 'image') and product.image:
            if str(product.image).strip():
                cdn_url = product.image.cdn_url
                if cdn_url:
                    return f"{cdn_url}{transform}"
    except (AttributeError, ValueError, TypeError) as e:
        logger.debug(f"Uploadcare image error for product {product.id}: {e}")

    # Fallback to legacy image
    try:
        if hasattr(product, 'legacy_image') and product.legacy_image:
            if product.legacy_image.name:
                return product.legacy_image.url
    except (AttributeError, ValueError, TypeError) as e:
        logger.debug(f"Legacy image error for product {product.id}: {e}")

    # Final fallback to placeholder
    return static('yummytummy_store/img/product-1.png')


@register.filter
def debug_product_image(product):
    """
    Debug filter to show image information for a product.
    Usage: {{ product|debug_product_image }}
    """
    if not product:
        return "Product is None"

    debug_info = []
    debug_info.append(f"Product ID: {product.id}")
    debug_info.append(f"Product Name: {product.name}")

    # Check Uploadcare image
    try:
        if hasattr(product, 'image'):
            debug_info.append(f"Has image field: True")
            debug_info.append(f"Image value: '{product.image}'")
            if product.image:
                debug_info.append(f"Image CDN URL: {product.image.cdn_url}")
            else:
                debug_info.append("Image field is empty")
        else:
            debug_info.append("Has image field: False")
    except Exception as e:
        debug_info.append(f"Image field error: {e}")

    # Check legacy image
    try:
        if hasattr(product, 'legacy_image'):
            debug_info.append(f"Has legacy_image field: True")
            debug_info.append(f"Legacy image name: '{product.legacy_image.name if product.legacy_image else 'None'}'")
            if product.legacy_image:
                debug_info.append(f"Legacy image URL: {product.legacy_image.url}")
            else:
                debug_info.append("Legacy image field is empty")
        else:
            debug_info.append("Has legacy_image field: False")
    except Exception as e:
        debug_info.append(f"Legacy image field error: {e}")

    return " | ".join(debug_info)


@register.inclusion_tag('yummytummy_store/partials/product_image.html')
def product_image(product, css_class="product-img", alt_text=None, size="400x400"):
    """
    Render a product image with proper fallbacks.
    Usage: {% product_image product css_class="my-image" alt_text="Custom alt" size="800x800" %}
    """
    image_url = product_image_url(product, size)
    alt_text = alt_text or product.name

    return {
        'image_url': image_url,
        'alt_text': alt_text,
        'css_class': css_class,
        'product': product,
    }


@register.filter
def split_variant_name(variant_name):
    """
    Split variant name into parts for display in variant cards.
    Examples:
    - "Yummy tummy Peanut Butter 500G" -> ["Peanut Butter", "500G"]
    - "Ground Nuts 250G" -> ["Ground Nuts", "250G"]
    - "Cashew Nuts Premium" -> ["Cashew Nuts", "Premium"]
    """
    if not variant_name:
        return ["Product"]

    # Remove common prefixes like "Yummy tummy" or product brand names
    name = variant_name.strip()

    # Common patterns to remove from the beginning
    prefixes_to_remove = [
        "Yummy tummy ",
        "YummyTummy ",
        "Maslove ",
    ]

    for prefix in prefixes_to_remove:
        if name.startswith(prefix):
            name = name[len(prefix):].strip()
            break

    # Split by common patterns
    # Look for size patterns (numbers followed by G, KG, ML, L, etc.)
    import re

    # Pattern to match sizes like "250G", "500G", "1KG", "500ML", etc.
    size_pattern = r'\b(\d+(?:\.\d+)?(?:G|KG|ML|L|OZ|LB))\b'
    size_match = re.search(size_pattern, name, re.IGNORECASE)

    if size_match:
        size = size_match.group(1)
        # Remove the size from the name to get the product type
        product_type = re.sub(size_pattern, '', name, flags=re.IGNORECASE).strip()

        # Clean up any extra spaces
        product_type = re.sub(r'\s+', ' ', product_type).strip()

        if product_type:
            return [product_type, size]
        else:
            return [size]

    # If no size pattern found, try to split by common words
    words = name.split()

    if len(words) <= 2:
        return words
    elif len(words) == 3:
        # For 3 words, try to group them intelligently
        return [f"{words[0]} {words[1]}", words[2]]
    else:
        # For more than 3 words, take first two as product type, rest as description
        return [f"{words[0]} {words[1]}", " ".join(words[2:])]
