import logging

from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler

logger = logging.getLogger("chat")


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return None

    if isinstance(exc, ValidationError):
        logger.warning(
            "validation error view=%s kwargs=%s errors=%s",
            context["view"].__class__.__name__,
            context.get("kwargs"),
            response.data,
        )
        error = {
            "code": "validation_error",
            "message": "Invalid data",
            "details": response.data,
        }
    else:
        detail = response.data.get("detail")
        error = {
            "code": getattr(detail, "code", "error"),
            "message": str(detail) if detail else "Something went wrong",
        }

    response.data = {"error": error}
    return response