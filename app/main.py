import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.core.config import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, debug=settings.debug)
app.include_router(api_router)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Request-Id"] = request_id
    logger.info(
        "request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    request_id = getattr(request.state, "request_id", None)
    logger.exception("Database error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Database operation failed", "request_id": request_id})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None)
    logger.exception("Unhandled server error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error", "request_id": request_id})


@app.get("/healthz", tags=["health"])
def healthz():
    return {"status": "ok", "environment": settings.environment}
