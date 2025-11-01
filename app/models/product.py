"""
Product database model.
Handles product information, pricing, stock, and images.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, Boolean, Numeric, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class Product(Base):
    """Product model for e-commerce catalog."""

    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)  # Store price with 2 decimal precision
    stock_quantity = Column(Integer, default=0, nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    image_urls = Column(JSON, default=list, nullable=True)  # Array of image URL strings
    is_active = Column(Boolean, default=True, nullable=False)  # Soft delete / hide products
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Constraints
    __table_args__ = (
        CheckConstraint('price >= 0', name='check_price_positive'),
        CheckConstraint('stock_quantity >= 0', name='check_stock_positive'),
    )

    # Relationships
    category = relationship("Category", back_populates="products")
    cart_items = relationship("CartItem", back_populates="product")
    order_items = relationship("OrderItem", back_populates="product")
