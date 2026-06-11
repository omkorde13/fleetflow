from uuid import UUID
from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional, List
from datetime import datetime

from app.models.models import UserRole, DeliveryStatus, PaymentStatus, OfferType, WeatherCondition

# ──────────────────────────────────────────────────────────
# Auth Schemas
# ──────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    password: str
    role: Optional[UserRole] = UserRole.CLIENT

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    role: UserRole


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


# ──────────────────────────────────────────────────────────
# User Schemas
# ──────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    phone: Optional[str]
    role: UserRole
    is_active: bool
    is_verified: bool
    avatar_url: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None


# ──────────────────────────────────────────────────────────
# Driver Schemas
# ──────────────────────────────────────────────────────────

class CreateDriverProfileRequest(BaseModel):
    license_number: str
    vehicle_type: str
    vehicle_number: str
    vehicle_model: Optional[str] = None


class DriverResponse(BaseModel):
    id: UUID
    user_id: UUID
    license_number: str
    vehicle_type: str
    vehicle_number: str
    vehicle_model: Optional[str]
    status: str
    is_verified: bool
    rating: float
    total_deliveries: int
    current_lat: Optional[float]
    current_lng: Optional[float]
    created_at: datetime

    model_config = {"from_attributes": True}


class DriverInfo(BaseModel):
    id: UUID
    full_name: Optional[str]
    phone: Optional[str]
    vehicle_type: str
    vehicle_number: str
    vehicle_model: Optional[str]
    rating: float

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────────────
# Delivery Schemas
# ──────────────────────────────────────────────────────────

class CreateDeliveryRequest(BaseModel):
    pickup_address: str
    pickup_lat: float
    pickup_lng: float
    pickup_contact_name: Optional[str] = None
    pickup_contact_phone: Optional[str] = None
    dropoff_address: str
    dropoff_lat: float
    dropoff_lng: float
    dropoff_contact_name: Optional[str] = None
    dropoff_contact_phone: Optional[str] = None
    parcel_description: Optional[str] = None
    parcel_weight: Optional[float] = None
    special_instructions: Optional[str] = None
    coupon_code: Optional[str] = None


class PaymentResponse(BaseModel):
    id: UUID
    delivery_id: UUID
    amount: float
    currency: str
    status: PaymentStatus
    razorpay_order_id: Optional[str]
    razorpay_payment_id: Optional[str]
    payment_method: Optional[str]
    invoice_url: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class DriverRatingResponse(BaseModel):
    rating: float
    comment: Optional[str] = None

    model_config = {"from_attributes": True}


class DeliveryResponse(BaseModel):
    id: UUID
    client_id: UUID
    driver_id: Optional[UUID]
    status: DeliveryStatus
    pickup_address: str
    pickup_lat: float
    pickup_lng: float
    dropoff_address: str
    dropoff_lat: float
    dropoff_lng: float
    parcel_description: Optional[str]
    distance_km: Optional[float]
    base_fare: Optional[float]
    weather_multiplier: float
    surge_multiplier: float
    discount_amount: float
    total_fare: Optional[float]
    weather_condition: WeatherCondition
    coupon_code: Optional[str]
    assigned_at: Optional[datetime]
    picked_up_at: Optional[datetime]
    delivered_at: Optional[datetime]
    created_at: datetime
    payment: Optional[PaymentResponse] = None
    driver: Optional[DriverInfo] = None
    rating: Optional[DriverRatingResponse] = None
    pickup_otp: Optional[str] = None
    delivery_otp: Optional[str] = None

    model_config = {"from_attributes": True}


class DeliveryListResponse(BaseModel):
    deliveries: List[DeliveryResponse]
    total: int
    page: int
    page_size: int


class AssignDriverRequest(BaseModel):
    driver_id: UUID


class UpdateDeliveryStatusRequest(BaseModel):
    status: DeliveryStatus
    note: Optional[str] = None


class CancelDeliveryRequest(BaseModel):
    reason: str


class RateDeliveryRequest(BaseModel):
    rating: float
    comment: Optional[str] = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v):
        if not (1 <= v <= 5):
            raise ValueError("Rating must be between 1 and 5")
        return v


class ConfirmPickupRequest(BaseModel):
    otp: str


class CompleteDeliveryRequest(BaseModel):
    otp: str


class FareEstimateRequest(BaseModel):
    pickup_lat: float
    pickup_lng: float
    dropoff_lat: float
    dropoff_lng: float
    coupon_code: Optional[str] = None


class FareEstimateResponse(BaseModel):
    distance_km: float
    base_fare: float
    weather_condition: str
    weather_multiplier: float
    surge_multiplier: float
    subtotal: float
    discount_amount: float
    total_fare: float


# ──────────────────────────────────────────────────────────
# Payment Schemas
# ──────────────────────────────────────────────────────────

class CreateOrderRequest(BaseModel):
    delivery_id: UUID


class CreateOrderResponse(BaseModel):
    razorpay_order_id: str
    amount: int  # paise
    currency: str
    key: str
    delivery_id: UUID


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    payment_method: Optional[str] = None


class PaymentListResponse(BaseModel):
    payments: List[PaymentResponse]


# ──────────────────────────────────────────────────────────
# Offer Schemas
# ──────────────────────────────────────────────────────────

class CreateOfferRequest(BaseModel):
    code: str
    title: str
    description: Optional[str] = None
    offer_type: OfferType
    discount_value: float
    min_order_value: float = 0.0
    max_discount: Optional[float] = None
    usage_limit: Optional[int] = None
    valid_from: datetime
    valid_until: datetime


class OfferResponse(BaseModel):
    id: UUID
    code: str
    title: str
    description: Optional[str]
    offer_type: OfferType
    discount_value: float
    min_order_value: float
    max_discount: Optional[float]
    usage_limit: Optional[int]
    used_count: int
    is_active: bool
    valid_from: datetime
    valid_until: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────────────
# Notification Schemas
# ──────────────────────────────────────────────────────────

class NotificationResponse(BaseModel):
    id: UUID
    title: str
    message: str
    is_read: bool
    event_type: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────────────
# User Update Schema
# ──────────────────────────────────────────────────────────

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None


# ──────────────────────────────────────────────────────────
# Pricing Estimate Schemas
# ──────────────────────────────────────────────────────────

class PricingEstimateRequest(BaseModel):
    pickup_lat: float
    pickup_lng: float
    dropoff_lat: float
    dropoff_lng: float
    coupon_code: Optional[str] = None


class PricingEstimateResponse(BaseModel):
    base_fare: float
    distance_km: float
    distance_fare: float
    weather_condition: str
    weather_multiplier: float
    surge_multiplier: float
    subtotal: float
    discount: float = 0.0
    total_fare: float
    currency: str = "INR"
