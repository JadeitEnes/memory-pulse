# MemoryPulse

**DRAM · NAND · AI Memory — Market Intelligence Platform**

A full-stack market intelligence system that tracks, stores, analyzes, and visualizes semiconductor memory prices — with real-time WebSocket updates, time-series forecasting, anomaly detection, and a full observability stack.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.12, FastAPI (async), SQLAlchemy 2.x, Pydantic v2 |
| **Database** | TimescaleDB (PostgreSQL + hypertable partitioning) |
| **Caching** | Redis dual-instance: broker (noeviction) + cache (allkeys-lru) |
| **Task Queue** | Celery + Redis Broker, Celery Beat scheduler |
| **Scraping** | httpx async, BeautifulSoup, exponential backoff retry |
| **Forecasting** | Prophet (Meta), asyncio.to_thread (CPU-bound isolation) |
| **Auth** | JWT (python-jose HS256), bcrypt (passlib), slowapi rate limiting |
| **Frontend** | React 18, TypeScript, Vite, Recharts, TailwindCSS, WebSocket |
| **Observability** | Prometheus, Grafana, Celery Flower |
| **Infrastructure** | Docker Compose (10 services), GitHub Actions CI |

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
                   React Dashboard
                   └── Recharts + TailwindCSS

Observability:
  Prometheus ──scrapes──► /metrics (prometheus-fastapi-instrumentator)
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
- **Redis cache layer** — Namespaced keys (`mp:prices:*`, `mp:forecast:*`, `mp:anomaly:*`), 7× latency improvement
- **WebSocket live feed** — 5-second broadcast of latest prices to all connected clients
- **Observability** — 5 custom Prometheus metrics, 7-panel Grafana dashboard, Flower worker monitoring

---

## Quick Start

```bash
git clone <repo>
cd memory-pulse
docker compose up --build -d

# Run DB migrations + seed initial data
docker compose exec api alembic upgrade head
docker compose exec api python -m app.infrastructure.seed_db
```

| Service | URL |
|---|---|
| API docs (Swagger) | http://localhost:8000/docs |
| React dashboard | http://localhost:5173 |
| Grafana | http://localhost:3000 (admin / admin) |
| Prometheus | http://localhost:9090 |
| Flower (Celery) | http://localhost:5555 |
| Health check | http://localhost:8000/api/v1/health/ready |

---

## API Authentication

```bash
# Get a token
curl -X POST http://localhost:8000/api/v1/auth/token \
  -d "username=admin&password=changeme"

# Use the token
curl http://localhost:8000/api/v1/prices \
  -H "Authorization: Bearer <token>"
```

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
- [ ] Nginx reverse proxy
- [ ] Integration tests (real DB + Redis)

---

## Copyright

Copyright (c) 2026 **Enes T.** — All Rights Reserved.

This project and its source code are the exclusive intellectual property of Enes T.
Unauthorized use, copying, or distribution is prohibited.
See [LICENSE](./LICENSE) for details.
