# dataharvest/middleware.py


import logging
import time
from abc import ABC, abstractmethod
from urllib.parse import urlparse

log = logging.getLogger("dataharvest.middleware")


class BaseMiddleware(ABC):
    @abstractmethod
    def process_request(self, url: str, headers: dict) -> tuple:
        "Retourne (url, headers) potentiellement modifies."

    @abstractmethod
    def process_response(self, response) -> object:
        "Retourne la response potentiellement transformee."


class LoggingMiddleware(BaseMiddleware):

    def process_request(self, url, headers):
        log.info(f"[GET {url}]")
        self._t0 = time.perf_counter()
        return url, headers

    def process_response(self, response):
        elapsed = time.perf_counter() - getattr(self, "_t0", time.perf_counter())
        status = getattr(response, "status_code", "?")
        log.info(f"[{status} - {elapsed:.2f}s]")
        return response


class RetryMiddleware(BaseMiddleware):


    def __init__(self, config, base_delay: float = 1.0):
        self.max_retries = config.fetcher.retries
        self.base_delay = base_delay

    def process_request(self, url, headers):
        return url, headers

    def process_response(self, response):
        return response

    def should_retry(self, response=None, exception=None) -> bool:
        if exception is not None:
            return True
        if response is not None:
            status = getattr(response, "status_code", 200)
            if status == 429 or 500 <= status < 600:
                return True
        return False

    def backoff_delay(self, attempt: int) -> float:
        return self.base_delay * (2 ** attempt)

