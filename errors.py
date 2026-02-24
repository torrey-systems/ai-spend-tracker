"""Custom exceptions and error handling for AI Spend Tracker."""

import logging
import time
from typing import Callable, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)


class AISpendTrackerError(Exception):
    """Base exception for AI Spend Tracker."""
    pass


class ProviderError(AISpendTrackerError):
    """Exception raised when a provider API call fails."""
    def __init__(self, provider: str, message: str, status_code: Optional[int] = None):
        self.provider = provider
        self.status_code = status_code
        super().__init__(f"{provider}: {message}")


class ConfigurationError(AISpendTrackerError):
    """Exception raised for configuration issues."""
    pass


class CacheError(AISpendTrackerError):
    """Exception raised for cache-related issues."""
    pass


def retry_on_exception(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """
    Decorator to retry a function on specified exceptions.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {current_delay}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"{func.__name__} failed after {max_retries + 1} attempts: {e}")
            
            raise last_exception
        return wrapper
    return decorator
