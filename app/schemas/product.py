"""
Product Pydantic schemas.
Request and response models for product endpoints.
"""

from pydantic import BaseModel, Field, field_validator
from decimal import Decimal
from datetime import datetime
from typing import Optional, List
from enum import Enum


class SortBy(str, Enum):
    """Sort options for product listing."""
    created_at = "created_at"
    price = "price"
    name = "name"


class SortOrder(str, Enum):
    """Sort order options."""
    asc = "asc"
    desc = "desc"


class ProductCreate(BaseModel):
    """Schema for creating a product."""

    name: str = Field(..., max_length=200)
    slug: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    price: Decimal = Field(..., ge=0, le=999999.99)
    stock_quantity: int = Field(..., ge=0)
    category_id: Optional[str] = None
    image_urls: Optional[List[str]] = Field(default_factory=list, max_length=10)
    is_active: bool = True

    @field_validator('image_urls')
    @classmethod
    def validate_image_urls(cls, v):
        """Validate image URLs list."""
        if v and len(v) > 10:
            raise ValueError('Maximum 10 images allowed')
        return v


class ProductUpdate(BaseModel):
    """Schema for updating a product."""

    name: Optional[str] = Field(None, max_length=200)
    slug: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0, le=999999.99)
    stock_quantity: Optional[int] = Field(None, ge=0)
    category_id: Optional[str] = None
    image_urls: Optional[List[str]] = Field(None, max_length=10)
    is_active: Optional[bool] = None

    @field_validator('image_urls')
    @classmethod
    def validate_image_urls(cls, v):
        """Validate image URLs list."""
        if v and len(v) > 10:
            raise ValueError('Maximum 10 images allowed')
        return v


class CategoryBasicResponse(BaseModel):
    """Basic category info for product response."""

    id: str
    name: str
    slug: str

    class Config:
        from_attributes = True


class ProductResponse(BaseModel):
    """Schema for product response."""

    id: str
    name: str
    slug: str
    description: Optional[str]
    price: Decimal
    stock_quantity: int
    category: Optional[CategoryBasicResponse] = None
    image_urls: List[str] = []
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    """Schema for paginated product list response."""

    products: List[ProductResponse]
    total: int
    page: int
    limit: int
    total_pages: int
