from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List, Optional

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.models import User, Notification
from app.schemas.all_schemas import (
    UserResponse, UserUpdate, NotificationResponse,
    PricingEstimateRequest, PricingEstimateResponse,
)
from app.services.pricing_service import PricingService

router = APIRouter()
pricing_service = PricingService()


@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """Get current user's profile."""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_my_profile(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update current user profile."""
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    await db.execute(
        update(User).where(User.id == current_user.id).values(**update_data)
    )
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.get("/me/notifications", response_model=List[NotificationResponse])
async def get_my_notifications(
    unread_only: bool = False,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get notifications for current user."""
    query = select(Notification).where(Notification.user_id == current_user.id)
    if unread_only:
        query = query.where(Notification.is_read == False)  # noqa: E712
    query = query.order_by(Notification.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/me/notifications/read-all")
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark all notifications as read."""
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read == False)  # noqa: E712
        .values(is_read=True)
    )
    await db.commit()
    return {"message": "All notifications marked as read"}


@router.post("/me/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a single notification as read."""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.is_read = True
    await db.commit()
    return {"message": "Notification marked as read"}


@router.post("/pricing/estimate", response_model=PricingEstimateResponse)
async def estimate_fare(
    data: PricingEstimateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Estimate delivery fare before creating an order."""
    result = await PricingService.estimate_fare(
        pickup_lat=data.pickup_lat,
        pickup_lng=data.pickup_lng,
        dropoff_lat=data.dropoff_lat,
        dropoff_lng=data.dropoff_lng,
        coupon_code=data.coupon_code,
        db=db,
    )
    return PricingEstimateResponse(
        base_fare=result["base_fare"],
        distance_km=result["distance_km"],
        distance_fare=round(result["base_fare"] * 0.6, 2),  # approximate split
        weather_condition=result["weather_condition"].value,
        weather_multiplier=result["weather_multiplier"],
        surge_multiplier=result["surge_multiplier"],
        subtotal=result["subtotal"],
        discount=result.get("discount_amount", 0.0),
        total_fare=result["total_fare"],
        currency="INR",
    )
