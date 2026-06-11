# 🚚 FleetFlow — Smart Logistics & Delivery Platform

Enterprise-grade, real-time delivery management platform built with FastAPI, React, WebSockets, Redis Pub/Sub, and Docker.

---

## ✨ Features

| Feature | Details |
|---|---|
| **Real-time GPS tracking** | WebSocket + Redis Pub/Sub fan-out; live Leaflet map for clients |
| **OTP pickup & delivery verification** | Auto-generated 4-digit codes; client shares with driver to confirm pickup and final delivery |
| **Driver ratings** | Clients rate drivers (1-5★ + comment) after delivery; driver's average rating updates live |
| **Cash on Delivery** | Pay-on-delivery option with driver-side cash confirmation |
| **Dynamic pricing** | Distance × weather × surge multipliers via OpenWeatherMap |
| **Razorpay payments** | Checkout, HMAC signature verification, webhook handler, refunds |
| **Google OAuth** | Social login with role-aware redirect |
| **Role-based access** | CLIENT / DRIVER / ADMIN with separate dashboards and route guards |
| **Celery jobs** | Notifications, invoice generation, daily reports, token cleanup |
| **Admin fleet monitor** | Live map of all active drivers via WebSocket |
| **Coupon system** | Percentage, flat, free-delivery offers with usage limits |
| **Alembic migrations** | Async SQLAlchemy with auto-migration on startup |
| **Docker Compose** | One-command spin-up for the full stack |

---

## 🏗️ Architecture

```
nginx (80)
├── /api/*        → backend:8000  (FastAPI)
├── /ws/*         → backend:8000  (WebSocket)
└── /*            → frontend:5173 (Vite + React)

backend
├── FastAPI app (uvicorn, async)
├── PostgreSQL (asyncpg + SQLAlchemy)
├── Redis (cache + Pub/Sub + rate limiting)
└── Celery worker + Celery Beat (scheduled tasks)
```

---

## 🚀 Quick Start

### Prerequisites
- Docker ≥ 24
- Docker Compose v2

### 1. Clone and configure environment

```bash
git clone <repo-url>
cd fleetflow
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Required — get from https://console.razorpay.com
RAZORPAY_KEY_ID=rzp_test_xxx
RAZORPAY_KEY_SECRET=your_secret

# Required — https://console.cloud.google.com (OAuth)
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_google_secret

# Required — https://openweathermap.org/api
OPENWEATHER_API_KEY=your_key

# Required — SMTP (e.g. Gmail app password)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your_app_password
FROM_EMAIL=you@gmail.com

# Change in production!
SECRET_KEY=change-me-to-a-long-random-string-in-production
```

### 2. Start everything

```bash
docker compose up --build
```

This will:
1. Start PostgreSQL and Redis
2. Run Alembic migrations automatically
3. Launch the FastAPI backend (port 8000)
4. Launch the Vite dev frontend (port 5173)
5. Start Celery worker + Celery Beat
6. Start Nginx reverse proxy (port **80**)

### 3. Open the app

→ **http://localhost**

---

## 🔑 Default Admin Setup

No default admin is seeded. To create the first admin:

```bash
# Connect to the backend container
docker compose exec backend bash

# Open a Python shell
python -c "
import asyncio
from app.db.session import AsyncSessionLocal
from app.models.models import User, UserRole
from app.core.security import get_password_hash

async def create_admin():
    async with AsyncSessionLocal() as db:
        admin = User(
            email='admin@fleetflow.com',
            full_name='Admin',
            hashed_password=get_password_hash('Admin@1234'),
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,
        )
        db.add(admin)
        await db.commit()
        print('Admin created: admin@fleetflow.com / Admin@1234')

asyncio.run(create_admin())
"
```

---

## 📡 API Reference

Base URL: `http://localhost/api/v1`

