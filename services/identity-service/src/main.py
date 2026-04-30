"""
Identity Service - Main Application Entry Point.
Handles user registration, authentication, and identity management.
"""

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from common.config import settings
from common.logging import setup_logging, get_logger, trace_id_var, request_id_var
from common.database import init_db, close_db
from common.messaging import get_message_publisher, close_message_publisher
from common.exceptions import AppException

from src.presentation.routers import auth, users
from src.presentation.schemas import HealthResponse


# Initialize logging
setup_logging()
logger = get_logger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"]
)

# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan handler for startup/shutdown."""
    # Startup
    logger.info(f"Starting {settings.SERVICE_NAME}...")

    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized")

        # Initialize message publisher
        await get_message_publisher()
        logger.info("Message publisher connected")

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.SERVICE_NAME}...")
    await close_message_publisher()
    await close_db()
    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Identity Service",
    description="User registration, authentication, and identity management for Sistema Clínico",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging and metrics middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware for request logging and metrics."""
    # Generate or extract trace ID
    trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    # Set context variables for logging
    trace_id_var.set(trace_id)
    request_id_var.set(request_id)

    # Process request with timing
    start_time = datetime.now(timezone.utc)
    try:
        response = await call_next(request)
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()

        # Record metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)

        # Add trace headers to response
        response.headers["X-Trace-ID"] = trace_id
        response.headers["X-Request-ID"] = request_id

        return response

    except Exception as e:
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=500
        ).inc()
        raise


# Global exception handler
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle application exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


# Health check endpoints
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def liveness():
    """Liveness probe - basic health check."""
    return HealthResponse(
        status="healthy",
        service=settings.SERVICE_NAME,
        version="1.0.0",
        timestamp=datetime.now(timezone.utc)
    )


@app.get("/health/ready", response_model=HealthResponse, tags=["Health"])
async def readiness():
    """Readiness probe - checks dependencies."""
    return HealthResponse(
        status="ready",
        service=settings.SERVICE_NAME,
        version="1.0.0",
        timestamp=datetime.now(timezone.utc),
        database="connected",
        message_queue="connected"
    )


# Prometheus metrics endpoint
@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """Prometheus metrics endpoint."""
    return JSONResponse(
        content=generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST
    )


# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/users", tags=["Users"])


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "service": settings.SERVICE_NAME,
        "version": "1.0.0",
        "status": "running"
    }
