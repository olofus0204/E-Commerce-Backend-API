"""
Order Pydantic schemas.
Request and response models for order endpoints.
"""

from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from typing import Optional, List
from enum import Enum


class OrderStatusEnum(str, Enum):
    """Order status options."""
    pending = "pending"
    processing = "processing"
    paid = "paid"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"
    refunded = "refunded"


class ShippingAddress(BaseModel):
    """Schema for shipping address."""

    street: str = Field(..., min_length=1)
    city: str = Field(..., min_length=1)
    state: str = Field(..., min_length=1)
    zip: str = Field(..., min_length=1)
    country: str = Field(..., min_length=1)


class OrderCreate(BaseModel):
    """Schema for creating an order from cart."""

    shipping_address: ShippingAddress
    notes: Optional[str] = Field(None, max_length=500)


class OrderStatusUpdate(BaseModel):
    """Schema for updating order status (admin only)."""

    status: OrderStatusEnum
    notes: Optional[str] = None


class ProductBasicInfo(BaseModel):
    """Basic product info for order item."""

    id: str
    name: str
    slug: str
    image_urls: List[str] = []

    class Config:
        from_attributes = True


class OrderItemResponse(BaseModel):
    """Schema for order item response."""

    id: str
    product: ProductBasicInfo
    quantity: int
    price_snapshot: Decimal
    subtotal: Decimal

    class Config:
        from_attributes = True


class UserBasicInfo(BaseModel):
    """Basic user info for order response."""

    id: str
    email: str
    full_name: Optional[str]

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    """Schema for order response."""

    id: str
    user_id: str
    status: str
    total_amount: Decimal
    payment_method: Optional[str]
    items_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OrderDetailResponse(BaseModel):
    """Schema for detailed order response."""

    id: str
    user: UserBasicInfo
    status: str
    total_amount: Decimal
    payment_method: Optional[str]
    payment_id: Optional[str]
    shipping_address: Optional[dict]
    notes: Optional[str]
    order_items: List[OrderItemResponse]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    """Schema for paginated order list response."""

    orders: List[OrderResponse]
    total: int
    page: int
    limit: int
    total_pages: int
