"""
Shopping cart routes.
API endpoints for managing shopping cart items.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from decimal import Decimal

from app.core.database import get_db
from app.middleware.auth import get_current_active_user
from app.models.user import User
from app.services.cart_service import CartService
from app.schemas.cart import (
    CartItemCreate,
    CartItemUpdate,
    CartItemResponse,
    CartResponse,
    ProductBasicResponse
)

router = APIRouter(prefix="/cart", tags=["Shopping Cart"])


def _build_cart_item_response(cart_item) -> CartItemResponse:
    """Helper function to build CartItemResponse from model."""
    product = cart_item.product
    product_response = ProductBasicResponse(
        id=str(product.id),
        name=product.name,
        slug=product.slug,
        price=product.price,
        stock_quantity=product.stock_quantity,
        image_urls=product.image_urls or []
    )

    subtotal = cart_item.price_snapshot * cart_item.quantity

    return CartItemResponse(
        id=str(cart_item.id),
        product=product_response,
        quantity=cart_item.quantity,
        price_snapshot=cart_item.price_snapshot,
        subtotal=Decimal(str(subtotal)),
        created_at=cart_item.created_at,
        updated_at=cart_item.updated_at
    )


@router.get("", response_model=CartResponse)
async def get_cart(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's cart.

    Requires valid access token.

    Returns all cart items with totals.
    """
    service = CartService(db)
    cart_items = service.get_user_cart(str(current_user.id))

    # Calculate totals
    totals = service.calculate_cart_totals(cart_items)

    return CartResponse(
        cart_items=[_build_cart_item_response(item) for item in cart_items],
        total_items=totals["total_items"],
        total_amount=totals["total_amount"]
    )


@router.post("/items", response_model=CartItemResponse, status_code=status.HTTP_201_CREATED)
async def add_to_cart(
    request: CartItemCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Add product to cart.

    Requires valid access token.

    - **product_id**: Product UUID (required)
    - **quantity**: Quantity to add (required, min: 1)

    Returns created cart item.

    Errors:
    - 404: Product not found or inactive
    - 400: Quantity exceeds available stock
    - 409: Product already in cart (use PUT to update)
    """
    service = CartService(db)
    cart_item = service.add_to_cart(
        user_id=str(current_user.id),
        product_id=request.product_id,
        quantity=request.quantity
    )

    return _build_cart_item_response(cart_item)


@router.put("/items/{id}", response_model=CartItemResponse)
async def update_cart_item(
    id: str,
    request: CartItemUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update cart item quantity.

    Requires valid access token.

    - **quantity**: New quantity (required, min: 1)

    Returns updated cart item.

    Errors:
    - 404: Cart item not found or doesn't belong to user
    - 400: Quantity exceeds available stock
    """
    service = CartService(db)
    cart_item = service.update_cart_item(
        cart_item_id=id,
        user_id=str(current_user.id),
        quantity=request.quantity
    )

    return _build_cart_item_response(cart_item)


@router.delete("/items/{id}")
async def remove_from_cart(
    id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Remove item from cart.

    Requires valid access token.

    Returns success message.

    Errors:
    - 404: Cart item not found or doesn't belong to user
    """
    service = CartService(db)
    service.remove_from_cart(
        cart_item_id=id,
        user_id=str(current_user.id)
    )

    return {"message": "Item removed from cart"}


@router.delete("")
async def clear_cart(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Clear all items from cart.

    Requires valid access token.

    Returns success message.
    """
    service = CartService(db)
    service.clear_cart(str(current_user.id))

    return {"message": "Cart cleared successfully"}
