"""
Pagination utility.
Helper functions for paginating database query results.
"""

from math import ceil
from typing import Any, Dict
from sqlalchemy.orm import Query


def paginate(query: Query, page: int, limit: int) -> Dict[str, Any]:
    """
    Paginate a SQLAlchemy query.

    Args:
        query: SQLAlchemy query object
        page: Page number (1-indexed)
        limit: Items per page (max 100)

    Returns:
        dict with:
            - items: List of paginated results
            - total: Total count of items
            - page: Current page number
            - limit: Items per page
            - total_pages: Total number of pages

    Raises:
        ValueError: If page < 1 or limit out of range
    """
    # Validate parameters
    if page < 1:
        raise ValueError("Page must be >= 1")

    if limit < 1 or limit > 100:
        raise ValueError("Limit must be between 1 and 100")

    # Get total count
    total = query.count()

    # Calculate offset
    offset = (page - 1) * limit

    # Calculate total pages
    total_pages = ceil(total / limit) if total > 0 else 0

    # Execute query with pagination
    items = query.offset(offset).limit(limit).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }
