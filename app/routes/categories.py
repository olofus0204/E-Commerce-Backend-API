"""
Category routes.
API endpoints for category management.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.middleware.auth import require_admin
from app.models.user import User
from app.models.product import Product
from app.services.category_service import CategoryService
from app.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryListResponse,
    CategoryDetailResponse
)

router = APIRouter(prefix="/categories", tags=["Categories"])


def _build_category_response(category) -> CategoryResponse:
    """Helper function to build CategoryResponse from model."""
    return CategoryResponse(
        id=str(category.id),
        name=category.name,
        slug=category.slug,
        description=category.description,
        parent_id=str(category.parent_id) if category.parent_id else None,
        created_at=category.created_at,
        updated_at=category.updated_at,
        subcategories=[_build_category_response(sub) for sub in category.subcategories]
    )


@router.get("", response_model=CategoryListResponse)
async def get_categories(
    parent_id: Optional[str] = Query(None, description="Filter by parent category"),
    include_children: bool = Query(True, description="Include subcategories"),
    db: Session = Depends(get_db)
):
    """
    Get all categories.

    Public endpoint - no authentication required.

    - **parent_id**: Filter by parent category UUID (optional)
    - **include_children**: Include subcategories (default: true)

    Returns list of categories with subcategories.
    """
    service = CategoryService(db)
    categories = service.get_all_categories(parent_id, include_children)

    return CategoryListResponse(
        categories=[_build_category_response(cat) for cat in categories],
        total=len(categories)
    )


@router.get("/{id}", response_model=CategoryDetailResponse)
async def get_category(
    id: str,
    db: Session = Depends(get_db)
):
    """
    Get category by ID.

    Public endpoint - no authentication required.

    Returns category details with subcategories and product count.
    """
    service = CategoryService(db)
    category = service.get_category_by_id(id)

    # Count products in this category
    products_count = db.query(Product).filter(Product.category_id == id).count()

    return CategoryDetailResponse(
        id=str(category.id),
        name=category.name,
        slug=category.slug,
        description=category.description,
        parent_id=str(category.parent_id) if category.parent_id else None,
        created_at=category.created_at,
        updated_at=category.updated_at,
        subcategories=[_build_category_response(sub) for sub in category.subcategories],
        products_count=products_count
    )


@router.post("", response_model=CategoryResponse, status_code=201)
async def create_category(
    request: CategoryCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new category.

    Requires admin authentication.

    - **name**: Category name (required)
    - **slug**: URL slug (auto-generated if not provided)
    - **description**: Optional description
    - **parent_id**: Optional parent category UUID

    Returns created category.
    """
    service = CategoryService(db)
    category = service.create_category(
        name=request.name,
        slug=request.slug,
        description=request.description,
        parent_id=request.parent_id
    )

    return _build_category_response(category)


@router.put("/{id}", response_model=CategoryResponse)
async def update_category(
    id: str,
    request: CategoryUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update a category.

    Requires admin authentication.

    - **name**: New name (optional)
    - **slug**: New slug (optional)
    - **description**: New description (optional)
    - **parent_id**: New parent UUID or null to remove parent (optional)

    Returns updated category.
    """
    service = CategoryService(db)
    category = service.update_category(
        category_id=id,
        name=request.name,
        slug=request.slug,
        description=request.description,
        parent_id=request.parent_id
    )

    return _build_category_response(category)


@router.delete("/{id}")
async def delete_category(
    id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a category.

    Requires admin authentication.

    Cannot delete categories with products or subcategories.

    Returns success message.
    """
    service = CategoryService(db)
    service.delete_category(id)

    return {"message": "Category deleted successfully"}
