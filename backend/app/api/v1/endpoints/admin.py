from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text
from datetime import datetime, timedelta
from typing import Optional
import structlog

from app.db.session import get_db
from app.models.models import (
    User, Driver, Delivery, Payment, Offer, OfferUsage,
    DeliveryStatus, PaymentStatus, DriverStatus, UserRole
)
from app.core.security import get_current_admin

logger = structlog.get_logger()
router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard")
async def get_dashboard(
    current_user=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Main admin analytics dashboard metrics."""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Total counts
    total_users = (await db.execute(
        select(func.count()).select_from(User).where(User.role == UserRole.CLIENT)
    )).scalar()

    total_drivers = (await db.execute(
        select(func.count()).select_from(Driver)
    )).scalar()

    active_drivers = (await db.execute(
        select(func.count()).select_from(Driver).where(
            Driver.status.in_([DriverStatus.ONLINE, DriverStatus.BUSY, DriverStatus.ON_DELIVERY])
        )
    )).scalar()

    active_deliveries = (await db.execute(
        select(func.count()).select_from(Delivery).where(
            Delivery.status.in_([
                DeliveryStatus.PENDING, DeliveryStatus.ASSIGNED,
                DeliveryStatus.PICKED_UP, DeliveryStatus.IN_TRANSIT
            ])
        )
    )).scalar()

    completed_deliveries = (await db.execute(
        select(func.count()).select_from(Delivery).where(
            Delivery.status == DeliveryStatus.DELIVERED
        )
    )).scalar()

    total_revenue = (await db.execute(
        select(func.sum(Payment.amount)).where(Payment.status == PaymentStatus.SUCCESS)
    )).scalar() or 0.0

    today_revenue = (await db.execute(
        select(func.sum(Payment.amount)).where(
            Payment.status == PaymentStatus.SUCCESS,
            Payment.created_at >= today_start
        )
    )).scalar() or 0.0

    today_deliveries = (await db.execute(
        select(func.count()).select_from(Delivery).where(
            Delivery.created_at >= today_start
        )
    )).scalar()

    # Offer usage stats
    top_offers = (await db.execute(
        select(Offer.code, Offer.title, Offer.used_count)
        .order_by(Offer.used_count.desc())
        .limit(5)
    )).all()

    return {
        "metrics": {
            "total_users": total_users,
            "total_drivers": total_drivers,
            "active_drivers": active_drivers,
            "active_deliveries": active_deliveries,
            "completed_deliveries": completed_deliveries,
            "total_revenue": round(float(total_revenue), 2),
            "today_revenue": round(float(today_revenue), 2),
            "today_deliveries": today_deliveries,
        },
        "top_offers": [
            {"code": o.code, "title": o.title, "used_count": o.used_count}
            for o in top_offers
        ],
    }


@router.get("/reports/revenue")
async def revenue_report(
    period: str = Query("daily", enum=["daily", "weekly", "monthly"]),
    current_user=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Revenue breakdown by time period."""
    now = datetime.utcnow()

    if period == "daily":
        # Last 30 days
        result = await db.execute(text("""
            SELECT
                DATE(created_at) as date,
                COUNT(*) as transactions,
                SUM(amount) as revenue
            FROM payments
            WHERE status = 'SUCCESS'
              AND created_at >= NOW() - INTERVAL '30 days'
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """))
    elif period == "weekly":
        result = await db.execute(text("""
            SELECT
                DATE_TRUNC('week', created_at) as week,
                COUNT(*) as transactions,
                SUM(amount) as revenue
            FROM payments
            WHERE status = 'SUCCESS'
              AND created_at >= NOW() - INTERVAL '12 weeks'
            GROUP BY DATE_TRUNC('week', created_at)
            ORDER BY week DESC
        """))
    else:  # monthly
        result = await db.execute(text("""
            SELECT
                DATE_TRUNC('month', created_at) as month,
                COUNT(*) as transactions,
                SUM(amount) as revenue
            FROM payments
            WHERE status = 'SUCCESS'
              AND created_at >= NOW() - INTERVAL '12 months'
            GROUP BY DATE_TRUNC('month', created_at)
            ORDER BY month DESC
        """))

    rows = result.fetchall()
    return {
        "period": period,
        "data": [
            {
                "date": str(row[0]),
                "transactions": row[1],
                "revenue": round(float(row[2] or 0), 2)
            }
            for row in rows
        ]
    }


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(User)
    if role:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)

    total = (await db.execute(
        select(func.count()).select_from(query.subquery())
    )).scalar()

    query = query.offset((page - 1) * page_size).limit(page_size)
    users = (await db.execute(query)).scalars().all()

    return {
        "users": [
            {
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": str(u.created_at),
                "last_login": str(u.last_login) if u.last_login else None,
            }
            for u in users
        ],
        "total": total,
        "page": page,
    }


@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    is_active: bool,
    current_user=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import update
    await db.execute(
        update(User).where(User.id == user_id).values(is_active=is_active)
    )
    action = "activated" if is_active else "deactivated"
    return {"message": f"User {action} successfully"}


@router.get("/drivers")
async def list_drivers(
    status: Optional[str] = None,
    is_verified: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.orm import selectinload
    query = select(Driver).options(selectinload(Driver.user))
    if status:
        query = query.where(Driver.status == status)
    if is_verified is not None:
        query = query.where(Driver.is_verified == is_verified)

    total = (await db.execute(
        select(func.count()).select_from(query.subquery())
    )).scalar()

    query = query.offset((page - 1) * page_size).limit(page_size)
    drivers = (await db.execute(query)).scalars().all()

    return {
        "drivers": [
            {
                "id": str(d.id),
                "user": {"email": d.user.email, "full_name": d.user.full_name},
                "vehicle_number": d.vehicle_number,
                "vehicle_type": d.vehicle_type,
                "status": d.status,
                "is_verified": d.is_verified,
                "rating": d.rating,
                "total_deliveries": d.total_deliveries,
                "current_lat": d.current_lat,
                "current_lng": d.current_lng,
            }
            for d in drivers
        ],
        "total": total,
    }


@router.patch("/drivers/{driver_id}/verify")
async def verify_driver(
    driver_id: str,
    current_user=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import update
    await db.execute(
        update(Driver).where(Driver.id == driver_id).values(is_verified=True)
    )
    return {"message": "Driver verified"}


@router.patch("/drivers/{driver_id}/suspend")
async def suspend_driver(
    driver_id: str,
    current_user=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import update
    await db.execute(
        update(Driver)
        .where(Driver.id == driver_id)
        .values(is_suspended=True, status=DriverStatus.OFFLINE)
    )
    return {"message": "Driver suspended"}
