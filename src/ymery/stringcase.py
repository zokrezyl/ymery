"""
Minimal stringcase implementation for ymery.
Only implements spinalcase (kebab-case) which is the only function we use.
"""

import re


def spinalcase(text: str) -> str:
    """
    Convert string to spinal-case (kebab-case).

    Examples:
        CamelCase -> camel-case
        snake_case -> snake-case
        SCREAMING_SNAKE -> screaming-snake
        mixedCamelCase -> mixed-camel-case
    """
    if not text:
        return text

    # Replace underscores with hyphens
    text = text.replace('_', '-')

    # Insert hyphens before uppercase letters (but not at the start)
    text = re.sub('([a-z0-9])([A-Z])', r'\1-\2', text)

    # Convert to lowercase
    text = text.lower()

    # Replace multiple consecutive hyphens with single hyphen
    text = re.sub('-+', '-', text)

    # Remove leading/trailing hyphens
    text = text.strip('-')

    return text
