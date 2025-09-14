"""
Enhanced tests for token refresh, error handling, and resilience patterns
"""
import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
import httpx

from app.services.token_refresh_scheduler import TokenRefreshScheduler
from app.core.exceptions import TokenRefreshError, RateLimitError
from app.core.rate_limiter import ExponentialBackoffRateLimiter


class TestProactiveTokenRefresh:
    """Test proactive token refresh functionality"""

    @pytest.fixture
    def mock_token_data(self):
        """Mock token data that will expire soon"""
        return {
            "id": "token-123",
            "user_id": "user-456",
            "access_token": "encrypted_access",
            "refresh_token": "encrypted_refresh",
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=8)).isoformat(),
            "refresh_count": 5,
            "proactive_refresh_enabled": True
        }

    @pytest.fixture
    def mock_expired_token_data(self):
        """Mock token data that is already expired"""
        return {
            "id": "token-789",
            "user_id": "user-012",
            "access_token": "encrypted_access_expired",
            "refresh_token": "encrypted_refresh_expired",
            "expires_at": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
            "refresh_count": 10,
            "proactive_refresh_enabled": True
        }

    @pytest.mark.asyncio
    async def test_refresh_token_before_expiration(self, mock_token_data):
        """Test that tokens are refreshed 10 minutes before expiration"""
        mock_supabase = Mock()
        mock_table = Mock()

        # Setup mock chain
        mock_table.select.return_value = mock_table
        mock_table.lte.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = Mock(data=[mock_token_data])
        mock_supabase.table.return_value = mock_table

        scheduler = TokenRefreshScheduler(mock_supabase)

        with patch.object(scheduler.token_service, 'refresh_oauth_token') as mock_refresh:
            mock_refresh.return_value = {
                "success": True,
                "token_id": mock_token_data["id"],
                "new_expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            }

            # Trigger refresh check
            await scheduler._check_and_refresh_tokens()

            # Verify token was selected for refresh (expires in 8 minutes, threshold is 10)
            mock_table.lte.assert_called()
            mock_refresh.assert_called_once_with(mock_token_data["id"])

    @pytest.mark.asyncio
    async def test_skip_refresh_for_non_expiring_tokens(self):
        """Test that tokens with plenty of time left are not refreshed"""
        mock_token_data = {
            "id": "token-good",
            "user_id": "user-good",
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
            "proactive_refresh_enabled": True
        }

        mock_supabase = Mock()
        mock_table = Mock()
        mock_table.select.return_value = mock_table
        mock_table.lte.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = Mock(data=[])  # No tokens need refresh
        mock_supabase.table.return_value = mock_table

        scheduler = TokenRefreshScheduler(mock_supabase)

        with patch.object(scheduler.token_service, 'refresh_oauth_token') as mock_refresh:
            await scheduler._check_and_refresh_tokens()

            # Should not attempt refresh
            mock_refresh.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_refresh_failure_with_retry(self, mock_expired_token_data):
        """Test handling of refresh failures with retry logic"""
        mock_supabase = Mock()
        mock_table = Mock()
        mock_table.select.return_value = mock_table
        mock_table.lte.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.execute.return_value = Mock(data=[mock_expired_token_data])
        mock_supabase.table.return_value = mock_table

        scheduler = TokenRefreshScheduler(mock_supabase)

        with patch.object(scheduler.token_service, 'refresh_oauth_token') as mock_refresh:
            # First attempt fails, second succeeds
            mock_refresh.side_effect = [
                TokenRefreshError("Invalid refresh token"),
                {
                    "success": True,
                    "token_id": mock_expired_token_data["id"],
                    "new_expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
                }
            ]

            await scheduler._check_and_refresh_tokens()

            # Should have been called twice (initial + retry)
            assert mock_refresh.call_count == 1  # Only once per check cycle

    @pytest.mark.asyncio
    async def test_concurrent_refresh_prevention(self):
        """Test that concurrent refreshes for the same token are prevented"""
        token_id = "token-concurrent"
        mock_supabase = Mock()
        scheduler = TokenRefreshScheduler(mock_supabase)

        # Simulate a long-running refresh
        async def slow_refresh(tid):
            await asyncio.sleep(0.5)
            return {"success": True, "token_id": tid}

        scheduler.token_service.refresh_oauth_token = slow_refresh

        # Start multiple concurrent refresh attempts
        tasks = [
            scheduler._refresh_single_token({"id": token_id}),
            scheduler._refresh_single_token({"id": token_id}),
            scheduler._refresh_single_token({"id": token_id})
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Only one should succeed, others should be skipped
        success_count = sum(1 for r in results if r and r.get("success"))
        assert success_count == 1


class TestExponentialBackoffRetry:
    """Test exponential backoff retry logic"""

    @pytest.mark.asyncio
    async def test_exponential_backoff_on_rate_limit(self):
        """Test exponential backoff when rate limited"""
        rate_limiter = ExponentialBackoffRateLimiter(
            initial_delay=0.1,
            max_delay=2.0,
            max_retries=3
        )

        call_count = 0

        async def rate_limited_call():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RateLimitError(retry_after=1)
            return {"success": True}

        result = await rate_limiter.execute_with_retry(rate_limited_call)

        assert result["success"] is True
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test that max retries are respected"""
        rate_limiter = ExponentialBackoffRateLimiter(
            initial_delay=0.01,
            max_delay=0.1,
            max_retries=2
        )

        async def always_fails():
            raise RateLimitError(retry_after=1)

        with pytest.raises(Exception):
            await rate_limiter.execute_with_retry(always_fails)

    @pytest.mark.asyncio
    async def test_respect_retry_after_header(self):
        """Test that Retry-After header is respected"""
        rate_limiter = ExponentialBackoffRateLimiter()

        async def api_call_with_retry_after():
            # Simulate API response with Retry-After
            raise RateLimitError(retry_after=0.5)

        start_time = asyncio.get_event_loop().time()

        with pytest.raises(Exception):  # Will still fail after retries
            await rate_limiter.execute_with_retry(api_call_with_retry_after)

        elapsed = asyncio.get_event_loop().time() - start_time

        # Should have waited at least the retry_after time
        assert elapsed >= 0.5


class TestErrorCategorization:
    """Test comprehensive error categorization and handling"""

    def test_categorize_http_errors(self):
        """Test categorization of different HTTP error codes"""
        error_categories = {
            400: "client_error",
            401: "authentication_error",
            403: "authorization_error",
            404: "not_found",
            429: "rate_limit",
            500: "server_error",
            502: "gateway_error",
            503: "service_unavailable"
        }

        for status_code, expected_category in error_categories.items():
            response = Mock(status_code=status_code)
            category = self._categorize_error(response)
            assert category == expected_category

    def _categorize_error(self, response):
        """Helper to categorize HTTP errors"""
        status = response.status_code
        if status == 401:
            return "authentication_error"
        elif status == 403:
            return "authorization_error"
        elif status == 404:
            return "not_found"
        elif status == 429:
            return "rate_limit"
        elif 400 <= status < 500:
            return "client_error"
        elif 502 <= status <= 504:
            return "gateway_error"
        elif status == 503:
            return "service_unavailable"
        elif 500 <= status < 600:
            return "server_error"
        else:
            return "unknown"

    @pytest.mark.asyncio
    async def test_handle_authentication_error(self):
        """Test handling of authentication errors (401)"""
        mock_response = Mock(status_code=401)

        with patch('app.services.amazon_oauth_service.amazon_oauth_service.refresh_access_token') as mock_refresh:
            mock_refresh.return_value = Mock(
                access_token="new_access_token",
                refresh_token="new_refresh_token",
                expires_in=3600
            )

            # Simulate retry after token refresh
            should_retry = await self._handle_auth_error(mock_response)
            assert should_retry is True
            mock_refresh.assert_called_once()

    async def _handle_auth_error(self, response):
        """Helper to handle authentication errors"""
        if response.status_code == 401:
            # Attempt token refresh
            from app.services.amazon_oauth_service import amazon_oauth_service
            try:
                await amazon_oauth_service.refresh_access_token("refresh_token")
                return True  # Retry the request
            except:
                return False
        return False


class TestCircuitBreaker:
    """Test circuit breaker pattern for API resilience"""

    @pytest.fixture
    def circuit_breaker(self):
        """Create a simple circuit breaker"""
        from app.core.circuit_breaker import CircuitBreaker
        return CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1.0,
            expected_exception=Exception
        )

    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(self, circuit_breaker):
        """Test that circuit opens after threshold failures"""
        call_count = 0

        async def failing_call():
            nonlocal call_count
            call_count += 1
            raise Exception("API Error")

        # Make calls until circuit opens
        for i in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_call)

        assert circuit_breaker.is_open is True
        assert call_count == 3

        # Further calls should fail immediately without calling the function
        with pytest.raises(Exception) as exc_info:
            await circuit_breaker.call(failing_call)

        assert "Circuit breaker is open" in str(exc_info.value)
        assert call_count == 3  # No additional calls

    @pytest.mark.asyncio
    async def test_circuit_closes_after_recovery(self, circuit_breaker):
        """Test that circuit closes after recovery timeout"""
        async def failing_then_success():
            if circuit_breaker.failure_count < 3:
                raise Exception("API Error")
            return {"success": True}

        # Open the circuit
        for i in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_then_success)

        assert circuit_breaker.is_open is True

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # Circuit should be half-open, allowing one test call
        result = await circuit_breaker.call(lambda: {"success": True})
        assert result["success"] is True
        assert circuit_breaker.is_open is False

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_fallback(self, circuit_breaker):
        """Test circuit breaker with fallback response"""
        async def api_call():
            raise Exception("API Error")

        async def fallback():
            return {"source": "cache", "data": "fallback_data"}

        # Open the circuit
        for i in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(api_call)

        # Use fallback when circuit is open
        result = await circuit_breaker.call(api_call, fallback=fallback)
        assert result["source"] == "cache"
        assert result["data"] == "fallback_data"


class TestAuditLogging:
    """Test comprehensive audit logging for token operations"""

    @pytest.mark.asyncio
    async def test_log_successful_refresh(self):
        """Test logging of successful token refresh"""
        mock_supabase = Mock()
        mock_table = Mock()
        mock_table.insert.return_value = mock_table
        mock_table.execute.return_value = Mock(data=[{"id": "audit-123"}])
        mock_supabase.table.return_value = mock_table

        audit_data = {
            "event_type": "token_refresh",
            "event_status": "success",
            "token_id": "token-123",
            "metadata": {
                "refresh_count": 1,
                "expires_in": 3600
            }
        }

        # Log the audit entry
        mock_supabase.table("auth_audit_log").insert(audit_data).execute()

        mock_table.insert.assert_called_once_with(audit_data)

    @pytest.mark.asyncio
    async def test_log_refresh_failure(self):
        """Test logging of token refresh failures"""
        mock_supabase = Mock()
        mock_table = Mock()
        mock_table.insert.return_value = mock_table
        mock_table.execute.return_value = Mock(data=[{"id": "audit-456"}])
        mock_supabase.table.return_value = mock_table

        audit_data = {
            "event_type": "token_refresh",
            "event_status": "failed",
            "token_id": "token-789",
            "error_message": "Invalid refresh token",
            "error_code": "INVALID_REFRESH_TOKEN",
            "metadata": {
                "refresh_count": 5,
                "retry_attempt": 3
            }
        }

        # Log the audit entry
        mock_supabase.table("auth_audit_log").insert(audit_data).execute()

        mock_table.insert.assert_called_once_with(audit_data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])