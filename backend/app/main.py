"""FastAPI retrieval application with sanitized provider and database failures."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from app.api.ask import router as ask_router
from app.api.search import router
from app.db.repository import create_db_engine
from app.errors import (
    ModelOutputError,
    ProviderConfigurationError,
    ProviderError,
    ProviderTimeoutError,
    SearchInputError,
)
from app.settings import Settings


class HealthResponse(BaseModel):
    """Describe application liveness, without asserting database readiness."""

    status: str


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the API without contacting a provider or database at import time."""
    config = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        """Own a lazy database engine without opening provider clients at startup."""
        engine = create_db_engine(config)
        application.state.settings = config
        application.state.db_engine = engine
        try:
            yield
        finally:
            engine.dispose()

    application = FastAPI(title="CiteRAG", version="0.3.0", lifespan=lifespan)

    @application.exception_handler(SearchInputError)
    def input_error(_request: Request, exc: SearchInputError) -> JSONResponse:
        """Return a bounded-input error without echoing the original query."""
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "invalid_search_request",
                    "message": str(exc),
                }
            },
        )

    @application.exception_handler(RequestValidationError)
    def validation_error(_request: Request, _exc: RequestValidationError) -> JSONResponse:
        """Avoid reflecting entire rejected payloads or query strings in validation errors."""
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "invalid_search_request",
                    "message": "Invalid request fields or field types.",
                }
            },
        )

    @application.exception_handler(ProviderConfigurationError)
    def configuration_error(_request: Request, _exc: ProviderConfigurationError) -> JSONResponse:
        """Report disabled/missing credentials without displaying configuration values."""
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "provider_not_configured",
                    "message": "Required model provider is not configured.",
                }
            },
        )

    @application.exception_handler(ProviderTimeoutError)
    def timeout_error(_request: Request, _exc: ProviderTimeoutError) -> JSONResponse:
        """Distinguish an exhausted provider timeout from an empty retrieval result."""
        return JSONResponse(
            status_code=504,
            content={
                "error": {
                    "code": "provider_timeout",
                    "message": "Model provider timed out. Try again later.",
                }
            },
        )

    @application.exception_handler(ProviderError)
    def provider_error(_request: Request, _exc: ProviderError) -> JSONResponse:
        """Suppress provider response bodies and request content."""
        return JSONResponse(
            status_code=502,
            content={
                "error": {
                    "code": "provider_failure",
                    "message": "Model provider failed. Try again later.",
                }
            },
        )

    @application.exception_handler(SQLAlchemyError)
    def database_error(_request: Request, _exc: SQLAlchemyError) -> JSONResponse:
        """Suppress database connection details, SQL statements, and stack traces."""
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "database_unavailable",
                    "message": "Document search is temporarily unavailable.",
                }
            },
        )

    application.include_router(router)
    application.include_router(ask_router)

    @application.exception_handler(ModelOutputError)
    def model_output_error(_request: Request, _exc: ModelOutputError) -> JSONResponse:
        """Distinguish malformed output from evidence-based document refusals."""
        return JSONResponse(
            status_code=502,
            content={
                "error": {
                    "code": "invalid_model_output",
                    "message": "The answer model returned invalid data.",
                }
            },
        )

    @application.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        """Report that the API process is alive."""
        return HealthResponse(status="ok")

    return application


app = create_app()
