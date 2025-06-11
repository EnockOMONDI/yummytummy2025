def cart_processor(request):
    """
    Context processor to make the cart available in all templates
    """
    # Ensure the cart exists in the session
    if 'cart' not in request.session:
        request.session['cart'] = {}
        request.session.modified = True

    cart = request.session['cart']

    # Calculate the total number of items in the cart
    cart_items_count = 0
    try:
        cart_items_count = sum(int(item.get('quantity', 0)) for item in cart.values())
    except (ValueError, TypeError):
        # Handle any corrupted cart data
        pass

    return {
        'cart': cart,
        'cart_items_count': cart_items_count
    }
