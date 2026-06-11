import razorpay
import hmac
import hashlib
import json
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import structlog

from app.db.session import get_db
from app.models.models import Payment, PaymentStatus, Delivery, DeliveryStatus, User
from app.core.security import get_current_user, get_current_admin
from app.core.config import settings
from app.core.redis import get_redis, PubSubManager
from app.schemas.payment import (
    CreateOrderRequest, CreateOrderResponse,
    VerifyPaymentRequest, PaymentResponse, PaymentListResponse
)
from app.services.notification_service import NotificationService
from app.workers.tasks import generate_invoice_task

logger = structlog.get_logger()
router = APIRouter(prefix="/payments", tags=["Payments"])


def get_razorpay_client():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


@router.post("/orders", response_model=CreateOrderResponse)
async def create_payment_order(
    payload: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Razorpay order for a delivery."""
    result = await db.execute(
        select(Delivery).where(Delivery.id == payload.delivery_id)
    )
    delivery = result.scalar_one_or_none()

    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")

    if str(delivery.client_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    if delivery.status != DeliveryStatus.DELIVERED:
        raise HTTPException(status_code=400, detail="Delivery must be completed before payment")

    # Check if payment already exists
    existing_payment = await db.execute(
        select(Payment).where(
            Payment.delivery_id == delivery.id,
            Payment.status == PaymentStatus.SUCCESS
        )
    )
    if existing_payment.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Payment already completed for this delivery")

    # Create Razorpay order
    client = get_razorpay_client()
    amount_paise = int(delivery.total_fare * 100)  # Convert to paise

    rz_order = client.order.create({
        "amount": amount_paise,
        "currency": "INR",
        "receipt": f"fleetflow_{str(delivery.id)[:8]}",
        "notes": {
            "delivery_id": str(delivery.id),
            "user_id": str(current_user.id),
        }
    })

    # Create payment record
    payment = Payment(
        delivery_id=delivery.id,
        user_id=current_user.id,
        amount=delivery.total_fare,
        currency="INR",
        status=PaymentStatus.PENDING,
        razorpay_order_id=rz_order["id"],
    )
    db.add(payment)

    logger.info(
        "Payment order created",
        order_id=rz_order["id"],
        delivery_id=str(delivery.id),
        amount=delivery.total_fare,
    )

    return CreateOrderResponse(
        razorpay_order_id=rz_order["id"],
        amount=amount_paise,
        currency="INR",
        key=settings.RAZORPAY_KEY_ID,
        delivery_id=delivery.id,
    )


@router.post("/verify")
async def verify_payment(
    payload: VerifyPaymentRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """Verify Razorpay payment signature and update status."""

    # Verify signature
    expected_signature = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        f"{payload.razorpay_order_id}|{payload.razorpay_payment_id}".encode(),
        hashlib.sha256
    ).hexdigest()

    if expected_signature != payload.razorpay_signature:
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    # Update payment
    result = await db.execute(
        select(Payment).where(Payment.razorpay_order_id == payload.razorpay_order_id)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    payment.status = PaymentStatus.SUCCESS
    payment.razorpay_payment_id = payload.razorpay_payment_id
    payment.razorpay_signature = payload.razorpay_signature
    payment.payment_method = payload.payment_method

    # Notify via WebSocket
    pubsub = PubSubManager(redis)
    await pubsub.publish_notification(
        str(current_user.id),
        {
            "title": "Payment Successful",
            "message": f"Payment of ₹{payment.amount:.2f} received successfully!",
            "event_type": "PAYMENT_SUCCESS",
        }
    )

    # Generate invoice in background
    background_tasks.add_task(
        generate_invoice_task.delay,
        str(payment.id)
    )

    logger.info("Payment verified", payment_id=str(payment.id), amount=payment.amount)

    return {"message": "Payment verified successfully", "payment_id": str(payment.id)}


@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle Razorpay webhook events."""
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    # Verify webhook signature
    expected = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    if expected != signature:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event = json.loads(body)
    event_type = event.get("event")

    logger.info("Razorpay webhook received", event_type=event_type)

    if event_type == "payment.failed":
        payment_data = event["payload"]["payment"]["entity"]
        order_id = payment_data.get("order_id")

        result = await db.execute(
            select(Payment).where(Payment.razorpay_order_id == order_id)
        )
        payment = result.scalar_one_or_none()
        if payment:
            payment.status = PaymentStatus.FAILED
            payment.metadata = {"failure_reason": payment_data.get("error_description")}

    elif event_type == "refund.processed":
        refund_data = event["payload"]["refund"]["entity"]
        payment_id = refund_data.get("payment_id")

        result = await db.execute(
            select(Payment).where(Payment.razorpay_payment_id == payment_id)
        )
        payment = result.scalar_one_or_none()
        if payment:
            payment.status = PaymentStatus.REFUNDED
            payment.refund_id = refund_data.get("id")
            payment.refunded_at = datetime.utcnow()

    return {"status": "ok"}


@router.get("/history", response_model=PaymentListResponse)
async def payment_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Payment)
        .options(selectinload(Payment.delivery))
        .where(Payment.user_id == current_user.id)
        .order_by(Payment.created_at.desc())
    )
    payments = result.scalars().all()
    return PaymentListResponse(
        payments=[PaymentResponse.model_validate(p) for p in payments]
    )


@router.post("/{payment_id}/refund", dependencies=[Depends(get_current_admin)])
async def process_refund(
    payment_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Admin processes a refund."""
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if payment.status != PaymentStatus.SUCCESS:
        raise HTTPException(status_code=400, detail="Can only refund successful payments")

    client = get_razorpay_client()
    refund = client.payment.refund(
        payment.razorpay_payment_id,
        {"amount": int(payment.amount * 100)}
    )

    payment.refund_id = refund["id"]
    payment.status = PaymentStatus.REFUNDED
    payment.refunded_at = datetime.utcnow()

    logger.info("Refund processed", payment_id=payment_id, refund_id=refund["id"])
    return {"message": "Refund processed", "refund_id": refund["id"]}
