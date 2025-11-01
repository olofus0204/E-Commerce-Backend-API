"""
CartItem database model.
Manages shopping cart items for authenticated users.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class CartItem(Base):
    """Cart item model for user shopping carts."""

    __tablename__ = "cart_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    price_snapshot = Column(Numeric(10, 2), nullable=False)  # Price at time of adding to cart
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'product_id', name='unique_user_product_cart'),
        CheckConstraint('quantity > 0', name='check_cart_quantity_positive'),
    )

    # Relationships
    user = relationship("User", back_populates="cart_items")
    product = relationship("Product", back_populates="cart_items")
