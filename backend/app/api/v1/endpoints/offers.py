from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from typing import List, Optional
import structlog

from app.db.session import get_db
from app.models.models import Offer, User
from app.core.security import get_current_user, get_current_admin
from app.schemas import CreateOfferRequest, OfferResponse

logger = structlog.get_logger()
router = APIRouter(prefix="/offers", tags=["Offers & Coupons"])


@router.get("", response_model=List[OfferResponse])
async def list_active_offers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all active offers available to clients."""
    result = await db.execute(
        select(Offer).where(
            Offer.is_active == True,
            Offer.valid_from <= datetime.utcnow(),
            Offer.valid_until >= datetime.utcnow(),
        ).order_by(Offer.created_at.desc())
    )
    return [OfferResponse.model_validate(o) for o in result.scalars().all()]


@router.get("/validate/{code}")
async def validate_coupon(
    code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Validate a coupon code."""
    result = await db.execute(
        select(Offer).where(
            Offer.code == code.upper(),
            Offer.is_active == True,
            Offer.valid_from <= datetime.utcnow(),
            Offer.valid_until >= datetime.utcnow(),
        )
    )
    offer = result.scalar_one_or_none()
    if not offer:
        raise HTTPException(status_code=400, detail="Invalid or expired coupon code")

    if offer.usage_limit and offer.used_count >= offer.usage_limit:
        raise HTTPException(status_code=400, detail="Coupon usage limit reached")

    return OfferResponse.model_validate(offer)


@router.post("", response_model=OfferResponse, status_code=201)
async def create_offer(
    payload: CreateOfferRequest,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin creates a new offer/coupon."""
    existing = await db.execute(
        select(Offer).where(Offer.code == payload.code.upper())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Coupon code already exists")

    offer = Offer(
        code=payload.code.upper(),
        title=payload.title,
        description=payload.description,
        offer_type=payload.offer_type,
        discount_value=payload.discount_value,
        min_order_value=payload.min_order_value,
        max_discount=payload.max_discount,
        usage_limit=payload.usage_limit,
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
        is_active=True,
    )
    db.add(offer)
    await db.flush()
    return OfferResponse.model_validate(offer)


@router.patch("/{offer_id}/disable")
async def disable_offer(
    offer_id: str,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import update
    await db.execute(
        update(Offer).where(Offer.id == offer_id).values(is_active=False)
    )
    return {"message": "Offer disabled"}
