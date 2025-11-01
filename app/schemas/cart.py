"""
Cart Pydantic schemas.
Request and response models for shopping cart endpoints.
"""

from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from typing import List


class CartItemCreate(BaseModel):
    """Schema for adding item to cart."""

    product_id: str
    quantity: int = Field(..., ge=1)


class CartItemUpdate(BaseModel):
    """Schema for updating cart item quantity."""

    quantity: int = Field(..., ge=1)


class ProductBasicResponse(BaseModel):
    """Basic product info for cart item response."""

    id: str
    name: str
    slug: str
    price: Decimal
    stock_quantity: int
    image_urls: List[str] = []

    class Config:
        from_attributes = True


class CartItemResponse(BaseModel):
    """Schema for cart item response."""

    id: str
    product: ProductBasicResponse
    quantity: int
    price_snapshot: Decimal
    subtotal: Decimal
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CartResponse(BaseModel):
    """Schema for complete cart response."""

    cart_items: List[CartItemResponse]
    total_items: int  # Sum of all quantities
    total_amount: Decimal  # Sum of all subtotals
