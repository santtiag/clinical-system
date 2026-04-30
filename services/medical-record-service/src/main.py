"""
Medical Record Service - Main Application.
Handles electronic medical records, clinical notes, diagnoses, and prescriptions.
"""

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from common.config import settings
from common.logging import setup_logging, get_logger, trace_id_var
from common.database import init_db, close_db
from common.messaging import get_message_publisher, close_message_publisher
from common.exceptions import AppException
from common.schemas import HealthResponse


setup_logging()
logger = get_logger(__name__)

REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
REQUEST_DURATION = Histogram("http_request_duration_seconds", "HTTP request duration", ["method", "endpoint"])


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    logger.info(f"Starting {settings.SERVICE_NAME}...")
    await init_db()
    await get_message_publisher()
    yield
    await close_message_publisher()
    await close_db()


app = FastAPI(
    title="Medical Record Service",
    description="Electronic medical records, clinical notes, diagnoses, and prescriptions",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
    trace_id_var.set(trace_id)
    start_time = datetime.now(timezone.utc)
    response = await call_next(request)
    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path, status=response.status_code).inc()
    REQUEST_DURATION.labels(method=request.method, endpoint=request.url.path).observe(duration)
    response.headers["X-Trace-ID"] = trace_id
    return response


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def liveness():
    return HealthResponse(status="healthy", service=settings.SERVICE_NAME, version="1.0.0", timestamp=datetime.now(timezone.utc))


@app.get("/health/ready", response_model=HealthResponse, tags=["Health"])
async def readiness():
    return HealthResponse(status="ready", service=settings.SERVICE_NAME, version="1.0.0", timestamp=datetime.now(timezone.utc), database="connected", message_queue="connected")


@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    from fastapi.responses import JSONResponse
    return JSONResponse(content=generate_latest().decode("utf-8"), media_type=CONTENT_TYPE_LATEST)


@app.get("/", tags=["Root"])
async def root():
    return {"service": settings.SERVICE_NAME, "version": "1.0.0", "status": "running"}
