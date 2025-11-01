"""
Cart service.
Business logic for shopping cart management.
"""

from sqlalchemy.orm import Session
from decimal import Decimal
from typing import List

from app.models.cart import CartItem
from app.models.product import Product
from app.models.user import User
from app.core.exceptions import NotFoundError, ValidationError, ConflictError


class CartService:
    """Service class for shopping cart operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_user_cart(self, user_id: str) -> List[CartItem]:
        """
        Get all cart items for a user.

        Args:
            user_id: User UUID as string

        Returns:
            List of CartItem objects
        """
        cart_items = self.db.query(CartItem).filter(
            CartItem.user_id == user_id
        ).all()

        return cart_items

    def add_to_cart(
        self,
        user_id: str,
        product_id: str,
        quantity: int
    ) -> CartItem:
        """
        Add product to cart.

        Args:
            user_id: User UUID
            product_id: Product UUID
            quantity: Quantity to add

        Returns:
            Created CartItem object

        Raises:
            NotFoundError: If product not found or inactive
            ValidationError: If quantity exceeds stock
            ConflictError: If product already in cart
        """
        # Get product
        product = self.db.query(Product).filter(
            Product.id == product_id,
            Product.is_active == True
        ).first()

        if not product:
            raise NotFoundError("Product not found or inactive")

        # Check stock availability
        if product.stock_quantity < quantity:
            raise ValidationError(
                f"Insufficient stock. Available: {product.stock_quantity}",
                details={"available_stock": product.stock_quantity}
            )

        # Check if product already in cart
        existing_item = self.db.query(CartItem).filter(
            CartItem.user_id == user_id,
            CartItem.product_id == product_id
        ).first()

        if existing_item:
            raise ConflictError(
                "Product already in cart. Use PUT to update quantity.",
                details={"cart_item_id": str(existing_item.id)}
            )

        # Create cart item
        cart_item = CartItem(
            user_id=user_id,
            product_id=product_id,
            quantity=quantity,
            price_snapshot=product.price
        )

        self.db.add(cart_item)
        self.db.commit()
        self.db.refresh(cart_item)

        return cart_item

    def update_cart_item(
        self,
        cart_item_id: str,
        user_id: str,
        quantity: int
    ) -> CartItem:
        """
        Update cart item quantity.

        Args:
            cart_item_id: CartItem UUID
            user_id: User UUID (for authorization)
            quantity: New quantity

        Returns:
            Updated CartItem object

        Raises:
            NotFoundError: If cart item not found or doesn't belong to user
            ValidationError: If quantity exceeds stock
        """
        # Get cart item
        cart_item = self.db.query(CartItem).filter(
            CartItem.id == cart_item_id,
            CartItem.user_id == user_id
        ).first()

        if not cart_item:
            raise NotFoundError("Cart item not found or doesn't belong to user")

        # Check stock availability
        product = cart_item.product
        if product.stock_quantity < quantity:
            raise ValidationError(
                f"Insufficient stock. Available: {product.stock_quantity}",
                details={"available_stock": product.stock_quantity}
            )

        # Update quantity
        cart_item.quantity = quantity
        self.db.commit()
        self.db.refresh(cart_item)

        return cart_item

    def remove_from_cart(
        self,
        cart_item_id: str,
        user_id: str
    ) -> None:
        """
        Remove item from cart.

        Args:
            cart_item_id: CartItem UUID
            user_id: User UUID (for authorization)

        Raises:
            NotFoundError: If cart item not found or doesn't belong to user
        """
        cart_item = self.db.query(CartItem).filter(
            CartItem.id == cart_item_id,
            CartItem.user_id == user_id
        ).first()

        if not cart_item:
            raise NotFoundError("Cart item not found or doesn't belong to user")

        self.db.delete(cart_item)
        self.db.commit()

    def clear_cart(self, user_id: str) -> None:
        """
        Remove all items from user's cart.

        Args:
            user_id: User UUID
        """
        self.db.query(CartItem).filter(CartItem.user_id == user_id).delete()
        self.db.commit()

    def calculate_cart_totals(self, cart_items: List[CartItem]) -> dict:
        """
        Calculate cart totals.

        Args:
            cart_items: List of CartItem objects

        Returns:
            Dict with total_items and total_amount
        """
        total_items = sum(item.quantity for item in cart_items)
        total_amount = sum(item.price_snapshot * item.quantity for item in cart_items)

        return {
            "total_items": total_items,
            "total_amount": Decimal(str(total_amount))
        }
