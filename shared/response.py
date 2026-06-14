from datetime import datetime, timezone
from typing import Any


def get_metadata(service: str, version: str = "1.0.0") -> dict:
    return {
        "service": service,
        "version": version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def success_response(data: Any, service: str, version: str = "1.0.0") -> dict:
    return {
        "success": True,
        "data": data,
        "error": None,
        "metadata": get_metadata(service, version),
    }


def error_response(message: str, service: str, version: str = "1.0.0") -> dict:
    return {
        "success": False,
        "data": None,
        "error": message,
        "metadata": get_metadata(service, version),
    }
