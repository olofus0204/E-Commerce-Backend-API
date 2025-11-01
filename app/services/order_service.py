"""
Order service.
Business logic for order management with status validation and stock handling.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from decimal import Decimal
from typing import Optional, Dict

from app.models.order import Order, OrderItem, OrderStatus
from app.models.cart import CartItem
from app.models.product import Product
from app.models.user import User, UserRole
from app.core.exceptions import NotFoundError, ValidationError, ConflictError, AuthorizationError
from app.utils.pagination import paginate


class OrderService:
    """Service class for order operations."""

    # Valid status transitions
    STATUS_TRANSITIONS = {
        OrderStatus.pending: [OrderStatus.processing, OrderStatus.cancelled],
        OrderStatus.processing: [OrderStatus.paid, OrderStatus.cancelled],
        OrderStatus.paid: [OrderStatus.shipped, OrderStatus.refunded],
        OrderStatus.shipped: [OrderStatus.delivered],
        OrderStatus.delivered: [OrderStatus.refunded],
        OrderStatus.cancelled: [],
        OrderStatus.refunded: []
    }

    def __init__(self, db: Session):
        self.db = db

    def get_user_orders(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20,
        status: Optional[str] = None
    ) -> Dict:
        """
        Get orders for a user with pagination.

        Args:
            user_id: User UUID
            page: Page number
            limit: Items per page
            status: Filter by order status

        Returns:
            Dict with paginated orders
        """
        query = self.db.query(Order).filter(Order.user_id == user_id)

        if status:
            query = query.filter(Order.status == status)

        query = query.order_by(Order.created_at.desc())

        result = paginate(query, page, limit)
        return result

    def get_all_orders(
        self,
        page: int = 1,
        limit: int = 20,
        status: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict:
        """
        Get all orders (admin only) with pagination.

        Args:
            page: Page number
            limit: Items per page
            status: Filter by order status
            user_id: Filter by user UUID

        Returns:
            Dict with paginated orders
        """
        query = self.db.query(Order)

        if status:
            query = query.filter(Order.status == status)

        if user_id:
            query = query.filter(Order.user_id == user_id)

        query = query.order_by(Order.created_at.desc())

        result = paginate(query, page, limit)
        return result

    def get_order_by_id(self, order_id: str, user_id: Optional[str] = None, is_admin: bool = False) -> Order:
        """
        Get order by ID.

        Args:
            order_id: Order UUID
            user_id: User UUID (for authorization)
            is_admin: Whether user is admin

        Returns:
            Order object

        Raises:
            NotFoundError: If order not found
            AuthorizationError: If order doesn't belong to user
        """
        order = self.db.query(Order).filter(Order.id == order_id).first()

        if not order:
            raise NotFoundError("Order not found")

        # Check authorization
        if not is_admin and user_id and str(order.user_id) != user_id:
            raise AuthorizationError("Order doesn't belong to user")

        return order

    def create_order_from_cart(
        self,
        user_id: str,
        shipping_address: dict,
        notes: Optional[str] = None
    ) -> Order:
        """
        Create order from user's cart items.

        Args:
            user_id: User UUID
            shipping_address: Shipping address dict
            notes: Optional order notes

        Returns:
            Created Order object

        Raises:
            ValidationError: If cart is empty
            ConflictError: If insufficient stock for any item
        """
        # Get cart items
        cart_items = self.db.query(CartItem).filter(CartItem.user_id == user_id).all()

        if not cart_items:
            raise ValidationError("Cart is empty")

        # Begin transaction for stock management
        try:
            total_amount = Decimal('0')
            order_items_data = []

            # Lock products and check stock
            for cart_item in cart_items:
                # Lock product row (SELECT FOR UPDATE)
                product = self.db.query(Product).filter(
                    Product.id == cart_item.product_id
                ).with_for_update().first()

                if not product:
                    raise NotFoundError(f"Product {cart_item.product_id} not found")

                # Check stock
                if product.stock_quantity < cart_item.quantity:
                    raise ConflictError(
                        f"Insufficient stock for {product.name}. Available: {product.stock_quantity}",
                        details={
                            "product_id": str(product.id),
                            "product_name": product.name,
                            "available_stock": product.stock_quantity,
                            "requested_quantity": cart_item.quantity
                        }
                    )

                # Decrement stock
                product.stock_quantity -= cart_item.quantity

                # Calculate total
                subtotal = cart_item.price_snapshot * cart_item.quantity
                total_amount += subtotal

                # Store order item data
                order_items_data.append({
                    "product_id": cart_item.product_id,
                    "quantity": cart_item.quantity,
                    "price_snapshot": cart_item.price_snapshot
                })

            # Create order
            order = Order(
                user_id=user_id,
                status=OrderStatus.pending,
                total_amount=total_amount,
                shipping_address=shipping_address,
                notes=notes
            )

            self.db.add(order)
            self.db.flush()  # Get order ID

            # Create order items
            for item_data in order_items_data:
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=item_data["product_id"],
                    quantity=item_data["quantity"],
                    price_snapshot=item_data["price_snapshot"]
                )
                self.db.add(order_item)

            # Clear cart
            self.db.query(CartItem).filter(CartItem.user_id == user_id).delete()

            # Commit transaction
            self.db.commit()
            self.db.refresh(order)

            return order

        except Exception as e:
            self.db.rollback()
            raise e

    def update_order_status(
        self,
        order_id: str,
        new_status: str,
        notes: Optional[str] = None
    ) -> Order:
        """
        Update order status (admin only).

        Args:
            order_id: Order UUID
            new_status: New status
            notes: Optional admin notes

        Returns:
            Updated Order object

        Raises:
            NotFoundError: If order not found
            ValidationError: If invalid status transition
        """
        order = self.get_order_by_id(order_id)

        # Validate status transition
        new_status_enum = OrderStatus(new_status)
        if not self.validate_status_transition(order.status, new_status_enum):
            raise ValidationError(
                f"Invalid status transition from {order.status.value} to {new_status}",
                details={
                    "current_status": order.status.value,
                    "requested_status": new_status,
                    "allowed_transitions": [s.value for s in self.STATUS_TRANSITIONS.get(order.status, [])]
                }
            )

        order.status = new_status_enum
        if notes:
            order.notes = notes

        self.db.commit()
        self.db.refresh(order)
        return order

    def cancel_order(self, order_id: str, user_id: Optional[str] = None, is_admin: bool = False) -> Order:
        """
        Cancel an order.

        Args:
            order_id: Order UUID
            user_id: User UUID (for authorization)
            is_admin: Whether user is admin

        Returns:
            Cancelled Order object

        Raises:
            NotFoundError: If order not found
            AuthorizationError: If order doesn't belong to user
            ValidationError: If order cannot be cancelled
        """
        order = self.get_order_by_id(order_id, user_id, is_admin)

        # Check if order can be cancelled
        if order.status not in [OrderStatus.pending, OrderStatus.processing]:
            raise ValidationError(
                "Order cannot be cancelled. Only pending or processing orders can be cancelled.",
                details={"current_status": order.status.value}
            )

        order.status = OrderStatus.cancelled
        self.db.commit()
        self.db.refresh(order)
        return order

    def validate_status_transition(self, current_status: OrderStatus, new_status: OrderStatus) -> bool:
        """
        Validate if status transition is allowed.

        Args:
            current_status: Current OrderStatus
            new_status: New OrderStatus

        Returns:
            True if transition is valid, False otherwise
        """
        allowed_statuses = self.STATUS_TRANSITIONS.get(current_status, [])
        return new_status in allowed_statuses
