"""
Category Pydantic schemas.
Request and response models for category endpoints.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class CategoryCreate(BaseModel):
    """Schema for creating a category."""

    name: str = Field(..., max_length=100)
    slug: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    parent_id: Optional[str] = None  # UUID as string


class CategoryUpdate(BaseModel):
    """Schema for updating a category."""

    name: Optional[str] = Field(None, max_length=100)
    slug: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    parent_id: Optional[str] = None  # null to remove parent


class CategoryResponse(BaseModel):
    """Schema for category response with subcategories."""

    id: str
    name: str
    slug: str
    description: Optional[str]
    parent_id: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime] = None
    subcategories: Optional[List['CategoryResponse']] = []

    class Config:
        from_attributes = True


class CategoryListResponse(BaseModel):
    """Schema for category list response."""

    categories: List[CategoryResponse]
    total: int


class CategoryDetailResponse(BaseModel):
    """Schema for detailed category response with product count."""

    id: str
    name: str
    slug: str
    description: Optional[str]
    parent_id: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime] = None
    subcategories: List[CategoryResponse] = []
    products_count: int = 0

    class Config:
        from_attributes = True


# Enable forward references for nested CategoryResponse
CategoryResponse.model_rebuild()
