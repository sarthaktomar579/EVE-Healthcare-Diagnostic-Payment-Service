import logging
import sys
from contextvars import ContextVar
import uuid

# Context variable to hold request correlation ID
request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="")


class StructuredFormatter(logging.Formatter):
    """
    Standard production-grade logging formatter that includes request correlation IDs
    and contextual information.
    """
    def format(self, record: logging.LogRecord) -> str:
        req_id = request_id_ctx_var.get()
        record.request_id = f"[{req_id}]" if req_id else "[-]"
        return super().format(record)


def setup_logging(debug: bool = True) -> logging.Logger:
    """Configures application-wide logging"""
    logger = logging.getLogger("eve_healthcare")
    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG if debug else logging.INFO)
        formatter = StructuredFormatter(
            fmt="%(asctime)s | %(levelname)-7s | %(request_id)s %(name)s:%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = setup_logging()
