"""
Payment routes.
API endpoints for payment processing.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.middleware.auth import get_current_active_user
from app.models.user import User
from app.services.payment_service import PaymentService
from app.schemas.payment import (
    PaymentRequest,
    PaymentProcessResponse,
    PaymentResponse,
    OrderUpdateResponse
)

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/process", response_model=PaymentProcessResponse)
async def process_payment(
    request: PaymentRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Process payment for an order.

    Requires valid access token.

    - **order_id**: Order UUID (required)
    - **payment_method**: Payment provider ('stripe' or 'mock'). Defaults to env var PAYMENT_PROVIDER
    - **stripe_token**: Stripe payment token (required if payment_method='stripe')

    Updates order status to 'paid' and stores payment details.

    Errors:
    - 404: Order not found
    - 403: Order doesn't belong to user
    - 400: Order already paid, invalid payment method, missing stripe_token
    - 402: Payment failed (Stripe error or mock failure)

    Mock payment always succeeds.
    Stripe payment requires valid token from Stripe.js frontend integration.
    """
    service = PaymentService(db)

    result = service.process_payment(
        order_id=request.order_id,
        user_id=str(current_user.id),
        payment_method=request.payment_method.value if request.payment_method else None,
        stripe_token=request.stripe_token
    )

    return PaymentProcessResponse(
        payment=PaymentResponse(**result["payment"]),
        order=OrderUpdateResponse(**result["order"])
    )
