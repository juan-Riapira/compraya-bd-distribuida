"""Errores de dominio y su traducción a respuestas HTTP.

Los servicios lanzan estas excepciones sin saber nada de HTTP;
`register_exception_handlers` las convierte en JSON con el código adecuado.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    status_code: int = 400
    code: str = "domain_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    status_code = 404
    code = "not_found"


class EmptyCartError(DomainError):
    status_code = 400
    code = "empty_cart"


class InsufficientStockError(DomainError):
    status_code = 409
    code = "insufficient_stock"


class PaymentDeclinedError(DomainError):
    status_code = 402
    code = "payment_declined"


class DuplicateRequestError(DomainError):
    status_code = 409
    code = "duplicate_request"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.code, "detail": exc.message},
        )
