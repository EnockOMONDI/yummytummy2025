"""
Django signals for YummyTummy Recipe system

This module contains signal handlers for automatic PDF generation
when recipes are created or updated.
"""

import logging
from pathlib import Path

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Recipe
from .pdf_utils import generate_recipe_pdf

logger = logging.getLogger(__name__)


def _generate_and_attach_recipe_pdf(recipe_id):
    """Generate a PDF after commit while preserving explicitly uploaded PDFs."""
    try:
        instance = Recipe.objects.get(pk=recipe_id)
        if not instance.is_published:
            return
        if not instance.ingredients or not instance.instructions:
            return

        previous_name = instance.pdf_file.name if instance.pdf_file else ''
        if previous_name and '_recipe' not in Path(previous_name).stem:
            return

        pdf_file = generate_recipe_pdf(instance)
        storage = instance.pdf_file.storage
        target_name = instance.pdf_file.field.generate_filename(instance, pdf_file.name)
        if target_name != previous_name and storage.exists(target_name):
            storage.delete(target_name)
        stored_name = storage.save(target_name, pdf_file)
        Recipe.objects.filter(pk=instance.pk).update(pdf_file=stored_name)

        if previous_name and previous_name != stored_name:
            storage.delete(previous_name)
    except Recipe.DoesNotExist:
        return
    except Exception as exc:
        logger.error('Failed to generate PDF for recipe %s: %s', recipe_id, exc.__class__.__name__)


@receiver(post_save, sender=Recipe)
def auto_generate_recipe_pdf(sender, instance, **kwargs):
    transaction.on_commit(
        lambda recipe_id=instance.pk: _generate_and_attach_recipe_pdf(recipe_id)
    )
