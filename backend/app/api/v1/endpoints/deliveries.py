from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime
import secrets
import structlog

from app.db.session import get_db
from app.models.models import (
    Delivery, DeliveryStatus, Driver, DriverStatus,
    User, UserRole, Payment, PaymentStatus, Offer, OfferUsage, DriverRating
)
from app.core.security import get_current_user, get_current_admin, get_current_active_client
from app.core.redis import get_redis, PubSubManager
from app.schemas.delivery import (
    CreateDeliveryRequest, DeliveryResponse, DeliveryListResponse,
    AssignDriverRequest, UpdateDeliveryStatusRequest, CancelDeliveryRequest, RateDeliveryRequest,
    ConfirmPickupRequest, CompleteDeliveryRequest
)
from app.services.pricing_service import PricingService
from app.services.notification_service import NotificationService
from app.workers.tasks import send_delivery_notification_task

logger = structlog.get_logger()
router = APIRouter(prefix="/deliveries", tags=["Deliveries"])


def _to_delivery_response(delivery: Delivery, role: UserRole) -> DeliveryResponse:
    """Serialize a delivery, hiding OTPs from anyone but the client (drivers
    must obtain them verbally to verify pickup/delivery)."""
    response = DeliveryResponse.model_validate(delivery)
    if role != UserRole.CLIENT:
        response.pickup_otp = None
        response.delivery_otp = None
    return response


@router.post("", response_model=DeliveryResponse, status_code=201)
async def create_delivery(
    payload: CreateDeliveryRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_client),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    # Validate coupon if provided
    offer = None
    discount_amount = 0.0
    if payload.coupon_code:
        offer_result = await db.execute(
            select(Offer).where(
                Offer.code == payload.coupon_code.upper(),
                Offer.is_active == True,
                Offer.valid_from <= datetime.utcnow(),
                Offer.valid_until >= datetime.utcnow(),
            )
        )
        offer = offer_result.scalar_one_or_none()
        if not offer:
            raise HTTPException(status_code=400, detail="Invalid or expired coupon code")

        if offer.usage_limit and offer.used_count >= offer.usage_limit:
            raise HTTPException(status_code=400, detail="Coupon usage limit reached")

    # Calculate pricing
    pricing = await PricingService.calculate_fare(
        pickup_lat=payload.pickup_lat,
        pickup_lng=payload.pickup_lng,
        dropoff_lat=payload.dropoff_lat,
        dropoff_lng=payload.dropoff_lng,
        offer=offer,
    )

    delivery = Delivery(
        client_id=current_user.id,
        pickup_address=payload.pickup_address,
        pickup_lat=payload.pickup_lat,
        pickup_lng=payload.pickup_lng,
        pickup_contact_name=payload.pickup_contact_name,
        pickup_contact_phone=payload.pickup_contact_phone,
        dropoff_address=payload.dropoff_address,
        dropoff_lat=payload.dropoff_lat,
        dropoff_lng=payload.dropoff_lng,
        dropoff_contact_name=payload.dropoff_contact_name,
        dropoff_contact_phone=payload.dropoff_contact_phone,
        parcel_description=payload.parcel_description,
        parcel_weight=payload.parcel_weight,
        special_instructions=payload.special_instructions,
        distance_km=pricing["distance_km"],
        base_fare=pricing["base_fare"],
        weather_multiplier=pricing["weather_multiplier"],
        surge_multiplier=pricing["surge_multiplier"],
        discount_amount=pricing["discount_amount"],
        total_fare=pricing["total_fare"],
        weather_condition=pricing["weather_condition"],
        coupon_code=payload.coupon_code,
        offer_id=offer.id if offer else None,
        status=DeliveryStatus.PENDING,
        pickup_otp=f"{secrets.randbelow(10000):04d}",
        delivery_otp=f"{secrets.randbelow(10000):04d}",
    )
    db.add(delivery)
    await db.flush()
    await db.refresh(delivery)

    # New delivery has no driver/payment/rating yet — set explicitly to
    # avoid lazy-loading these relationships in an async context
    delivery.driver = None
    delivery.payment = None
    delivery.rating = None

    # Track coupon usage
    if offer:
        offer.used_count += 1
        usage = OfferUsage(
            offer_id=offer.id,
            user_id=current_user.id,
            delivery_id=delivery.id,
            discount_applied=pricing["discount_amount"],
        )
        db.add(usage)

    # Publish to Redis for real-time notification
    pubsub = PubSubManager(redis)
    await pubsub.publish_delivery_update(
        str(delivery.id), "PENDING",
        {"message": "New delivery created"}
    )

    # Background: notify available drivers
    background_tasks.add_task(
        send_delivery_notification_task.delay,
        str(delivery.id), str(current_user.id)
    )

    # Background: email order confirmation to the client
    background_tasks.add_task(
        NotificationService.send_order_placed_email,
        current_user.email, current_user.full_name, str(delivery.id),
        delivery.pickup_address, delivery.dropoff_address, delivery.total_fare,
    )

    logger.info("Delivery created", delivery_id=str(delivery.id), client_id=str(current_user.id))
    return DeliveryResponse.model_validate(delivery)


