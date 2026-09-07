import re

import bleach
from django.utils.html import linebreaks
from django.utils.safestring import mark_safe


ALLOWED_TAGS = [
    'a', 'blockquote', 'br', 'em', 'h2', 'h3', 'h4', 'li', 'ol', 'p', 'strong', 'ul'
]
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'rel'],
}
ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']


def sanitize_rich_text(value):
    if not value:
        return ''
    return bleach.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )


def render_rich_text(value):
    sanitized = sanitize_rich_text(value)
    if not re.search(r'<[a-z][^>]*>', sanitized, re.IGNORECASE):
        sanitized = linebreaks(sanitized)
    return mark_safe(sanitized)
