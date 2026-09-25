import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.config import settings
from app.core.logging import logger, request_id_ctx_var
from app.db.base import Base
from app.db.session import engine
from app.api.v1.api import api_router
from app.api.v1.endpoints import payments as root_payments
from app.schemas.common import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables are created
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info(f"{settings.PROJECT_NAME} initialized successfully.")
    yield
    # Shutdown
    logger.info("Application shutting down...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
    description="""
    ## EVE Healthcare Backend API
    Diagnostic Test Booking and Simulated Payment Processing System.
    
    ### Key Features:
    - **Authentication**: JWT-based authentication with role-based access control (Patient / Admin).
    - **Diagnostic Catalogue**: Centers, tests, and centre-specific pricing with Redis caching.
    - **Booking Lifecycle**: State-machine validated booking transitions (`PENDING`, `CONFIRMED`, `FAILED`, `CANCELLED`).
    - **Simulated Payment Gateway**: Instant transaction processing with scenario simulation (`POST /payments/`).
    - **Idempotent Webhooks**: Safe event-driven processing preventing duplicate charges or race conditions (`POST /payments/webhook/`).
    """,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Correlation ID and Request Logging Middleware
@app.middleware("http")
async def correlation_id_and_logging_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    request_id_ctx_var.set(correlation_id)

    start_time = time.time()
    logger.info(f"Incoming request: {request.method} {request.url.path}")

    try:
        response: Response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
        logger.info(
            f"Completed request: {request.method} {request.url.path} "
            f"- Status: {response.status_code} in {process_time:.2f}ms"
        )
        return response
    except Exception as exc:
        process_time = (time.time() - start_time) * 1000
        logger.error(
            f"Unhandled exception during {request.method} {request.url.path}: {str(exc)}",
            exc_info=True,
        )
        raise exc


# Health Check Endpoint
@app.get(
    f"{settings.API_V1_STR}/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Service Health Check",
)
def health_check():
    db_status = "connected"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return HealthResponse(
        status="ok" if db_status == "connected" else "degraded",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        database=db_status,
        cache="configured",
    )


# Include API v1 Routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# Also expose payments router at root level (POST /payments/ and POST /payments/webhook/)
# as requested specifically in assignment prompt
app.include_router(root_payments.router, tags=["Payments & Webhooks (Root Route)"])


@app.get("/", include_in_schema=False)
def root_redirect():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs_url": f"{settings.API_V1_STR}/docs",
    }
