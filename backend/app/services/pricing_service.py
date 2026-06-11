"""
Dynamic pricing engine.
Factors: Base Fare + Distance + Weather + Surge + Coupon
"""
import httpx
from datetime import datetime
from haversine import haversine, Unit
from sqlalchemy import select
from typing import Optional, Dict, Any
from app.core.config import settings
from app.models.models import WeatherCondition, OfferType, Offer
import structlog

logger = structlog.get_logger()

WEATHER_MULTIPLIERS = {
    WeatherCondition.NORMAL: 1.0,
    WeatherCondition.LIGHT_RAIN: 1.1,
    WeatherCondition.MODERATE_RAIN: 1.25,
    WeatherCondition.HEAVY_RAIN: 1.5,
}


class PricingService:

    @staticmethod
    async def get_weather_condition(lat: float, lng: float) -> WeatherCondition:
        """Fetch weather from OpenWeatherMap and map to condition."""
        if not settings.OPENWEATHER_API_KEY:
            return WeatherCondition.NORMAL

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{settings.OPENWEATHER_BASE_URL}/weather",
                    params={
                        "lat": lat,
                        "lon": lng,
                        "appid": settings.OPENWEATHER_API_KEY,
                    }
                )
                data = response.json()

            weather_id = data.get("weather", [{}])[0].get("id", 800)
            rain_volume = data.get("rain", {}).get("1h", 0)

            if weather_id < 300:  # Thunderstorm
                return WeatherCondition.HEAVY_RAIN
            elif weather_id < 500:  # Drizzle
                return WeatherCondition.LIGHT_RAIN
            elif 500 <= weather_id < 600:  # Rain
                if rain_volume > 10:
                    return WeatherCondition.HEAVY_RAIN
                elif rain_volume > 2.5:
                    return WeatherCondition.MODERATE_RAIN
                else:
                    return WeatherCondition.LIGHT_RAIN
            else:
                return WeatherCondition.NORMAL

        except Exception as e:
            logger.warning("Weather API failed, using NORMAL", error=str(e))
            return WeatherCondition.NORMAL

    @staticmethod
    def calculate_distance(
        pickup_lat: float, pickup_lng: float,
        dropoff_lat: float, dropoff_lng: float
    ) -> float:
        """Calculate distance in km using Haversine formula."""
        return haversine(
            (pickup_lat, pickup_lng),
            (dropoff_lat, dropoff_lng),
            unit=Unit.KILOMETERS
        )

    @staticmethod
    def apply_surge(distance_km: float, active_deliveries: int) -> float:
        """Simple surge pricing based on active demand."""
        if active_deliveries > 50:
            return 2.0
        elif active_deliveries > 30:
            return 1.5
        elif active_deliveries > 10:
            return 1.2
        return 1.0

    @staticmethod
    def apply_offer_discount(subtotal: float, offer) -> float:
        """Calculate discount for an offer."""
        if not offer:
            return 0.0

        if offer.offer_type == OfferType.FREE_DELIVERY:
            return subtotal

        if offer.offer_type == OfferType.FLAT:
            discount = min(offer.discount_value, subtotal)
        elif offer.offer_type == OfferType.PERCENTAGE:
            discount = subtotal * (offer.discount_value / 100)
        else:
            discount = 0.0

        if offer.min_order_value and subtotal < offer.min_order_value:
            return 0.0

        if offer.max_discount:
            discount = min(discount, offer.max_discount)

        return discount

    @classmethod
    async def calculate_fare(
        cls,
        pickup_lat: float,
        pickup_lng: float,
        dropoff_lat: float,
        dropoff_lng: float,
        offer=None,
        active_deliveries: int = 0,
    ) -> Dict[str, Any]:
        """Full pricing calculation pipeline."""

        # Distance
        distance_km = cls.calculate_distance(pickup_lat, pickup_lng, dropoff_lat, dropoff_lng)
        distance_km = round(distance_km, 2)

        # Weather
        weather_condition = await cls.get_weather_condition(pickup_lat, pickup_lng)
        weather_multiplier = WEATHER_MULTIPLIERS[weather_condition]

        # Surge
        surge_multiplier = cls.apply_surge(distance_km, active_deliveries)

        # Base calculation
        base_fare = settings.BASE_FARE + (distance_km * settings.PRICE_PER_KM)
        subtotal = base_fare * weather_multiplier * surge_multiplier

        # Discount
        discount_amount = cls.apply_offer_discount(subtotal, offer)
        total_fare = max(0, subtotal - discount_amount)
        total_fare = round(total_fare, 2)

        return {
            "distance_km": distance_km,
            "base_fare": round(base_fare, 2),
            "weather_condition": weather_condition,
            "weather_multiplier": weather_multiplier,
            "surge_multiplier": surge_multiplier,
            "subtotal": round(subtotal, 2),
            "discount_amount": round(discount_amount, 2),
            "total_fare": total_fare,
        }

    @classmethod
    async def estimate_fare(
        cls,
        pickup_lat: float,
        pickup_lng: float,
        dropoff_lat: float,
        dropoff_lng: float,
        coupon_code: Optional[str] = None,
        db=None,
    ) -> Dict[str, Any]:
        """Fare estimate for display to client before booking."""
        offer = None
        if coupon_code and db is not None:
            offer_result = await db.execute(
                select(Offer).where(
                    Offer.code == coupon_code.upper(),
                    Offer.is_active == True,
                    Offer.valid_from <= datetime.utcnow(),
                    Offer.valid_until >= datetime.utcnow(),
                )
            )
            offer = offer_result.scalar_one_or_none()

        return await cls.calculate_fare(
            pickup_lat, pickup_lng, dropoff_lat, dropoff_lng, offer=offer
        )
