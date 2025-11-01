"""
Payment service.
Business logic for payment processing with Stripe and Mock providers.
"""

from abc import ABC, abstractmethod
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import datetime
import time
import uuid
from typing import Optional

from app.models.order import Order, OrderStatus
from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError, PaymentError, AuthorizationError

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False


class PaymentProvider(ABC):
    """Abstract base class for payment providers."""

    @abstractmethod
    def process_payment(self, order: Order, **kwargs) -> dict:
        """
        Process payment for an order.

        Args:
            order: Order object
            **kwargs: Provider-specific parameters

        Returns:
            dict with payment_id and status
        """
        pass


class StripeProvider(PaymentProvider):
    """Stripe payment provider implementation."""

    def __init__(self):
        if not STRIPE_AVAILABLE:
            raise ImportError("Stripe library not installed. Run: pip install stripe")

        if not settings.STRIPE_SECRET_KEY:
            raise ValueError("STRIPE_SECRET_KEY not configured")

        stripe.api_key = settings.STRIPE_SECRET_KEY

    def process_payment(self, order: Order, stripe_token: str = None, **kwargs) -> dict:
        """
        Process payment with Stripe.

        Args:
            order: Order object
            stripe_token: Stripe token from frontend

        Returns:
            dict with payment_id and status

        Raises:
            ValidationError: If stripe_token is missing
            PaymentError: If payment fails
        """
        if not stripe_token:
            raise ValidationError("stripe_token is required for Stripe payments")

        try:
            # Convert amount to cents (Stripe uses smallest currency unit)
            amount_cents = int(order.total_amount * 100)

            # Create payment intent
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency="usd",
                payment_method=stripe_token,
                confirm=True,
                description=f"Order {order.id}",
                metadata={
                    "order_id": str(order.id),
                    "user_id": str(order.user_id)
                }
            )

            if payment_intent.status == "succeeded":
                return {
                    "payment_id": payment_intent.id,
                    "status": "paid"
                }
            else:
                raise PaymentError(
                    f"Payment failed with status: {payment_intent.status}",
                    details={"stripe_status": payment_intent.status}
                )

        except stripe.error.CardError as e:
            # Card was declined
            raise PaymentError(
                f"Card declined: {e.user_message}",
                details={"stripe_error": str(e)}
            )
        except stripe.error.StripeError as e:
            # Other Stripe errors
            raise PaymentError(
                f"Payment processing failed: {str(e)}",
                details={"stripe_error": str(e)}
            )


class MockProvider(PaymentProvider):
    """Mock payment provider for testing and development."""

    def process_payment(self, order: Order, **kwargs) -> dict:
        """
        Mock payment processing (always succeeds).

        Args:
            order: Order object

        Returns:
            dict with payment_id and status
        """
        # Simulate processing delay
        time.sleep(0.5)

        # Generate mock payment ID
        payment_id = f"mock_{uuid.uuid4().hex[:16]}"

        # Mock payment always succeeds
        return {
            "payment_id": payment_id,
            "status": "paid"
        }


class PaymentService:
    """Service class for payment operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_payment_provider(self, provider_name: Optional[str] = None) -> PaymentProvider:
        """
        Get payment provider instance based on configuration.

        Args:
            provider_name: Provider name ('stripe' or 'mock'). Defaults to env var.

        Returns:
            PaymentProvider instance

        Raises:
            ValueError: If provider not supported
        """
        if not provider_name:
            provider_name = settings.PAYMENT_PROVIDER

        provider_name = provider_name.lower()

        if provider_name == "stripe":
            return StripeProvider()
        elif provider_name == "mock":
            return MockProvider()
        else:
            raise ValueError(f"Unsupported payment provider: {provider_name}")

    def process_payment(
        self,
        order_id: str,
        user_id: str,
        payment_method: Optional[str] = None,
        stripe_token: Optional[str] = None
    ) -> dict:
        """
        Process payment for an order.

        Args:
            order_id: Order UUID
            user_id: User UUID (for authorization)
            payment_method: Payment provider ('stripe' or 'mock')
            stripe_token: Stripe token (required for Stripe)

        Returns:
            dict with payment details and updated order

        Raises:
            NotFoundError: If order not found
            AuthorizationError: If order doesn't belong to user
            ValidationError: If order already paid
            PaymentError: If payment processing fails
        """
        # Get order
        order = self.db.query(Order).filter(Order.id == order_id).first()

        if not order:
            raise NotFoundError("Order not found")

        # Check authorization
        if str(order.user_id) != user_id:
            raise AuthorizationError("Order doesn't belong to user")

        # Check if already paid
        if order.status == OrderStatus.paid:
            raise ValidationError("Order already paid")

        # Check if order is in valid status for payment
        if order.status not in [OrderStatus.pending, OrderStatus.processing]:
            raise ValidationError(
                f"Order cannot be paid. Current status: {order.status.value}",
                details={"current_status": order.status.value}
            )

        # Get payment provider
        provider = self.get_payment_provider(payment_method)

        try:
            # Process payment
            payment_result = provider.process_payment(
                order=order,
                stripe_token=stripe_token
            )

            # Update order
            order.status = OrderStatus.paid
            order.payment_method = payment_method or settings.PAYMENT_PROVIDER
            order.payment_id = payment_result["payment_id"]

            self.db.commit()
            self.db.refresh(order)

            return {
                "payment": {
                    "id": payment_result["payment_id"],
                    "order_id": str(order.id),
                    "status": payment_result["status"],
                    "payment_method": order.payment_method,
                    "amount": order.total_amount,
                    "created_at": datetime.utcnow()
                },
                "order": {
                    "id": str(order.id),
                    "status": order.status.value,
                    "updated_at": order.updated_at
                }
            }

        except Exception as e:
            self.db.rollback()
            raise e
