# MemoryPulse

**DRAM · NAND · AI Memory — Market Intelligence Platform**

A full-stack market intelligence system that tracks, stores, and visualizes semiconductor memory prices — including DRAM, DDR5, HBM3, LPDDR5, and NAND — with real-time WebSocket updates and a React dashboard.

---

## Tech Stack

**Backend** — Python 3.11, FastAPI (async), SQLAlchemy 2.x, Pydantic v2, Alembic

**Database** — TimescaleDB (PostgreSQL extension for time-series), hypertable partitioning

**Caching** — Redis dual-instance: broker (Celery, noeviction) + cache (API, allkeys-lru)

**Background Jobs** — Celery + Redis, scheduled price collection every 6 hours

**Frontend** — React 18, Vite, TypeScript, Recharts, TailwindCSS, WebSocket

**Infrastructure** — Docker Compose (7 services), GitHub Actions CI

---

## Architecture

```
Simulated / HTTP Collectors
           │
    Celery Beat Scheduler (every 6h)
           │
    Celery Worker  ──── Redis Broker
           │
    FastAPI (async)  ── Redis Cache (7x latency improvement)
           │
    TimescaleDB (hypertable, chunk_interval: 7 days)
           │
    React Dashboard  ── WebSocket (live feed, 5s interval)
```

---

## Quick Start

```bash
git clone <repo>
cd memory-pulse

docker compose up --build -d
docker compose exec api alembic upgrade head
docker compose exec api python -m app.infrastructure.seed_db
```

API docs: http://localhost:8000/docs  
Dashboard: http://localhost:5173  
Health: http://localhost:8000/api/v1/health/ready

---

## Roadmap

- [x] FastAPI async backend with Repository pattern and DI
- [x] TimescaleDB hypertable with composite primary key
- [x] Celery distributed task queue with retry
- [x] Redis dual-instance cache layer
- [x] React dashboard with Recharts and WebSocket live feed
- [ ] HTTP scraper (httpx async) with real DRAM/NAND sources
- [ ] Price forecasting with Prophet / XGBoost
- [ ] Anomaly detection and risk scoring
- [ ] JWT authentication and rate limiting
- [ ] Prometheus metrics and Nginx reverse proxy

---

## Copyright

Copyright (c) 2026 **Enes T.** — All Rights Reserved.

This project and its source code are the exclusive intellectual property of Enes T.
Unauthorized use, copying, or distribution is prohibited.
See [LICENSE](./LICENSE) for details.
