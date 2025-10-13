"""
Django signals for YummyTummy Recipe system

This module contains signal handlers for automatic PDF generation
when recipes are created or updated.
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Recipe
from .pdf_utils import generate_recipe_pdf

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Recipe)
def auto_generate_recipe_pdf(sender, instance, created, **kwargs):
    """
    Automatically generate PDF when a Recipe is created or updated
    
    Args:
        sender: The Recipe model class
        instance: The Recipe instance being saved
        created: Boolean indicating if this is a new instance
        **kwargs: Additional keyword arguments
    """
    try:
        # Only generate PDF for published recipes with content
        if not instance.is_published:
            logger.info(f"Skipping PDF generation for unpublished recipe: {instance.title}")
            return
            
        if not instance.ingredients or not instance.instructions:
            logger.info(f"Skipping PDF generation for incomplete recipe: {instance.title}")
            return
        
        # Generate the PDF
        logger.info(f"Generating PDF for recipe: {instance.title}")
        pdf_file = generate_recipe_pdf(instance)
        
        # Save the PDF to the recipe's pdf_file field
        # Use update() to avoid triggering the signal again
        Recipe.objects.filter(pk=instance.pk).update(
            pdf_file=pdf_file.name
        )
        
        # Manually save the file content
        instance.pdf_file.save(pdf_file.name, pdf_file, save=False)
        
        logger.info(f"Successfully generated PDF for recipe: {instance.title}")
        
    except Exception as e:
        logger.error(f"Failed to generate PDF for recipe {instance.title}: {str(e)}")
        # Don't raise the exception to avoid breaking the recipe save operation
