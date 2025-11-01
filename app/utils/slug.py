"""
Slug generation utility.
Creates URL-friendly slugs from text with uniqueness checking.
"""

import re
from sqlalchemy.orm import Session


def generate_slug(text: str, db: Session, model, slug_field: str = 'slug') -> str:
    """
    Generate a unique URL-friendly slug from text.

    Process:
    1. Convert to lowercase
    2. Replace spaces with hyphens
    3. Remove non-alphanumeric characters (except hyphens)
    4. Remove consecutive hyphens
    5. Strip leading/trailing hyphens
    6. Check uniqueness and append number if needed

    Args:
        text: Input text to convert to slug
        db: Database session
        model: SQLAlchemy model class to check for uniqueness
        slug_field: Name of the slug field in the model (default: 'slug')

    Returns:
        Unique slug string

    Example:
        "Product Name!" -> "product-name"
        "Product Name" (if exists) -> "product-name-2"
    """
    # Convert to lowercase and replace spaces with hyphens
    slug = text.lower().strip()
    slug = re.sub(r'\s+', '-', slug)

    # Remove all non-alphanumeric characters except hyphens
    slug = re.sub(r'[^a-z0-9-]', '', slug)

    # Remove consecutive hyphens
    slug = re.sub(r'-+', '-', slug)

    # Strip leading/trailing hyphens
    slug = slug.strip('-')

    # Ensure slug is not empty
    if not slug:
        slug = 'item'

    # Check for uniqueness
    original_slug = slug
    counter = 2

    while True:
        # Query database for existing slug
        existing = db.query(model).filter(
            getattr(model, slug_field) == slug
        ).first()

        if not existing:
            # Slug is unique
            break

        # Slug exists, append counter
        slug = f"{original_slug}-{counter}"
        counter += 1

    return slug
