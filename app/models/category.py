"""
Category database model.
Supports hierarchical categories with self-referential parent-child relationships.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Category(Base):
    """Category model for product classification with support for subcategories."""

    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Self-referential relationships for hierarchical categories
    parent = relationship("Category", remote_side=[id], back_populates="subcategories")
    subcategories = relationship("Category", back_populates="parent", cascade="all, delete-orphan")

    # Relationship with products
    products = relationship("Product", back_populates="category")
