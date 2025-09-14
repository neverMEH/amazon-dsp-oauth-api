"""
Rate limiter with exponential backoff for Amazon API calls
"""
import asyncio
import time
import random
from typing import Optional, Callable, Any, TypeVar
from functools import wraps
import structlog
from datetime import datetime, timezone
from typing import Dict
from supabase import Client

logger = structlog.get_logger()

T = TypeVar('T')


class RateLimitError(Exception):
    """Exception raised when rate limit is hit"""
    def __init__(self, retry_after: Optional[int] = None):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds")


class ExponentialBackoffRateLimiter:
    """
    Rate limiter with exponential backoff for Amazon API calls

    Features:
    - Exponential backoff with jitter
    - Respects Retry-After headers
    - Circuit breaker pattern
    - Request rate limiting
    """

    def __init__(
        self,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        rate_limit: int = 2,  # requests per second
        supabase_client: Optional[Client] = None,
        user_id: Optional[str] = None
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.rate_limit = rate_limit
        self.request_times = []
        self.consecutive_failures = 0
        self.circuit_open = False
        self.circuit_open_until = 0
        self.supabase_client = supabase_client
        self.user_id = user_id
        self.endpoint_tracking: Dict[str, dict] = {}

    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        endpoint: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Execute function with automatic retry and exponential backoff

        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Exception: After max retries exceeded
        """
        # Check circuit breaker
        if self.circuit_open:
            if time.time() < self.circuit_open_until:
                wait_time = self.circuit_open_until - time.time()
                logger.warning(
                    "Circuit breaker is open",
                    wait_seconds=wait_time,
                    consecutive_failures=self.consecutive_failures
                )
                raise RateLimitError(int(wait_time))
            else:
                # Reset circuit breaker
                self.circuit_open = False
                self.consecutive_failures = 0
                logger.info("Circuit breaker reset")

        for attempt in range(self.max_retries):
            try:
                # Check rate limit
                await self._check_rate_limit()

                # Execute function
                result = await func(*args, **kwargs)

                # Reset consecutive failures on success
                self.consecutive_failures = 0

                # Record successful request
                self.request_times.append(time.time())

                # Track successful request in database
                if endpoint:
                    await self._track_request(endpoint, success=True)

                return result

            except RateLimitError as e:
                self.consecutive_failures += 1

                # Track rate limit hit in database
                if endpoint:
                    await self._track_rate_limit_hit(endpoint, e.retry_after)

                if attempt == self.max_retries - 1:
                    # Open circuit breaker after max retries
                    self._open_circuit_breaker()
                    raise

                # Calculate backoff delay with jitter
                delay = min(
                    self.base_delay * (2 ** attempt) + random.uniform(0, 1),
                    self.max_delay
                )

                # Use Retry-After header if available
                if e.retry_after:
                    delay = max(delay, e.retry_after)

                logger.warning(
                    "Rate limited, retrying with backoff",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    delay_seconds=delay,
                    retry_after=e.retry_after
                )

                await asyncio.sleep(delay)

            except Exception as e:
                # For non-rate-limit errors, check if it's a 429 status
                if hasattr(e, 'status_code') and e.status_code == 429:
                    # Extract Retry-After if available
                    retry_after = None
                    if hasattr(e, 'headers'):
                        retry_after = e.headers.get('Retry-After')
                        if retry_after:
                            retry_after = int(retry_after)

                    # Convert to RateLimitError and retry
                    rate_error = RateLimitError(retry_after)

                    if attempt < self.max_retries - 1:
                        delay = min(
                            self.base_delay * (2 ** attempt) + random.uniform(0, 1),
                            self.max_delay
                        )
                        if retry_after:
                            delay = max(delay, retry_after)

                        logger.warning(
                            "HTTP 429 detected, retrying",
                            attempt=attempt + 1,
                            delay_seconds=delay
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        self._open_circuit_breaker()
                        raise rate_error
                else:
                    # Re-raise non-rate-limit errors
                    raise

    async def _check_rate_limit(self):
        """Check and enforce rate limit"""
        now = time.time()

        # Remove old requests outside the window
        self.request_times = [
            t for t in self.request_times
            if now - t < 1.0  # 1 second window
        ]

        # Check if we're at the limit
        if len(self.request_times) >= self.rate_limit:
            # Calculate wait time
            oldest_request = min(self.request_times)
            wait_time = 1.0 - (now - oldest_request)

            if wait_time > 0:
                logger.debug(
                    "Rate limit throttling",
                    wait_seconds=wait_time,
                    current_requests=len(self.request_times)
                )
                await asyncio.sleep(wait_time)

    def _open_circuit_breaker(self):
        """Open circuit breaker after repeated failures"""
        self.circuit_open = True
        # Circuit stays open for exponentially longer periods
        circuit_open_duration = min(
            self.base_delay * (2 ** min(self.consecutive_failures, 10)),
            300  # Max 5 minutes
        )
        self.circuit_open_until = time.time() + circuit_open_duration

        logger.error(
            "Circuit breaker opened due to repeated failures",
            consecutive_failures=self.consecutive_failures,
            open_duration_seconds=circuit_open_duration
        )

    def reset(self):
        """Reset rate limiter state"""
        self.request_times = []
        self.consecutive_failures = 0
        self.circuit_open = False
        self.circuit_open_until = 0
        self.endpoint_tracking = {}

    async def _track_request(self, endpoint: str, success: bool = True):
        """Track API request in database"""
        if not self.supabase_client or not self.user_id:
            return

        try:
            # Initialize endpoint tracking if needed
            if endpoint not in self.endpoint_tracking:
                self.endpoint_tracking[endpoint] = {
                    'request_count': 0,
                    'limit_hit_count': 0,
                    'window_start': datetime.now(timezone.utc)
                }

            # Update local tracking
            self.endpoint_tracking[endpoint]['request_count'] += 1

            # Update database periodically (every 10 requests or on window reset)
            if self.endpoint_tracking[endpoint]['request_count'] % 10 == 0:
                await self._update_database_tracking(endpoint)

        except Exception as e:
            logger.warning("Failed to track request", error=str(e), endpoint=endpoint)

    async def _track_rate_limit_hit(self, endpoint: str, retry_after: Optional[int]):
        """Track rate limit hit in database"""
        if not self.supabase_client or not self.user_id:
            return

        try:
            # Initialize endpoint tracking if needed
            if endpoint not in self.endpoint_tracking:
                self.endpoint_tracking[endpoint] = {
                    'request_count': 0,
                    'limit_hit_count': 0,
                    'window_start': datetime.now(timezone.utc)
                }

            # Update local tracking
            self.endpoint_tracking[endpoint]['limit_hit_count'] += 1

            # Immediately update database on rate limit hit
            await self._update_database_tracking(endpoint, retry_after=retry_after)

        except Exception as e:
            logger.warning("Failed to track rate limit hit", error=str(e), endpoint=endpoint)

    async def _update_database_tracking(self, endpoint: str, retry_after: Optional[int] = None):
        """Update rate limit tracking in database"""
        if not self.supabase_client or not self.user_id or endpoint not in self.endpoint_tracking:
            return

        try:
            tracking = self.endpoint_tracking[endpoint]
            now = datetime.now(timezone.utc)

            # Check if we need to reset the window (1 hour windows)
            if (now - tracking['window_start']).total_seconds() > 3600:
                # Start new tracking window
                tracking['request_count'] = 0
                tracking['limit_hit_count'] = 0
                tracking['window_start'] = now

            # Prepare data for upsert
            data = {
                'user_id': self.user_id,
                'endpoint': endpoint,
                'request_count': tracking['request_count'],
                'limit_hit_count': tracking['limit_hit_count'],
                'window_start': tracking['window_start'].isoformat(),
                'updated_at': now.isoformat()
            }

            if retry_after:
                data['retry_after_seconds'] = retry_after
                data['last_limit_hit'] = now.isoformat()

            # Upsert to database
            self.supabase_client.table('rate_limit_tracking').upsert(
                data,
                on_conflict='user_id,endpoint,window_start'
            ).execute()

            logger.debug(
                "Updated rate limit tracking",
                endpoint=endpoint,
                request_count=tracking['request_count'],
                limit_hits=tracking['limit_hit_count']
            )

        except Exception as e:
            logger.error("Failed to update database tracking", error=str(e), endpoint=endpoint)


# Global rate limiter instance
amazon_rate_limiter = ExponentialBackoffRateLimiter()


def with_rate_limit(func):
    """
    Decorator to apply rate limiting to async functions

    Usage:
        @with_rate_limit
        async def make_api_call():
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await amazon_rate_limiter.execute_with_retry(func, *args, **kwargs)
    return wrapper