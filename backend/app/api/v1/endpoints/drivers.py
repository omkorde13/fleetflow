from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import structlog

from app.db.session import get_db
from app.models.models import Driver, DriverStatus, User
from app.core.security import get_current_user, get_current_driver
from app.schemas import CreateDriverProfileRequest, DriverResponse

logger = structlog.get_logger()
router = APIRouter(prefix="/drivers", tags=["Drivers"])


@router.post("/profile", response_model=DriverResponse, status_code=201)
async def create_driver_profile(
    payload: CreateDriverProfileRequest,
    current_user: User = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db),
):
    """Create driver profile (called after driver registration)."""
    existing = await db.execute(
        select(Driver).where(Driver.user_id == current_user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Driver profile already exists")

    driver = Driver(
        user_id=current_user.id,
        license_number=payload.license_number,
        vehicle_type=payload.vehicle_type,
        vehicle_number=payload.vehicle_number,
        vehicle_model=payload.vehicle_model,
        status=DriverStatus.OFFLINE,
        is_verified=False,
    )
    db.add(driver)
    await db.flush()
    return DriverResponse.model_validate(driver)


@router.get("/profile/me", response_model=DriverResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Driver).where(Driver.user_id == current_user.id))
    driver = result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    return DriverResponse.model_validate(driver)


@router.patch("/status")
async def update_driver_status(
    status: DriverStatus,
    current_user: User = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Driver).where(Driver.user_id == current_user.id))
    driver = result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")

    if not driver.is_verified:
        raise HTTPException(status_code=403, detail="Driver must be verified before going online")

    if driver.is_suspended:
        raise HTTPException(status_code=403, detail="Driver is suspended")

    # Can't manually set ON_DELIVERY
    if status == DriverStatus.ON_DELIVERY:
        raise HTTPException(status_code=400, detail="Status is managed automatically during deliveries")

    driver.status = status
    return {"message": f"Status updated to {status.value}"}


@router.get("/nearby")
async def get_nearby_drivers(
    lat: float,
    lng: float,
    radius_km: float = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get available drivers within radius."""
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
    nearby = []
    for driver in drivers:
        if driver.current_lat and driver.current_lng:
            distance = haversine(
                (lat, lng),
                (driver.current_lat, driver.current_lng),
                unit=Unit.KILOMETERS
            )
            if distance <= radius_km:
                nearby.append({
                    "driver_id": str(driver.id),
                    "current_lat": driver.current_lat,
                    "current_lng": driver.current_lng,
                    "vehicle_type": driver.vehicle_type,
                    "rating": driver.rating,
                    "distance_km": round(distance, 2),
                })

    nearby.sort(key=lambda x: x["distance_km"])
    return {"drivers": nearby}


@router.post("/documents")
async def upload_document(
    document_type: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db),
):
    """Upload driver verification documents."""
    result = await db.execute(select(Driver).where(Driver.user_id == current_user.id))
    driver = result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")

    # In production: upload to S3/GCS and store URL
    allowed_types = ["license_front", "license_back", "vehicle_rc", "insurance", "photo"]
    if document_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Invalid document type. Allowed: {allowed_types}")

    # Simulate storing document URL
    doc_url = f"/documents/{str(driver.id)}/{document_type}/{file.filename}"
    documents = driver.documents or {}
    documents[document_type] = doc_url
    driver.documents = documents

    return {"message": "Document uploaded", "document_type": document_type, "url": doc_url}
