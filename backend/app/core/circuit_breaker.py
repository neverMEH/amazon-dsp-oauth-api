"""
Circuit Breaker pattern implementation for API resilience
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Callable, Any, Type
from enum import Enum
import structlog

logger = structlog.get_logger()


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures

    The circuit breaker has three states:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fail immediately
    - HALF_OPEN: Testing if service recovered, limited requests allowed

    Features:
    - Configurable failure threshold
    - Automatic recovery testing
    - Fallback support
    - Metrics tracking
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception,
        name: Optional[str] = None
    ):
        """
        Initialize circuit breaker

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before testing recovery
            expected_exception: Exception type to catch
            name: Name for logging
        """
        self.name = name or "CircuitBreaker"
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.success_count = 0
        self.total_calls = 0

    @property
    def is_open(self) -> bool:
        """Check if circuit is open"""
        return self.state == CircuitState.OPEN

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed"""
        return self.state == CircuitState.CLOSED

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open"""
        return self.state == CircuitState.HALF_OPEN

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return False

        time_since_failure = (
            datetime.now(timezone.utc) - self.last_failure_time
        ).total_seconds()

        return time_since_failure >= self.recovery_timeout

    async def call(
        self,
        func: Callable,
        fallback: Optional[Callable] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function through circuit breaker

        Args:
            func: Async function to execute
            fallback: Optional fallback function if circuit is open
            *args: Arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from func or fallback

        Raises:
            Exception: If circuit is open and no fallback provided
        """
        self.total_calls += 1

        # Check if circuit should transition from open to half-open
        if self.is_open and self._should_attempt_reset():
            self.state = CircuitState.HALF_OPEN
            logger.info(
                f"{self.name}: Circuit transitioning to half-open",
                failure_count=self.failure_count
            )

        # If circuit is open, use fallback or fail fast
        if self.is_open:
            logger.warning(
                f"{self.name}: Circuit is open, rejecting call",
                failure_count=self.failure_count
            )
            if fallback:
                return await self._execute_fallback(fallback, *args, **kwargs)
            raise Exception(f"Circuit breaker is open for {self.name}")

        # Try to execute the function
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Success - update state
            self._on_success()
            return result

        except self.expected_exception as e:
            # Failure - update state
            self._on_failure()

            # If we have a fallback and circuit just opened, use it
            if self.is_open and fallback:
                return await self._execute_fallback(fallback, *args, **kwargs)

            raise e

    def _on_success(self):
        """Handle successful call"""
        self.success_count += 1

        if self.is_half_open:
            # Success in half-open state closes the circuit
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            logger.info(
                f"{self.name}: Circuit closed after successful test",
                success_count=self.success_count
            )
        elif self.is_closed:
            # Reset failure count on success
            self.failure_count = 0

    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc)

        if self.is_half_open:
            # Failure in half-open state reopens the circuit
            self.state = CircuitState.OPEN
            logger.warning(
                f"{self.name}: Circuit reopened after test failure",
                failure_count=self.failure_count
            )
        elif self.failure_count >= self.failure_threshold:
            # Too many failures, open the circuit
            self.state = CircuitState.OPEN
            logger.error(
                f"{self.name}: Circuit opened after {self.failure_count} failures",
                threshold=self.failure_threshold
            )

    async def _execute_fallback(self, fallback: Callable, *args, **kwargs) -> Any:
        """Execute fallback function"""
        try:
            if asyncio.iscoroutinefunction(fallback):
                return await fallback(*args, **kwargs)
            else:
                return fallback(*args, **kwargs)
        except Exception as e:
            logger.error(f"{self.name}: Fallback also failed", error=str(e))
            raise

    def reset(self):
        """Manually reset the circuit breaker"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        logger.info(f"{self.name}: Circuit manually reset")

    def get_stats(self) -> dict:
        """Get circuit breaker statistics"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "total_calls": self.total_calls,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout
        }


class CircuitBreakerManager:
    """
    Manages multiple circuit breakers for different services
    """

    def __init__(self):
        """Initialize circuit breaker manager"""
        self.breakers: dict[str, CircuitBreaker] = {}

    def get_or_create(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ) -> CircuitBreaker:
        """
        Get existing or create new circuit breaker

        Args:
            name: Unique name for the circuit breaker
            failure_threshold: Number of failures before opening
            recovery_timeout: Recovery timeout in seconds
            expected_exception: Exception type to catch

        Returns:
            Circuit breaker instance
        """
        if name not in self.breakers:
            self.breakers[name] = CircuitBreaker(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                expected_exception=expected_exception,
                name=name
            )

        return self.breakers[name]

    def get_all_stats(self) -> dict:
        """Get statistics for all circuit breakers"""
        return {
            name: breaker.get_stats()
            for name, breaker in self.breakers.items()
        }

    def reset_all(self):
        """Reset all circuit breakers"""
        for breaker in self.breakers.values():
            breaker.reset()


# Global circuit breaker manager
circuit_breaker_manager = CircuitBreakerManager()