### Auth
| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Register (CLIENT or DRIVER role) |
| POST | `/auth/login` | Email + password login |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/logout` | Revoke refresh token |
| GET | `/auth/google/login` | Initiate Google OAuth |
| POST | `/auth/forgot-password` | Send reset email |
| POST | `/auth/reset-password` | Reset with token |

### Deliveries
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/deliveries` | CLIENT | Create delivery order |
| GET | `/deliveries` | All | List (filtered by role) |
| GET | `/deliveries/{id}` | All | Get detail |
| POST | `/deliveries/{id}/cancel` | CLIENT | Cancel |
| POST | `/deliveries/{id}/accept` | DRIVER | Accept pending delivery |
| POST | `/deliveries/{id}/pickup` | DRIVER | Mark picked up (requires pickup OTP from client) |
| POST | `/deliveries/{id}/complete` | DRIVER | Mark delivered (requires delivery OTP from client) |
| POST | `/deliveries/{id}/rate` | CLIENT | Rate driver (1-5★ + optional comment) after delivery |
| POST | `/deliveries/{id}/assign` | ADMIN | Force-assign driver |

### Pricing
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/users/pricing/estimate` | Any | Fare estimate (no booking) |

### Payments
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/payments/orders` | CLIENT | Create Razorpay order |
| POST | `/payments/cod` | CLIENT | Pay with cash on delivery |
| POST | `/payments/{id}/confirm-cash` | DRIVER | Confirm cash received from client |
| GET | `/payments/by-delivery/{delivery_id}` | All | Get payment for a delivery |
| POST | `/payments/verify` | CLIENT | Verify payment signature |
| GET | `/payments/history` | CLIENT | Payment history |
| POST | `/payments/webhook` | — | Razorpay webhook |
| POST | `/payments/{id}/refund` | ADMIN | Issue refund |

### WebSockets
| Endpoint | Role | Description |
|---|---|---|
| `ws://host/ws/driver/{driver_id}` | DRIVER | Stream GPS location |
| `ws://host/ws/track/{delivery_id}` | CLIENT | Receive live driver location |
| `ws://host/ws/fleet` | ADMIN | All active driver locations |
| `ws://host/ws/notifications/{user_id}` | Any | Real-time notifications |

---

## 🗂️ Project Structure

```
fleetflow/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   # Route handlers (auth, deliveries, payments…)
│   │   ├── core/               # Config, security, Redis helpers
│   │   ├── db/                 # SQLAlchemy session
│   │   ├── models/             # ORM models + Enums
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── services/           # PricingService, NotificationService
│   │   ├── utils/              # Geospatial helpers (haversine, bounding box)
│   │   ├── websockets/         # ConnectionManager, WebSocket routes
│   │   ├── workers/            # Celery app + tasks
│   │   └── main.py             # FastAPI app entry point
│   ├── alembic/                # DB migrations
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/         # Shared UI (map, delivery, payment, common)
│       ├── context/            # Zustand auth store
│       ├── hooks/              # useWebSocket, useDeliveryTracking…
│       ├── pages/              # auth/ client/ driver/ admin/
│       └── services/           # Axios API client
├── nginx/nginx.conf
├── scripts/init.sql
└── docker-compose.yml
```

---

## 🧪 Development

### Backend only (without Docker)

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

### Frontend only

```bash
cd frontend
npm install
npm run dev   # Vite dev server at http://localhost:5173
```

Vite proxies `/api` and `/ws` to `localhost:8000` automatically.

### Run Celery worker

```bash
cd backend
celery -A app.workers.celery_app worker --loglevel=info
celery -A app.workers.celery_app beat --loglevel=info
```

---

## 🔒 Security Notes

- JWT access tokens expire in 15 minutes; refresh tokens in 7 days
- Account locks after 5 failed login attempts (30-minute lockout)
- Razorpay webhook uses HMAC-SHA256 signature verification
- Refresh tokens are rotated on every use (old token revoked)
- API rate limiting via `slowapi`: 60 req/min general, 10 req/min on auth routes
- All passwords hashed with bcrypt (cost factor 12)

---

## 📦 Production Checklist

- [ ] Set a strong `SECRET_KEY` (≥32 random chars)
- [ ] Set real Razorpay live keys
- [ ] Configure a real SMTP provider (SendGrid, SES, etc.)
- [ ] Set `ALLOWED_ORIGINS` to your actual domain
- [ ] Switch Nginx to HTTPS with Let's Encrypt
- [ ] Set `NODE_ENV=production` and build frontend: `npm run build`
- [ ] Replace Vite dev server with a static file server or CDN
- [ ] Enable PostgreSQL connection pooling (PgBouncer)
- [ ] Set up monitoring (Sentry, Prometheus)

---

## 📄 License

MIT © FleetFlow
