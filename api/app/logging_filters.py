import logging


class StripQueryString(logging.Filter):
    """Removes the query string from uvicorn access log lines.

    Queries carry user addresses (/geocode?q=) and coordinates (lat, lon), which
    must never be logged (SPEC: Never).
    """

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        # uvicorn.access args: (client_addr, method, full_path, http_version, status_code)
        if isinstance(args, tuple) and len(args) >= 3 and isinstance(args[2], str):
            record.args = (*args[:2], args[2].split("?", 1)[0], *args[3:])
        return True


def install() -> None:
    logger = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, StripQueryString) for f in logger.filters):
        logger.addFilter(StripQueryString())
