from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "application_starting",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )


    from app.core.database import check_db_connection
    db_ok = await check_db_connection()
    if not db_ok:
        logger.error("startup_db_connection_failed")

        if settings.is_production:
            raise RuntimeError("Cannot connect to database on startup")
        else:
            logger.info("startup_db_connection_ok")

        logger.info("application_started")

        yield

        logger.info("application_shutting_down")

        from app.core.database import engine
        await engine.dispose()

def create_application() -> FastAPI:

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
         description="""
## Memory Market Intelligence Platform
 
AI yatirimlarinin DRAM, NAND, RAM ve SSD piyasasina etkisini analiz eden API.
 
### Features
 Real-time price tracking
 Time-series data analysis
 Price forecasting (coming soon)
 Anomaly detection (coming soon)
        """,
        
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
  
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"]
    )

    app.add_middleware(GZipMiddleware, minimum_size=1000)

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            "unhandled_exception",
            path=request.url.path,
            method=request.method,
            error=str(exc),
            error_type=type(exc).__name__,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "message": "An internal error occurred",
                "request_id": request.headers.get("X-Request-ID", "unknown"),
            },
        )

    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX.replace("/v1", ""))


    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "health": "/api/v1/health",
        }
    return app


app = create_application()