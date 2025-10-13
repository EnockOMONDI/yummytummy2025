"""
Template filters for YummyTummy Recipe system

This module provides template filters for recipe content truncation
and preview functionality.
"""

from django import template
import math

register = template.Library()


@register.filter
def truncate_ingredients(ingredients, percentage=15):
    """
    Truncate ingredients list to show only a percentage of items
    
    Args:
        ingredients: List of ingredient strings
        percentage: Percentage of ingredients to show (default: 15%)
    
    Returns:
        List of truncated ingredients with "..." indicator if truncated
    
    Usage: {{ recipe.ingredients|truncate_ingredients:15 }}
    """
    if not ingredients or not isinstance(ingredients, list):
        return ingredients
    
    total_count = len(ingredients)
    if total_count == 0:
        return ingredients
    
    # Calculate how many ingredients to show (minimum 1, maximum all)
    show_count = max(1, math.ceil(total_count * percentage / 100))
    show_count = min(show_count, total_count)
    
    # If we're showing all ingredients, return as-is
    if show_count >= total_count:
        return ingredients
    
    # Return truncated list with indicator
    truncated = ingredients[:show_count]
    truncated.append(f"... and {total_count - show_count} more ingredients")
    
    return truncated


@register.filter
def truncate_instructions(instructions, show_steps=1):
    """
    Truncate instructions list to show only the first few steps
    
    Args:
        instructions: List of instruction strings
        show_steps: Number of steps to show (default: 1)
    
    Returns:
        List of truncated instructions with "..." indicator if truncated
    
    Usage: {{ recipe.instructions|truncate_instructions:2 }}
    """
    if not instructions or not isinstance(instructions, list):
        return instructions
    
    total_count = len(instructions)
    if total_count == 0:
        return instructions
    
    # Ensure show_steps is at least 1 and not more than total
    show_steps = max(1, min(show_steps, total_count))
    
    # If we're showing all steps, return as-is
    if show_steps >= total_count:
        return instructions
    
    # Return truncated list with indicator
    truncated = instructions[:show_steps]
    truncated.append(f"... and {total_count - show_steps} more steps to complete this delicious recipe!")
    
    return truncated


@register.filter
def recipe_preview_stats(recipe):
    """
    Get preview statistics for a recipe
    
    Args:
        recipe: Recipe model instance
    
    Returns:
        Dictionary with preview statistics
    
    Usage: {% with stats=recipe|recipe_preview_stats %}{{ stats.ingredients_shown }}/{{ stats.total_ingredients }}{% endwith %}
    """
    if not recipe:
        return {
            'total_ingredients': 0,
            'ingredients_shown': 0,
            'total_steps': 0,
            'steps_shown': 0,
        }
    
    total_ingredients = len(recipe.ingredients) if recipe.ingredients else 0
    total_steps = len(recipe.instructions) if recipe.instructions else 0
    
    # Calculate preview amounts (15% for ingredients, 1 step for instructions)
    ingredients_shown = max(1, math.ceil(total_ingredients * 15 / 100)) if total_ingredients > 0 else 0
    ingredients_shown = min(ingredients_shown, total_ingredients)
    
    steps_shown = min(1, total_steps)
    
    return {
        'total_ingredients': total_ingredients,
        'ingredients_shown': ingredients_shown,
        'total_steps': total_steps,
        'steps_shown': steps_shown,
    }


@register.filter
def has_purchased_recipe(user, recipe):
    """
    Check if a user has purchased a specific recipe
    
    Args:
        user: User instance (can be AnonymousUser)
        recipe: Recipe instance
    
    Returns:
        Boolean indicating if user has purchased the recipe
    
    Usage: {% if user|has_purchased_recipe:recipe %}...{% endif %}
    """
    if not user or not recipe:
        return False
    
    # Anonymous users haven't purchased anything
    if not user.is_authenticated:
        return False
    
    # Import here to avoid circular imports
    from ..models import RecipePurchase
    
    try:
        return RecipePurchase.objects.filter(user=user, recipe=recipe).exists()
    except Exception:
        return False


@register.simple_tag
def recipe_purchase_status(user, recipe):
    """
    Get detailed purchase status for a recipe
    
    Args:
        user: User instance (can be AnonymousUser)
        recipe: Recipe instance
    
    Returns:
        Dictionary with purchase status information
    
    Usage: {% recipe_purchase_status user recipe as status %}
    """
    if not user or not recipe:
        return {
            'purchased': False,
            'can_purchase': False,
            'message': 'Recipe not available'
        }
    
    # Anonymous users can purchase but haven't purchased
    if not user.is_authenticated:
        return {
            'purchased': False,
            'can_purchase': True,
            'message': 'Sign in to track your purchases'
        }
    
    # Import here to avoid circular imports
    from ..models import RecipePurchase
    
    try:
        purchased = RecipePurchase.objects.filter(user=user, recipe=recipe).exists()
        return {
            'purchased': purchased,
            'can_purchase': not purchased,
            'message': 'Already purchased' if purchased else 'Available for purchase'
        }
    except Exception:
        return {
            'purchased': False,
            'can_purchase': True,
            'message': 'Available for purchase'
        }
