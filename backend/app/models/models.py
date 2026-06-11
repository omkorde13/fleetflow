from sqlalchemy import (
    Column, String, Boolean, Float, Integer, Text, ForeignKey,
    DateTime, Enum as SAEnum, JSON, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base
from datetime import datetime
import uuid
import enum


# ──────────────────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    CLIENT = "CLIENT"
    DRIVER = "DRIVER"
    ADMIN = "ADMIN"


class DriverStatus(str, enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    BUSY = "BUSY"
    ON_DELIVERY = "ON_DELIVERY"


class DeliveryStatus(str, enum.Enum):
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class OfferType(str, enum.Enum):
    PERCENTAGE = "PERCENTAGE"
    FLAT = "FLAT"
    FREE_DELIVERY = "FREE_DELIVERY"


class WeatherCondition(str, enum.Enum):
    NORMAL = "NORMAL"
    LIGHT_RAIN = "LIGHT_RAIN"
    MODERATE_RAIN = "MODERATE_RAIN"
    HEAVY_RAIN = "HEAVY_RAIN"


class NotificationChannel(str, enum.Enum):
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"
    REAL_TIME = "REAL_TIME"


# ──────────────────────────────────────────────────────────
# Mixins
# ──────────────────────────────────────────────────────────

class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class UUIDMixin:
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)


# ──────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────

class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), unique=True, nullable=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=True)
    role = Column(SAEnum(UserRole), default=UserRole.CLIENT, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    google_id = Column(String(255), nullable=True, unique=True)
    avatar_url = Column(Text, nullable=True)
    login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    driver_profile = relationship("Driver", back_populates="user", uselist=False)
    deliveries = relationship("Delivery", back_populates="client", foreign_keys="Delivery.client_id")
    payments = relationship("Payment", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")


class Driver(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "drivers"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    license_number = Column(String(100), nullable=False, unique=True)
    vehicle_type = Column(String(100), nullable=False)
    vehicle_number = Column(String(50), nullable=False, unique=True)
    vehicle_model = Column(String(100), nullable=True)
    status = Column(SAEnum(DriverStatus), default=DriverStatus.OFFLINE, nullable=False)
    is_verified = Column(Boolean, default=False)
    is_suspended = Column(Boolean, default=False)
    documents = Column(JSON, default={})
    rating = Column(Float, default=5.0)
    total_deliveries = Column(Integer, default=0)
    current_lat = Column(Float, nullable=True)
    current_lng = Column(Float, nullable=True)
    last_location_update = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="driver_profile")
    deliveries = relationship("Delivery", back_populates="driver", foreign_keys="Delivery.driver_id")
    locations = relationship("Location", back_populates="driver")
    ratings = relationship("DriverRating", back_populates="driver")

    __table_args__ = (
        Index("ix_driver_status", "status"),
        Index("ix_driver_location", "current_lat", "current_lng"),
    )

    @property
    def full_name(self):
        return self.user.full_name if self.user else None

    @property
    def phone(self):
        return self.user.phone if self.user else None


class Delivery(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "deliveries"

    client_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    driver_id = Column(UUID(as_uuid=True), ForeignKey("drivers.id"), nullable=True)
    status = Column(SAEnum(DeliveryStatus), default=DeliveryStatus.PENDING, nullable=False)

    # Pickup
    pickup_address = Column(Text, nullable=False)
    pickup_lat = Column(Float, nullable=False)
    pickup_lng = Column(Float, nullable=False)
    pickup_contact_name = Column(String(255), nullable=True)
    pickup_contact_phone = Column(String(20), nullable=True)

    # Dropoff
    dropoff_address = Column(Text, nullable=False)
    dropoff_lat = Column(Float, nullable=False)
    dropoff_lng = Column(Float, nullable=False)
    dropoff_contact_name = Column(String(255), nullable=True)
    dropoff_contact_phone = Column(String(20), nullable=True)

    # Parcel info
    parcel_description = Column(Text, nullable=True)
    parcel_weight = Column(Float, nullable=True)

    # Pricing
    distance_km = Column(Float, nullable=True)
    base_fare = Column(Float, nullable=True)
    weather_multiplier = Column(Float, default=1.0)
    surge_multiplier = Column(Float, default=1.0)
    discount_amount = Column(Float, default=0.0)
    total_fare = Column(Float, nullable=True)
    weather_condition = Column(SAEnum(WeatherCondition), default=WeatherCondition.NORMAL)

    # Coupon
    coupon_code = Column(String(50), nullable=True)
    offer_id = Column(UUID(as_uuid=True), ForeignKey("offers.id"), nullable=True)

    # Timestamps
    assigned_at = Column(DateTime, nullable=True)
    picked_up_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)

    # Notes
    special_instructions = Column(Text, nullable=True)

    # OTP verification
    pickup_otp = Column(String(4), nullable=True)
    delivery_otp = Column(String(4), nullable=True)

    # Relationships
    client = relationship("User", back_populates="deliveries", foreign_keys=[client_id])
    driver = relationship("Driver", back_populates="deliveries", foreign_keys=[driver_id])
    payment = relationship("Payment", back_populates="delivery", uselist=False)
    offer = relationship("Offer", back_populates="deliveries")
    rating = relationship("DriverRating", back_populates="delivery", uselist=False)

    __table_args__ = (
        Index("ix_delivery_status", "status"),
        Index("ix_delivery_client", "client_id"),
        Index("ix_delivery_driver", "driver_id"),
    )


class Location(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "locations"

    driver_id = Column(UUID(as_uuid=True), ForeignKey("drivers.id"), nullable=False)
    delivery_id = Column(UUID(as_uuid=True), ForeignKey("deliveries.id"), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    speed = Column(Float, nullable=True)
    heading = Column(Float, nullable=True)
    accuracy = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    driver = relationship("Driver", back_populates="locations")

    __table_args__ = (
        Index("ix_location_driver_time", "driver_id", "timestamp"),
    )


class Payment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "payments"

    delivery_id = Column(UUID(as_uuid=True), ForeignKey("deliveries.id"), nullable=False, unique=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR")
    status = Column(SAEnum(PaymentStatus), default=PaymentStatus.PENDING)
    razorpay_order_id = Column(String(255), nullable=True)
    razorpay_payment_id = Column(String(255), nullable=True)
    razorpay_signature = Column(String(512), nullable=True)
    payment_method = Column(String(50), nullable=True)
    refund_id = Column(String(255), nullable=True)
    refunded_at = Column(DateTime, nullable=True)
    invoice_url = Column(String(512), nullable=True)
    extra_data = Column(JSON, default={})

    # Relationships
    delivery = relationship("Delivery", back_populates="payment")
    user = relationship("User", back_populates="payments")

    __table_args__ = (
        Index("ix_payment_status", "status"),
        Index("ix_payment_user", "user_id"),
    )


class Offer(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "offers"

    code = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    offer_type = Column(SAEnum(OfferType), nullable=False)
    discount_value = Column(Float, nullable=False)
    min_order_value = Column(Float, default=0.0)
    max_discount = Column(Float, nullable=True)
    usage_limit = Column(Integer, nullable=True)
    used_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    valid_from = Column(DateTime, nullable=False)
    valid_until = Column(DateTime, nullable=False)

    # Relationships
    usages = relationship("OfferUsage", back_populates="offer")
    deliveries = relationship("Delivery", back_populates="offer")


class OfferUsage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "offer_usage"

    offer_id = Column(UUID(as_uuid=True), ForeignKey("offers.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    delivery_id = Column(UUID(as_uuid=True), ForeignKey("deliveries.id"), nullable=True)
    discount_applied = Column(Float, nullable=False)

    # Relationships
    offer = relationship("Offer", back_populates="usages")

    __table_args__ = (
        Index("ix_offer_usage_user", "user_id", "offer_id"),
    )


class Notification(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "notifications"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    channel = Column(SAEnum(NotificationChannel), default=NotificationChannel.IN_APP)
    is_read = Column(Boolean, default=False)
    event_type = Column(String(100), nullable=True)
    reference_id = Column(UUID(as_uuid=True), nullable=True)
    extra_data = Column(JSON, default={})

    # Relationships
    user = relationship("User", back_populates="notifications")

    __table_args__ = (
        Index("ix_notification_user_read", "user_id", "is_read"),
    )


class AuditLog(Base, UUIDMixin):
    __tablename__ = "audit_logs"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String(255), nullable=False)
    entity_type = Column(String(100), nullable=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    details = Column(JSON, default={})
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_user_time", "user_id", "timestamp"),
        Index("ix_audit_action", "action"),
    )


class DriverRating(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "driver_ratings"

    driver_id = Column(UUID(as_uuid=True), ForeignKey("drivers.id"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    delivery_id = Column(UUID(as_uuid=True), ForeignKey("deliveries.id"), nullable=False, unique=True)
    rating = Column(Float, nullable=False)
    comment = Column(Text, nullable=True)

    # Relationships
    driver = relationship("Driver", back_populates="ratings")
    delivery = relationship("Delivery", back_populates="rating")

    __table_args__ = (
        Index("ix_rating_driver", "driver_id"),
    )


class RefreshToken(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "refresh_tokens"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token = Column(Text, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")
