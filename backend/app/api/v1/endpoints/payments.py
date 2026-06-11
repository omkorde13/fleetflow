import razorpay
import hmac
import hashlib
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import structlog

from app.db.session import get_db
from app.models.models import Payment, PaymentStatus, Delivery, DeliveryStatus, Driver, User, UserRole
from app.core.security import get_current_user, get_current_driver, get_current_admin
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


@router.post("/cod")
async def pay_cash_on_delivery(
    payload: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """Mark a completed delivery as cash-on-delivery, pending the driver's confirmation."""
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

    existing_payment = await db.execute(
        select(Payment).where(Payment.delivery_id == delivery.id)
    )
    if existing_payment.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Payment already initiated for this delivery")

    payment = Payment(
        delivery_id=delivery.id,
        user_id=current_user.id,
        amount=delivery.total_fare,
        currency="INR",
        status=PaymentStatus.PENDING,
        payment_method="CASH",
    )
    db.add(payment)
    await db.flush()

    pubsub = PubSubManager(redis)
    await pubsub.publish_notification(
        str(current_user.id),
        {
            "title": "Cash Payment Pending",
            "message": f"Your cash payment of ₹{payment.amount:.2f} is pending confirmation from the driver.",
            "event_type": "PAYMENT_PENDING",
        }
    )

    if delivery.driver_id:
        driver_result = await db.execute(select(Driver.user_id).where(Driver.id == delivery.driver_id))
        driver_user_id = driver_result.scalar_one_or_none()
        if driver_user_id:
            await pubsub.publish_notification(
                str(driver_user_id),
                {
                    "title": "Confirm Cash Received",
                    "message": f"Customer marked ₹{payment.amount:.2f} as paid in cash for delivery #{str(delivery.id)[:8].upper()}. Please confirm once received.",
                    "event_type": "CASH_PAYMENT_PENDING",
                    "delivery_id": str(delivery.id),
                    "payment_id": str(payment.id),
                }
            )

    logger.info("Cash payment pending driver confirmation", payment_id=str(payment.id), delivery_id=str(delivery.id))

    return {"message": "Cash payment recorded, pending driver confirmation", "payment_id": str(payment.id)}


@router.post("/{payment_id}/confirm-cash")
async def confirm_cash_payment(
    payment_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """Driver confirms they received the cash payment from the customer."""
    driver_result = await db.execute(select(Driver).where(Driver.user_id == current_user.id))
    driver = driver_result.scalar_one_or_none()

    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if payment.payment_method != "CASH" or payment.status != PaymentStatus.PENDING:
        raise HTTPException(status_code=400, detail="No pending cash payment to confirm")

    delivery_result = await db.execute(select(Delivery).where(Delivery.id == payment.delivery_id))
    delivery = delivery_result.scalar_one_or_none()

    if not driver or not delivery or str(delivery.driver_id) != str(driver.id):
        raise HTTPException(status_code=403, detail="Access denied")

    payment.status = PaymentStatus.SUCCESS

    pubsub = PubSubManager(redis)
    await pubsub.publish_notification(
        str(payment.user_id),
        {
            "title": "Payment Confirmed",
            "message": f"The driver confirmed receipt of your ₹{payment.amount:.2f} cash payment.",
            "event_type": "PAYMENT_SUCCESS",
        }
    )

    background_tasks.add_task(
        generate_invoice_task.delay,
        str(payment.id)
    )

    logger.info("Cash payment confirmed by driver", payment_id=str(payment.id), driver_id=str(driver.id))

    return {"message": "Cash payment confirmed", "payment_id": str(payment.id)}


@router.get("/by-delivery/{delivery_id}", response_model=Optional[PaymentResponse])
async def get_payment_by_delivery(
    delivery_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the payment record for a delivery, if one exists."""
    delivery_result = await db.execute(select(Delivery).where(Delivery.id == delivery_id))
    delivery = delivery_result.scalar_one_or_none()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")

    is_client = str(delivery.client_id) == str(current_user.id)
    is_admin = current_user.role == UserRole.ADMIN
    is_driver = False

    if current_user.role == UserRole.DRIVER and delivery.driver_id:
        driver_result = await db.execute(select(Driver).where(Driver.user_id == current_user.id))
        driver = driver_result.scalar_one_or_none()
        is_driver = driver is not None and str(delivery.driver_id) == str(driver.id)

    if not (is_client or is_driver or is_admin):
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(select(Payment).where(Payment.delivery_id == delivery_id))
    payment = result.scalar_one_or_none()
    return PaymentResponse.model_validate(payment) if payment else None


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
