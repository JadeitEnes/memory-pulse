# MemoryPulse

**DRAM · NAND · AI Memory — Market Intelligence Platform**

A full-stack market intelligence system that tracks, stores, analyzes, and visualizes semiconductor memory prices — with real-time WebSocket updates, time-series forecasting, anomaly detection, and a full observability stack.

![CI](https://github.com/enest/memory-pulse/actions/workflows/ci.yml/badge.svg)

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.11, FastAPI (async), SQLAlchemy 2.x, Pydantic v2 |
| **Database** | TimescaleDB (PostgreSQL + hypertable partitioning) |
| **Caching** | Redis dual-instance: broker (noeviction) + cache (allkeys-lru) |
| **Task Queue** | Celery + Redis Broker, Celery Beat scheduler |
| **Scraping** | httpx async + brotli, BeautifulSoup, exponential backoff retry |
| **Forecasting** | Prophet (Meta), asyncio.to_thread (CPU-bound isolation) |
| **Auth** | JWT (python-jose HS256), bcrypt, slowapi rate limiting |
| **Frontend** | React 18, TypeScript, Vite, Recharts, TailwindCSS, WebSocket |
| **Observability** | Prometheus (custom ASGI middleware), Grafana, Celery Flower |
| **Infrastructure** | Docker Compose (11 services), Nginx reverse proxy, GitHub Actions CI |

---

## Architecture

```
Newegg HTTP Scraper ─┐
                     ├──► Celery Worker ──── Redis Broker (noeviction)
Simulated Collector ─┘         │
                               │ bulk insert
                         TimescaleDB (hypertable, 7-day chunks)
                               │
                         FastAPI (async) ──── Redis Cache (allkeys-lru)
                         │         │
                    REST/JSON   WebSocket (5s live feed)
                               │
                         Nginx (port 80)
                               │
                        React Dashboard
                        └── Recharts + TailwindCSS

Observability:
  Prometheus ──scrapes──► /metrics (custom prometheus-client middleware)
  Grafana ──reads──► Prometheus  (auto-provisioned dashboard)
  Flower ──watches──► Celery Workers
```

---

## Features

- **Real price collection** — Newegg scraper (DDR5, DDR4, NVMe) with graceful fallback to simulated data when blocked
- **Time-series forecasting** — Prophet model, 30/60/90-day horizon, 80% confidence interval, cached 1 hour
- **Anomaly detection** — Z-score (σ=1.5/2.0/3.0 thresholds) + composite risk score (anomaly 40% + volatility 35% + trend 25%)
- **JWT authentication** — Bearer token login, bcrypt password hashing, protected write endpoints
- **Rate limiting** — 60 req/min global, 10 req/min on `/auth/token` (brute-force protection)
- **Redis cache layer** — Namespaced keys (`mp:prices:*`, `mp:forecast:*`, `mp:anomaly:*`), TTL-based invalidation
- **WebSocket live feed** — 5-second broadcast of latest prices to all connected clients
- **Nginx reverse proxy** — Single entry point on port 80, security headers, WebSocket upgrade support
- **Observability** — 5 custom Prometheus metrics, 7-panel Grafana dashboard, Flower worker monitoring
- **CI/CD** — GitHub Actions runs integration tests against full Docker stack on every push

---

## Quick Start

```bash
git clone <repo>
cd memory-pulse
cp .env.example .env   # edit values before running
docker compose up --build -d

# Run DB migrations + seed initial data
docker compose exec api alembic upgrade head
docker compose exec api python -m app.infrastructure.seed_db
```

| Service | URL |
|---|---|
| **React dashboard** | http://localhost (port 80 via nginx) |
| **API docs (Swagger)** | http://localhost/docs |
| **Health check** | http://localhost/api/v1/health |
| **Readiness check** | http://localhost/api/v1/health/ready |
| Grafana | http://localhost:3000 (admin / admin) |
| Prometheus | http://localhost:9090 |
| Flower (Celery) | http://localhost:5555 |

---

## API Authentication

```bash
# Get a token
curl -X POST http://localhost/api/v1/auth/token \
  -d "username=admin&password=changeme"

# Use the token
curl http://localhost/api/v1/prices \
  -H "Authorization: Bearer <token>"
```

---

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Generate a strong secret key
python -c "import secrets; print(secrets.token_hex(32))"
```

Key variables:

| Variable | Description |
|---|---|
| `SECRET_KEY` | JWT signing key — **must be changed in production** |
| `API_PASSWORD` | Admin password for `/auth/token` |
| `POSTGRES_PASSWORD` | Database password |
| `ENVIRONMENT` | `development` / `staging` / `production` |

---

## Roadmap

- [x] FastAPI async backend with Repository pattern and DI
- [x] TimescaleDB hypertable with composite primary key
- [x] Celery distributed task queue with exponential backoff retry
- [x] Redis dual-instance cache layer (broker vs cache separation)
- [x] HTTP scraper — Newegg (httpx + BeautifulSoup, median price, per-GB normalization)
- [x] Prophet time-series forecasting with 80% confidence bands
- [x] Z-score anomaly detection + composite risk scoring
- [x] JWT authentication + bcrypt + slowapi rate limiting
- [x] React dashboard — live WebSocket, forecast chart, risk cards
- [x] Prometheus metrics + Grafana dashboard + Celery Flower
- [x] Nginx reverse proxy with security headers
- [x] Integration tests 30/30 (real DB + Redis)
- [x] GitHub Actions CI pipeline

---

## Copyright

Copyright (c) 2026 **Enes T.** — All Rights Reserved.

This project and its source code are the exclusive intellectual property of Enes T.
Unauthorized use, copying, or distribution is prohibited.
See [LICENSE](./LICENSE) for details.
