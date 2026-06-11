import asyncio
from celery import shared_task
from app.workers.celery_app import celery_app
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger()

@celery_app.task(bind=True, max_retries=3)
def send_delivery_notification_task(self, delivery_id: str, client_id: str):
    """Notify nearby drivers about a new delivery."""
    try:
        asyncio.run(_notify_drivers(delivery_id, client_id))
    except Exception as exc:
        logger.error("Failed to notify drivers", delivery_id=delivery_id, error=str(exc))
        raise self.retry(exc=exc, countdown=60)

async def _notify_drivers(delivery_id: str, client_id: str):
    from app.db.session import AsyncSessionLocal, engine
    from app.services.notification_service import NotificationService
    from app.models.models import Driver, DriverStatus, Delivery
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        # Get delivery
        result = await db.execute(select(Delivery).where(Delivery.id == delivery_id))
        delivery = result.scalar_one_or_none()
        if not delivery:
            return

        # Find nearby online drivers (simplified — within 50km)
        result = await db.execute(
            select(Driver).where(
                Driver.status == DriverStatus.ONLINE,
                Driver.is_verified == True,
                Driver.is_suspended == False,
                Driver.current_lat.isnot(None),
            )
        )
        drivers = result.scalars().all()

        from haversine import haversine, Unit
        nearby_drivers = []
        for driver in drivers:
            if driver.current_lat and driver.current_lng:
                dist = haversine(
                    (delivery.pickup_lat, delivery.pickup_lng),
                    (driver.current_lat, driver.current_lng),
                    unit=Unit.KILOMETERS
                )
                if dist <= 50:
                    nearby_drivers.append(driver)

        # Notify them
        for driver in nearby_drivers[:10]:  # Cap at 10 notifications
            await NotificationService.create_notification(
                db=db,
                user_id=str(driver.user_id),
                title="New Delivery Available",
                message=f"New delivery near you! ₹{delivery.total_fare:.2f} — {delivery.pickup_address[:50]}",
                event_type="NEW_DELIVERY",
                reference_id=delivery_id,
            )

        await db.commit()
        logger.info("Notified drivers", delivery_id=delivery_id, count=len(nearby_drivers))

    await engine.dispose()

@celery_app.task(bind=True, max_retries=3)
def generate_invoice_task(self, payment_id: str):
    """Generate and store PDF invoice for a payment."""
    try:
        asyncio.run(_generate_invoice(payment_id))
    except Exception as exc:
        logger.error("Invoice generation failed", payment_id=payment_id, error=str(exc))
        raise self.retry(exc=exc, countdown=120)

async def _generate_invoice(payment_id: str):
    from app.db.session import AsyncSessionLocal, engine
    from app.models.models import Payment
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Payment)
            .options(selectinload(Payment.delivery), selectinload(Payment.user))
            .where(Payment.id == payment_id)
        )
        payment = result.scalar_one_or_none()
        if not payment:
            return

        # In production: generate actual PDF with reportlab or weasyprint
        invoice_url = f"/invoices/{payment_id}.pdf"
        payment.invoice_url = invoice_url
        await db.commit()

        logger.info("Invoice generated", payment_id=payment_id, url=invoice_url)

    await engine.dispose()

@celery_app.task
def cleanup_expired_tokens():
    """Remove expired refresh tokens."""
    asyncio.run(_cleanup_tokens())

async def _cleanup_tokens():
    from app.db.session import AsyncSessionLocal, engine
    from app.models.models import RefreshToken
    from sqlalchemy import delete

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            delete(RefreshToken).where(RefreshToken.expires_at < datetime.utcnow())
        )
        await db.commit()
        logger.info("Cleaned up expired tokens", count=result.rowcount)

    await engine.dispose()

@celery_app.task
def generate_daily_report():
    """Generate and email daily analytics report to admins."""
    asyncio.run(_daily_report())

async def _daily_report():
    from app.db.session import AsyncSessionLocal, engine
    from app.models.models import Delivery, Payment, PaymentStatus, DeliveryStatus, User, UserRole
    from app.services.notification_service import NotificationService
    from sqlalchemy import select, func
    from datetime import date

    async with AsyncSessionLocal() as db:
        today = datetime.utcnow().date()
        start = datetime.combine(today, datetime.min.time())
        end = datetime.combine(today, datetime.max.time())

        # Count deliveries today
        deliveries_today = await db.execute(
            select(func.count()).select_from(Delivery).where(
                Delivery.created_at.between(start, end)
            )
        )
        completed_today = await db.execute(
            select(func.count()).select_from(Delivery).where(
                Delivery.delivered_at.between(start, end)
            )
        )
        revenue_today = await db.execute(
            select(func.sum(Payment.amount)).where(
                Payment.status == PaymentStatus.SUCCESS,
                Payment.created_at.between(start, end)
            )
        )

        report = {
            "date": str(today),
            "deliveries_created": deliveries_today.scalar() or 0,
            "deliveries_completed": completed_today.scalar() or 0,
            "revenue": float(revenue_today.scalar() or 0),
        }

        logger.info("Daily report generated", **report)

        # Email the report to all admins
        admins_result = await db.execute(
            select(User).where(User.role == UserRole.ADMIN, User.is_active == True)
        )
        for admin in admins_result.scalars().all():
            await NotificationService.send_daily_report_email(admin.email, report)

    await engine.dispose()

@celery_app.task
def update_driver_ratings():
    """Recalculate average driver ratings."""
    asyncio.run(_update_ratings())

async def _update_ratings():
    from app.db.session import AsyncSessionLocal, engine
    from app.models.models import Driver, DriverRating
    from sqlalchemy import select, func

    async with AsyncSessionLocal() as db:
        # Get all drivers with ratings
        result = await db.execute(
            select(
                DriverRating.driver_id,
                func.avg(DriverRating.rating).label("avg_rating")
            ).group_by(DriverRating.driver_id)
        )

        for row in result:
            await db.execute(
                Driver.__table__.update()
                .where(Driver.id == row.driver_id)
                .values(rating=round(float(row.avg_rating), 2))
            )

        await db.commit()
        logger.info("Driver ratings updated")

    await engine.dispose()
