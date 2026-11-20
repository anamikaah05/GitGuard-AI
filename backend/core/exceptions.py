"""
core/exceptions.py — Custom HTTP exception handlers for FastAPI

Registers handlers for common error scenarios so the API always returns
consistent JSON error bodies instead of default FastAPI/Starlette responses.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ModelNotLoadedError(RuntimeError):
    """Raised when a model is requested before it has been loaded."""


class GitHubAPIError(RuntimeError):
    """Raised when the GitHub API returns an unexpected error."""


class InvalidInputError(ValueError):
    """Raised when request input fails domain-level validation."""


# ── Handler registration ──────────────────────────────────────────────────────

def register_exception_handlers(app: FastAPI) -> None:
    """Attach all custom exception handlers to the FastAPI application."""

    @app.exception_handler(ModelNotLoadedError)
    async def model_not_loaded_handler(
        request: Request, exc: ModelNotLoadedError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"error": "model_not_loaded", "detail": str(exc)},
        )

    @app.exception_handler(GitHubAPIError)
    async def github_api_error_handler(
        request: Request, exc: GitHubAPIError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content={"error": "github_api_error", "detail": str(exc)},
        )

    @app.exception_handler(InvalidInputError)
    async def invalid_input_handler(
        request: Request, exc: InvalidInputError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": "invalid_input", "detail": str(exc)},
        )
