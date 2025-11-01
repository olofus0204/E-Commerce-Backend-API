"""
Payment Pydantic schemas.
Request and response models for payment endpoints.
"""

from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime
from typing import Optional
from enum import Enum


class PaymentMethod(str, Enum):
    """Payment method options."""
    stripe = "stripe"
    mock = "mock"


class PaymentRequest(BaseModel):
    """Schema for payment processing request."""

    order_id: str
    payment_method: Optional[PaymentMethod] = None  # Defaults to env var PAYMENT_PROVIDER
    stripe_token: Optional[str] = None  # Required if payment_method='stripe'


class PaymentResponse(BaseModel):
    """Schema for payment response."""

    id: str  # payment_id from provider
    order_id: str
    status: str  # 'paid', 'failed'
    payment_method: str
    amount: Decimal
    created_at: datetime

    class Config:
        from_attributes = True


class OrderUpdateResponse(BaseModel):
    """Schema for order after payment."""

    id: str
    status: str
    updated_at: datetime

    class Config:
        from_attributes = True


class PaymentProcessResponse(BaseModel):
    """Schema for complete payment process response."""

    payment: PaymentResponse
    order: OrderUpdateResponse
