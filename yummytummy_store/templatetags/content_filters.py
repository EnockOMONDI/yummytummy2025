from django import template

from yummytummy_store.rich_text import render_rich_text

register = template.Library()


@register.filter
def safe_richtext(value):
    return render_rich_text(value)
