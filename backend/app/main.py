"""FastAPI skeleton; retrieval and answering arrive in M2 and M3."""

from fastapi import FastAPI
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Describe application liveness, without asserting database readiness."""

    status: str


def create_app() -> FastAPI:
    """Create the API without contacting a provider or database at import time."""
    application = FastAPI(title="CiteRAG", version="0.1.0")

    @application.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        """Report that the API process is alive."""
        return HealthResponse(status="ok")

    return application


app = create_app()
