"""
Order routes.
API endpoints for order management.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Optional
from decimal import Decimal

from app.core.database import get_db
from app.middleware.auth import get_current_active_user, require_admin
from app.models.user import User, UserRole
from app.services.order_service import OrderService
from app.schemas.order import (
    OrderCreate,
    OrderStatusUpdate,
    OrderResponse,
    OrderDetailResponse,
    OrderListResponse,
    OrderItemResponse,
    UserBasicInfo,
    ProductBasicInfo,
    OrderStatusEnum
)

router = APIRouter(prefix="/orders", tags=["Orders"])


def _build_order_response(order, include_items: bool = False):
    """Helper function to build order response."""
    items_count = len(order.order_items)

    if not include_items:
        return OrderResponse(
            id=str(order.id),
            user_id=str(order.user_id),
            status=order.status.value,
            total_amount=order.total_amount,
            payment_method=order.payment_method,
            items_count=items_count,
            created_at=order.created_at,
            updated_at=order.updated_at
        )

    # Build detailed response with items
    user_info = UserBasicInfo(
        id=str(order.user.id),
        email=order.user.email,
        full_name=order.user.full_name
    )

    order_items = []
    for item in order.order_items:
        product_info = ProductBasicInfo(
            id=str(item.product.id),
            name=item.product.name,
            slug=item.product.slug,
            image_urls=item.product.image_urls or []
        )

        subtotal = item.price_snapshot * item.quantity

        order_items.append(OrderItemResponse(
            id=str(item.id),
            product=product_info,
            quantity=item.quantity,
            price_snapshot=item.price_snapshot,
            subtotal=Decimal(str(subtotal))
        ))

    return OrderDetailResponse(
        id=str(order.id),
        user=user_info,
        status=order.status.value,
        total_amount=order.total_amount,
        payment_method=order.payment_method,
        payment_id=order.payment_id,
        shipping_address=order.shipping_address,
        notes=order.notes,
        order_items=order_items,
        created_at=order.created_at,
        updated_at=order.updated_at
    )


@router.get("", response_model=OrderListResponse)
async def get_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[OrderStatusEnum] = Query(None),
    user_id: Optional[str] = Query(None, description="Admin only: filter by user"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get orders.

    Regular users see only their own orders.
    Admins can see all orders and filter by user_id.

    - **page**: Page number (min: 1)
    - **limit**: Items per page (min: 1, max: 100)
    - **status**: Filter by order status
    - **user_id**: Filter by user UUID (admin only)
    """
    service = OrderService(db)

    is_admin = current_user.role == UserRole.admin

    # Non-admin users can only see their own orders
    if not is_admin:
        if user_id and user_id != str(current_user.id):
            from app.core.exceptions import AuthorizationError
            raise AuthorizationError("Cannot access another user's orders")

        result = service.get_user_orders(
            user_id=str(current_user.id),
            page=page,
            limit=limit,
            status=status.value if status else None
        )
    else:
        # Admin can see all orders
        result = service.get_all_orders(
            page=page,
            limit=limit,
            status=status.value if status else None,
            user_id=user_id
        )

    return OrderListResponse(
        orders=[_build_order_response(order) for order in result["items"]],
        total=result["total"],
        page=result["page"],
        limit=result["limit"],
        total_pages=result["total_pages"]
    )


@router.get("/{id}", response_model=OrderDetailResponse)
async def get_order(
    id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get order by ID with full details.

    Users can only view their own orders unless they're admin.

    Returns order with all items, shipping address, and status.
    """
    service = OrderService(db)
    is_admin = current_user.role == UserRole.admin

    order = service.get_order_by_id(
        order_id=id,
        user_id=str(current_user.id),
        is_admin=is_admin
    )

    return _build_order_response(order, include_items=True)


@router.post("", response_model=OrderDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    request: OrderCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create order from current cart.

    Requires valid access token.

    - **shipping_address**: Complete shipping address (required)
      - street, city, state, zip, country
    - **notes**: Optional order notes (max 500 chars)

    Creates order from all cart items, clears cart, and decrements stock.

    Errors:
    - 400: Cart is empty or invalid shipping address
    - 409: Insufficient stock for one or more items
    """
    service = OrderService(db)
    order = service.create_order_from_cart(
        user_id=str(current_user.id),
        shipping_address=request.shipping_address.model_dump(),
        notes=request.notes
    )

    return _build_order_response(order, include_items=True)


@router.put("/{id}/status", response_model=OrderDetailResponse)
async def update_order_status(
    id: str,
    request: OrderStatusUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update order status.

    Requires admin authentication.

    - **status**: New order status (required)
    - **notes**: Optional admin notes about status change

    Validates status transitions before updating.

    Errors:
    - 404: Order not found
    - 400: Invalid status transition
    """
    service = OrderService(db)
    order = service.update_order_status(
        order_id=id,
        new_status=request.status.value,
        notes=request.notes
    )

    return _build_order_response(order, include_items=True)


@router.post("/{id}/cancel", response_model=OrderDetailResponse)
async def cancel_order(
    id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Cancel an order.

    Users can cancel their own orders. Admins can cancel any order.

    Only pending or processing orders can be cancelled.

    Errors:
    - 404: Order not found
    - 403: Order doesn't belong to user (unless admin)
    - 400: Order cannot be cancelled (wrong status)
    """
    service = OrderService(db)
    is_admin = current_user.role == UserRole.admin

    order = service.cancel_order(
        order_id=id,
        user_id=str(current_user.id),
        is_admin=is_admin
    )

    return _build_order_response(order, include_items=True)