@router.get("", response_model=DeliveryListResponse)
async def list_deliveries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[DeliveryStatus] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Delivery).options(
        selectinload(Delivery.driver).selectinload(Driver.user),
        selectinload(Delivery.payment),
        selectinload(Delivery.rating),
    )

    # Filter based on role
    if current_user.role == UserRole.CLIENT:
        query = query.where(Delivery.client_id == current_user.id)
    elif current_user.role == UserRole.DRIVER:
        driver_result = await db.execute(
            select(Driver).where(Driver.user_id == current_user.id)
        )
        driver = driver_result.scalar_one_or_none()
        if not driver:
            raise HTTPException(status_code=404, detail="Driver profile not found")
        if status == DeliveryStatus.PENDING:
            # Pending deliveries are unassigned — show all available to claim
            query = query.where(Delivery.driver_id.is_(None))
        else:
            query = query.where(Delivery.driver_id == driver.id)
    # Admin sees all

    if status:
        query = query.where(Delivery.status == status)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # Paginate
    query = query.order_by(Delivery.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    deliveries = result.scalars().all()

    return DeliveryListResponse(
        deliveries=[_to_delivery_response(d, current_user.role) for d in deliveries],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{delivery_id}", response_model=DeliveryResponse)
async def get_delivery(
    delivery_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Delivery)
        .options(
            selectinload(Delivery.driver).selectinload(Driver.user),
            selectinload(Delivery.payment),
            selectinload(Delivery.rating),
        )
        .where(Delivery.id == delivery_id)
    )
    delivery = result.scalar_one_or_none()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")

    # Access control
    if current_user.role == UserRole.CLIENT and str(delivery.client_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    return _to_delivery_response(delivery, current_user.role)


@router.post("/{delivery_id}/cancel")
async def cancel_delivery(
    delivery_id: str,
    payload: CancelDeliveryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    result = await db.execute(select(Delivery).where(Delivery.id == delivery_id))
    delivery = result.scalar_one_or_none()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")

    if current_user.role == UserRole.CLIENT and str(delivery.client_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    if delivery.status in [DeliveryStatus.DELIVERED, DeliveryStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel delivery in {delivery.status} state")

    delivery.status = DeliveryStatus.CANCELLED
    delivery.cancelled_at = datetime.utcnow()
    delivery.cancellation_reason = payload.reason

    # Free up driver if assigned
    if delivery.driver_id:
        driver_result = await db.execute(
            select(Driver).where(Driver.id == delivery.driver_id)
        )
        driver = driver_result.scalar_one_or_none()
        if driver and driver.status in [DriverStatus.BUSY, DriverStatus.ON_DELIVERY]:
            driver.status = DriverStatus.ONLINE

    pubsub = PubSubManager(redis)
    await pubsub.publish_delivery_update(
        str(delivery.id), "CANCELLED",
        {"reason": payload.reason}
    )

    return {"message": "Delivery cancelled", "delivery_id": delivery_id}


@router.post("/{delivery_id}/accept")
async def accept_delivery(
    delivery_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """Driver accepts a pending delivery."""
    driver_result = await db.execute(
        select(Driver).where(Driver.user_id == current_user.id)
    )
    driver = driver_result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")

    if driver.status not in [DriverStatus.ONLINE]:
        raise HTTPException(status_code=400, detail="Driver must be ONLINE to accept deliveries")

    result = await db.execute(select(Delivery).where(Delivery.id == delivery_id))
    delivery = result.scalar_one_or_none()
    if not delivery or delivery.status != DeliveryStatus.PENDING:
        raise HTTPException(status_code=400, detail="Delivery not available")

    delivery.driver_id = driver.id
    delivery.status = DeliveryStatus.ASSIGNED
    delivery.assigned_at = datetime.utcnow()
    driver.status = DriverStatus.BUSY

    pubsub = PubSubManager(redis)
    await pubsub.publish_delivery_update(
        str(delivery.id), "ASSIGNED",
        {"driver_id": str(driver.id)}
    )

    return {"message": "Delivery accepted", "delivery_id": delivery_id}


@router.post("/{delivery_id}/pickup")
async def confirm_pickup(
    delivery_id: str,
    payload: ConfirmPickupRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """Driver confirms pickup using the OTP shared by the client."""
    driver_result = await db.execute(
        select(Driver).where(Driver.user_id == current_user.id)
    )
    driver = driver_result.scalar_one_or_none()

    result = await db.execute(select(Delivery).where(Delivery.id == delivery_id))
    delivery = result.scalar_one_or_none()

    if not delivery or str(delivery.driver_id) != str(driver.id):
        raise HTTPException(status_code=403, detail="Access denied")

    if delivery.status != DeliveryStatus.ASSIGNED:
        raise HTTPException(status_code=400, detail=f"Invalid status transition from {delivery.status}")

    if payload.otp != delivery.pickup_otp:
        raise HTTPException(status_code=400, detail="Invalid pickup OTP")

    delivery.status = DeliveryStatus.PICKED_UP
    delivery.picked_up_at = datetime.utcnow()
    driver.status = DriverStatus.ON_DELIVERY

    pubsub = PubSubManager(redis)
    await pubsub.publish_delivery_update(str(delivery.id), "PICKED_UP", {})

    return {"message": "Pickup confirmed"}


@router.post("/{delivery_id}/complete")
async def complete_delivery(
    delivery_id: str,
    payload: CompleteDeliveryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """Driver marks delivery as complete using the OTP shared by the customer."""
    driver_result = await db.execute(
        select(Driver).where(Driver.user_id == current_user.id)
    )
    driver = driver_result.scalar_one_or_none()

    result = await db.execute(select(Delivery).where(Delivery.id == delivery_id))
    delivery = result.scalar_one_or_none()

    if not delivery or str(delivery.driver_id) != str(driver.id):
        raise HTTPException(status_code=403, detail="Access denied")

    if delivery.status not in [DeliveryStatus.PICKED_UP, DeliveryStatus.IN_TRANSIT]:
        raise HTTPException(status_code=400, detail=f"Cannot complete from status {delivery.status}")

    if payload.otp != delivery.delivery_otp:
        raise HTTPException(status_code=400, detail="Invalid delivery OTP")

    delivery.status = DeliveryStatus.DELIVERED
    delivery.delivered_at = datetime.utcnow()
    driver.status = DriverStatus.ONLINE
    driver.total_deliveries = (driver.total_deliveries or 0) + 1

    pubsub = PubSubManager(redis)
    await pubsub.publish_delivery_update(str(delivery.id), "DELIVERED", {})

    # Notify client
    await pubsub.publish_notification(
        str(delivery.client_id),
        {"title": "Delivery Complete", "message": f"Your delivery #{delivery_id[:8]} has been delivered!"}
    )

    return {"message": "Delivery completed"}


@router.post("/{delivery_id}/rate")
async def rate_delivery(
    delivery_id: str,
    payload: RateDeliveryRequest,
    current_user: User = Depends(get_current_active_client),
    db: AsyncSession = Depends(get_db),
):
    """Client rates the driver for a completed delivery."""
    result = await db.execute(select(Delivery).where(Delivery.id == delivery_id))
    delivery = result.scalar_one_or_none()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")

    if str(delivery.client_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    if delivery.status != DeliveryStatus.DELIVERED:
        raise HTTPException(status_code=400, detail="Can only rate completed deliveries")

    if not delivery.driver_id:
        raise HTTPException(status_code=400, detail="Delivery has no assigned driver")

    existing = await db.execute(
        select(DriverRating).where(DriverRating.delivery_id == delivery.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Delivery already rated")

    rating = DriverRating(
        driver_id=delivery.driver_id,
        client_id=current_user.id,
        delivery_id=delivery.id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(rating)
    await db.flush()

    avg_result = await db.execute(
        select(func.avg(DriverRating.rating)).where(DriverRating.driver_id == delivery.driver_id)
    )
    avg_rating = avg_result.scalar()

    driver_result = await db.execute(select(Driver).where(Driver.id == delivery.driver_id))
    driver = driver_result.scalar_one_or_none()
    if driver and avg_rating is not None:
        driver.rating = round(float(avg_rating), 2)

    logger.info("Driver rated", delivery_id=delivery_id, driver_id=str(delivery.driver_id), rating=payload.rating)

    return {"message": "Rating submitted successfully"}


@router.post("/{delivery_id}/assign", dependencies=[Depends(get_current_admin)])
async def assign_driver(
    delivery_id: str,
    payload: AssignDriverRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """Admin assigns a driver to a delivery."""
    result = await db.execute(select(Delivery).where(Delivery.id == delivery_id))
    delivery = result.scalar_one_or_none()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")

    driver_result = await db.execute(select(Driver).where(Driver.id == payload.driver_id))
    driver = driver_result.scalar_one_or_none()
    if not driver or driver.status not in [DriverStatus.ONLINE]:
        raise HTTPException(status_code=400, detail="Driver not available")

    delivery.driver_id = driver.id
    delivery.status = DeliveryStatus.ASSIGNED
    delivery.assigned_at = datetime.utcnow()
    driver.status = DriverStatus.BUSY

    pubsub = PubSubManager(redis)
    await pubsub.publish_delivery_update(str(delivery.id), "ASSIGNED", {"driver_id": payload.driver_id})

    return {"message": "Driver assigned successfully"}
