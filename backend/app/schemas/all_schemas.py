# Re-export all schemas from the main schemas module
from app.schemas import (
    RegisterRequest, LoginRequest, TokenResponse, RefreshTokenRequest,
    ForgotPasswordRequest, ResetPasswordRequest, UserResponse, UpdateUserRequest,
    CreateDriverProfileRequest, DriverResponse,
    CreateDeliveryRequest, DeliveryResponse, DeliveryListResponse,
    AssignDriverRequest, UpdateDeliveryStatusRequest, CancelDeliveryRequest,
    FareEstimateRequest, FareEstimateResponse,
    CreateOrderRequest, CreateOrderResponse, VerifyPaymentRequest, PaymentResponse, PaymentListResponse,
    CreateOfferRequest, OfferResponse, NotificationResponse
)

# Auth-specific
class auth:
    RegisterRequest = RegisterRequest
    LoginRequest = LoginRequest
    TokenResponse = TokenResponse
    RefreshTokenRequest = RefreshTokenRequest
    ForgotPasswordRequest = ForgotPasswordRequest
    ResetPasswordRequest = ResetPasswordRequest

class delivery:
    CreateDeliveryRequest = CreateDeliveryRequest
    DeliveryResponse = DeliveryResponse
    DeliveryListResponse = DeliveryListResponse
    AssignDriverRequest = AssignDriverRequest
    UpdateDeliveryStatusRequest = UpdateDeliveryStatusRequest
    CancelDeliveryRequest = CancelDeliveryRequest

class payment:
    CreateOrderRequest = CreateOrderRequest
    CreateOrderResponse = CreateOrderResponse
    VerifyPaymentRequest = VerifyPaymentRequest
    PaymentResponse = PaymentResponse
    PaymentListResponse = PaymentListResponse

# Missing schemas added in continuation
from app.schemas import UserUpdate, PricingEstimateRequest, PricingEstimateResponse
