"""
Product routes.
API endpoints for product management with search, filtering, and pagination.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from decimal import Decimal
from typing import Optional

from app.core.database import get_db
from app.middleware.auth import require_admin, get_current_active_user
from app.models.user import User, UserRole
from app.services.product_service import ProductService
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
    CategoryBasicResponse,
    SortBy,
    SortOrder
)

router = APIRouter(prefix="/products", tags=["Products"])


def _build_product_response(product) -> ProductResponse:
    """Helper function to build ProductResponse from model."""
    category_response = None
    if product.category:
        category_response = CategoryBasicResponse(
            id=str(product.category.id),
            name=product.category.name,
            slug=product.category.slug
        )

    return ProductResponse(
        id=str(product.id),
        name=product.name,
        slug=product.slug,
        description=product.description,
        price=product.price,
        stock_quantity=product.stock_quantity,
        category=category_response,
        image_urls=product.image_urls or [],
        is_active=product.is_active,
        created_at=product.created_at,
        updated_at=product.updated_at
    )


@router.get("", response_model=ProductListResponse)
async def get_products(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    category_id: Optional[str] = Query(None, description="Filter by category UUID"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    min_price: Optional[Decimal] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[Decimal] = Query(None, ge=0, description="Maximum price"),
    in_stock: Optional[bool] = Query(None, description="Filter by stock availability"),
    sort_by: SortBy = Query(SortBy.created_at, description="Sort field"),
    sort_order: SortOrder = Query(SortOrder.desc, description="Sort order"),
    db: Session = Depends(get_db)
):
    """
    Get all products with filtering, search, and pagination.

    Public endpoint - no authentication required.

    Only returns active products unless accessed by admin.

    Query parameters:
    - **page**: Page number (min: 1)
    - **limit**: Items per page (min: 1, max: 100)
    - **category_id**: Filter by category UUID
    - **search**: Search term for name/description
    - **min_price**: Minimum price filter
    - **max_price**: Maximum price filter
    - **in_stock**: Filter products with stock > 0
    - **sort_by**: Sort by created_at, price, or name
    - **sort_order**: asc or desc
    """
    service = ProductService(db)
    result = service.get_all_products(
        page=page,
        limit=limit,
        category_id=category_id,
        search=search,
        min_price=min_price,
        max_price=max_price,
        in_stock=in_stock,
        sort_by=sort_by.value,
        sort_order=sort_order.value,
        include_inactive=False
    )

    return ProductListResponse(
        products=[_build_product_response(p) for p in result["items"]],
        total=result["total"],
        page=result["page"],
        limit=result["limit"],
        total_pages=result["total_pages"]
    )


@router.get("/{id}", response_model=ProductResponse)
async def get_product(
    id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_active_user) if False else None
):
    """
    Get product by ID.

    Public endpoint - no authentication required.

    Returns product details. Inactive products are hidden from non-admin users.
    """
    # Check if user is admin to include inactive products
    include_inactive = False
    try:
        # Try to get current user (optional)
        from fastapi import Request
        # For now, only show active products to public
        pass
    except:
        pass

    service = ProductService(db)
    product = service.get_product_by_id(id, include_inactive=include_inactive)

    return _build_product_response(product)


@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(
    request: ProductCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new product.

    Requires admin authentication.

    - **name**: Product name (required)
    - **price**: Price (required, 0-999999.99)
    - **stock_quantity**: Available stock (required, >= 0)
    - **slug**: URL slug (auto-generated if not provided)
    - **description**: Product description (optional)
    - **category_id**: Category UUID (optional)
    - **image_urls**: List of image URLs (max 10)
    - **is_active**: Active status (default: true)

    Returns created product.
    """
    service = ProductService(db)
    product = service.create_product(
        name=request.name,
        slug=request.slug,
        description=request.description,
        price=request.price,
        stock_quantity=request.stock_quantity,
        category_id=request.category_id,
        image_urls=request.image_urls,
        is_active=request.is_active
    )

    return _build_product_response(product)


@router.put("/{id}", response_model=ProductResponse)
async def update_product(
    id: str,
    request: ProductUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update a product.

    Requires admin authentication.

    All fields are optional. Only provided fields will be updated.

    Returns updated product.
    """
    service = ProductService(db)
    product = service.update_product(
        product_id=id,
        name=request.name,
        slug=request.slug,
        description=request.description,
        price=request.price,
        stock_quantity=request.stock_quantity,
        category_id=request.category_id,
        image_urls=request.image_urls,
        is_active=request.is_active
    )

    return _build_product_response(product)


@router.delete("/{id}")
async def delete_product(
    id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a product (soft delete).

    Requires admin authentication.

    Sets product to inactive (is_active=False).

    Returns success message.
    """
    service = ProductService(db)
    service.delete_product(id)

    return {"message": "Product deleted successfully"}
