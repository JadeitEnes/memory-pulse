Memory Pulse
Memory Market Intelligence Platform

A backend platform designed to collect, store, and analyze memory semiconductor market data including DRAM, DDR4, DDR5, HBM, and NAND prices.

Memory Pulse simulates a real-world market intelligence system by combining time-series databases, background job processing, containerized infrastructure, and automated quality pipelines.

Why Memory Pulse?

The semiconductor market is heavily influenced by:

AI accelerator demand
Supply and demand fluctuations
Seasonal trends
Manufacturing cycles

Memory Pulse aims to transform raw memory pricing data into historical datasets and meaningful market insights.

Tech Stack
Backend
Python 3.11
FastAPI
SQLAlchemy Async
Pydantic
Database
PostgreSQL
TimescaleDB
Alembic
Background Processing
Celery
Redis
Infrastructure
Docker & Docker Compose
GitHub Actions CI
Testing & Code Quality
Pytest
Black
Isort
Flake8
MyPy
Architecture
Data Collectors
       |
       ▼
Celery Background Tasks
       |
       ▼
Redis Message Broker
       |
       ▼
FastAPI Application
       |
       ▼
PostgreSQL + TimescaleDB
       |
       ▼
Market Analytics

Quick Start
docker compose up --build

Future Roadmap
Integrate real DRAM/NAND market data sources
Add market trend detection
Develop price forecasting models
Build analytics dashboard
Add alert and notification system

Developed by Enes T.