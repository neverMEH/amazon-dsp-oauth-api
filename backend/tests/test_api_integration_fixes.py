"""
Tests for Amazon Account Management API integration fixes
Tests POST method, content-type headers, rate limiting, and retry logic
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.services.account_service import AmazonAccountService
from app.config import settings


class TestAccountManagementAPIFixes:
    """Test suite for Account Management API fixes"""

    @pytest.fixture
    def account_service(self):
        """Create AmazonAccountService instance"""
        return AmazonAccountService()

    @pytest.fixture
    def mock_access_token(self):
        """Mock access token"""
        return "test_access_token_12345"

    @pytest.fixture
    def mock_amazon_response(self):
        """Mock successful Amazon API response"""
        return {
            "accounts": [
                {
                    "accountId": "ENTITY123456",
                    "name": "Test Account",
                    "type": "ADVERTISER",
                    "status": "ACTIVE",
                    "marketplaceId": "ATVPDKIKX0DER",
                    "marketplaceName": "United States",
                    "countryCode": "US",
                    "currencyCode": "USD",
                    "timezone": "America/Los_Angeles",
                    "createdDate": "2024-01-01T00:00:00Z",
                    "lastUpdatedDate": "2024-12-01T00:00:00Z"
                }
            ],
            "nextToken": None
        }

    @pytest.mark.asyncio
    async def test_account_management_api_uses_post_method(self, account_service, mock_access_token):
        """Test that Account Management API correctly uses POST method"""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"accounts": [], "nextToken": None}
            mock_post.return_value = mock_response

            await account_service.list_ads_accounts(mock_access_token)

            # Verify POST method was called, not GET
            mock_post.assert_called_once()
            call_args = mock_post.call_args

            # Verify the correct URL
            assert call_args[0][0] == "https://advertising-api.amazon.com/adsAccounts/list"

    @pytest.mark.asyncio
    async def test_account_management_api_content_type_header(self, account_service, mock_access_token):
        """Test correct content-type header for Account Management API v1"""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"accounts": [], "nextToken": None}
            mock_post.return_value = mock_response

            await account_service.list_ads_accounts(mock_access_token)

            # Verify headers include correct content-type
            call_kwargs = mock_post.call_args[1]
            headers = call_kwargs.get('headers', {})

            assert 'Content-Type' in headers
            assert headers['Content-Type'] == 'application/vnd.listaccountsresource.v1+json'
            assert headers['Accept'] == 'application/json'

    @pytest.mark.asyncio
    async def test_account_management_api_request_body(self, account_service, mock_access_token):
        """Test request body structure for Account Management API"""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"accounts": [], "nextToken": None}
            mock_post.return_value = mock_response

            # Test without pagination token
            await account_service.list_ads_accounts(mock_access_token)

            call_kwargs = mock_post.call_args[1]
            request_body = call_kwargs.get('json', {})

            assert 'maxResults' in request_body
            assert request_body['maxResults'] == 100
            assert 'nextToken' not in request_body or request_body['nextToken'] is None

            # Reset mock
            mock_post.reset_mock()

            # Test with pagination token
            await account_service.list_ads_accounts(mock_access_token, next_token="token123")

            call_kwargs = mock_post.call_args[1]
            request_body = call_kwargs.get('json', {})

            assert request_body['nextToken'] == "token123"

    @pytest.mark.asyncio
    async def test_rate_limit_429_handling(self, account_service, mock_access_token):
        """Test proper handling of 429 rate limit responses"""
        with patch('httpx.AsyncClient.post') as mock_post:
            # First call returns 429 with Retry-After header
            rate_limit_response = Mock()
            rate_limit_response.status_code = 429
            rate_limit_response.headers = {'Retry-After': '2'}
            rate_limit_response.json.return_value = {
                "errors": [{"code": "RATE_LIMIT_EXCEEDED"}]
            }

            # Second call succeeds
            success_response = Mock()
            success_response.status_code = 200
            success_response.json.return_value = {"accounts": [], "nextToken": None}

            mock_post.side_effect = [rate_limit_response, success_response]

            # Should handle rate limit and retry
            result = await account_service.list_ads_accounts(mock_access_token)

            # Verify retry occurred
            assert mock_post.call_count == 2
            assert result == {"accounts": [], "nextToken": None}

    @pytest.mark.asyncio
    async def test_retry_after_header_parsing(self, account_service, mock_access_token):
        """Test parsing and respecting Retry-After header"""
        with patch('httpx.AsyncClient.post') as mock_post:
            with patch('asyncio.sleep') as mock_sleep:
                rate_limit_response = Mock()
                rate_limit_response.status_code = 429
                rate_limit_response.headers = {'Retry-After': '5'}
                rate_limit_response.json.return_value = {"error": "Rate limited"}

                success_response = Mock()
                success_response.status_code = 200
                success_response.json.return_value = {"accounts": []}

                mock_post.side_effect = [rate_limit_response, success_response]

                await account_service.list_ads_accounts(mock_access_token)

                # Verify sleep was called with parsed Retry-After value
                mock_sleep.assert_called_once()
                sleep_duration = mock_sleep.call_args[0][0]
                assert sleep_duration >= 5  # Should respect Retry-After header

    @pytest.mark.asyncio
    async def test_exponential_backoff_on_repeated_rate_limits(self, account_service, mock_access_token):
        """Test exponential backoff when multiple rate limits occur"""
        with patch('httpx.AsyncClient.post') as mock_post:
            with patch('asyncio.sleep') as mock_sleep:
                # Multiple rate limit responses
                rate_limit_response = Mock()
                rate_limit_response.status_code = 429
                rate_limit_response.headers = {}  # No Retry-After header
                rate_limit_response.json.return_value = {"error": "Rate limited"}

                success_response = Mock()
                success_response.status_code = 200
                success_response.json.return_value = {"accounts": []}

                # Three rate limits then success
                mock_post.side_effect = [
                    rate_limit_response,
                    rate_limit_response,
                    rate_limit_response,
                    success_response
                ]

                await account_service.list_ads_accounts(mock_access_token)

                # Verify exponential backoff pattern
                assert mock_sleep.call_count == 3
                sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]

                # Each sleep should be longer than the previous
                assert sleep_calls[1] > sleep_calls[0]
                assert sleep_calls[2] > sleep_calls[1]

    @pytest.mark.asyncio
    async def test_max_retry_attempts(self, account_service, mock_access_token):
        """Test that retries stop after maximum attempts"""
        with patch('httpx.AsyncClient.post') as mock_post:
            # Always return rate limit error
            rate_limit_response = Mock()
            rate_limit_response.status_code = 429
            rate_limit_response.headers = {'Retry-After': '1'}
            rate_limit_response.json.return_value = {"error": "Rate limited"}

            mock_post.return_value = rate_limit_response

            # Should raise exception after max retries
            with pytest.raises(HTTPException) as exc_info:
                await account_service.list_ads_accounts(mock_access_token)

            assert exc_info.value.status_code == 429
            # Verify max retry attempts (e.g., 5)
            assert mock_post.call_count <= 5

    @pytest.mark.asyncio
    async def test_pagination_with_rate_limiting(self, account_service, mock_access_token):
        """Test pagination continues correctly after rate limit recovery"""
        with patch('httpx.AsyncClient.post') as mock_post:
            # First page succeeds
            page1_response = Mock()
            page1_response.status_code = 200
            page1_response.json.return_value = {
                "accounts": [{"accountId": "1"}],
                "nextToken": "page2token"
            }

            # Second page rate limited
            rate_limit_response = Mock()
            rate_limit_response.status_code = 429
            rate_limit_response.headers = {'Retry-After': '1'}
            rate_limit_response.json.return_value = {"error": "Rate limited"}

            # Second page retry succeeds
            page2_response = Mock()
            page2_response.status_code = 200
            page2_response.json.return_value = {
                "accounts": [{"accountId": "2"}],
                "nextToken": None
            }

            mock_post.side_effect = [
                page1_response,
                rate_limit_response,
                page2_response
            ]

            # Get first page
            result1 = await account_service.list_ads_accounts(mock_access_token)
            assert result1["nextToken"] == "page2token"

            # Get second page (will be rate limited then succeed)
            result2 = await account_service.list_ads_accounts(
                mock_access_token,
                next_token="page2token"
            )
            assert result2["nextToken"] is None
            assert len(result2["accounts"]) == 1

    @pytest.mark.asyncio
    async def test_different_error_codes_handling(self, account_service, mock_access_token):
        """Test handling of different error responses"""
        with patch('httpx.AsyncClient.post') as mock_post:
            # Test 401 Unauthorized
            unauthorized_response = Mock()
            unauthorized_response.status_code = 401
            unauthorized_response.json.return_value = {"error": "Unauthorized"}
            mock_post.return_value = unauthorized_response

            with pytest.raises(HTTPException) as exc_info:
                await account_service.list_ads_accounts(mock_access_token)
            assert exc_info.value.status_code == 401

            # Test 500 Server Error with retry
            server_error_response = Mock()
            server_error_response.status_code = 500
            server_error_response.json.return_value = {"error": "Internal Server Error"}

            success_response = Mock()
            success_response.status_code = 200
            success_response.json.return_value = {"accounts": []}

            mock_post.side_effect = [server_error_response, success_response]

            # Should retry on 500 and succeed
            result = await account_service.list_ads_accounts(mock_access_token)
            assert result == {"accounts": []}

    @pytest.mark.asyncio
    async def test_timeout_handling(self, account_service, mock_access_token):
        """Test handling of request timeouts"""
        with patch('httpx.AsyncClient.post') as mock_post:
            # Simulate timeout
            mock_post.side_effect = httpx.TimeoutException("Request timed out")

            with pytest.raises(HTTPException) as exc_info:
                await account_service.list_ads_accounts(mock_access_token)

            assert "timeout" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_connection_error_handling(self, account_service, mock_access_token):
        """Test handling of connection errors"""
        with patch('httpx.AsyncClient.post') as mock_post:
            # Simulate connection error
            mock_post.side_effect = httpx.ConnectError("Connection failed")

            with pytest.raises(HTTPException) as exc_info:
                await account_service.list_ads_accounts(mock_access_token)

            assert "connection" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_all_required_headers_present(self, account_service, mock_access_token):
        """Test all required headers are included in the request"""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"accounts": []}
            mock_post.return_value = mock_response

            await account_service.list_ads_accounts(mock_access_token)

            call_kwargs = mock_post.call_args[1]
            headers = call_kwargs.get('headers', {})

            # Verify all required headers
            assert 'Authorization' in headers
            assert headers['Authorization'] == f'Bearer {mock_access_token}'
            assert 'Amazon-Advertising-API-ClientId' in headers
            assert headers['Amazon-Advertising-API-ClientId'] == settings.amazon_client_id
            assert 'Content-Type' in headers
            assert headers['Content-Type'] == 'application/vnd.listaccountsresource.v1+json'
            assert 'Accept' in headers
            assert headers['Accept'] == 'application/json'


class TestProfilesAPIPaginationFix:
    """Test suite for Profiles API pagination implementation"""

    @pytest.fixture
    def account_service(self):
        """Create AmazonAccountService instance"""
        return AmazonAccountService()

    @pytest.mark.asyncio
    async def test_profiles_api_pagination_parameters(self, account_service):
        """Test that Profiles API includes pagination parameters"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = []
            mock_get.return_value = mock_response

            await account_service.list_profiles("test_token", next_token="profile_page_2")

            call_kwargs = mock_get.call_args[1]
            params = call_kwargs.get('params', {})

            assert 'maxResults' in params
            assert params['maxResults'] == 100
            assert 'nextToken' in params
            assert params['nextToken'] == "profile_page_2"

    @pytest.mark.asyncio
    async def test_profiles_api_pagination_response(self, account_service):
        """Test handling of paginated profiles response"""
        with patch('httpx.AsyncClient.get') as mock_get:
            # Mock paginated response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "profiles": [
                    {"profileId": "1", "profileName": "Profile 1"},
                    {"profileId": "2", "profileName": "Profile 2"}
                ],
                "nextToken": "next_page_token"
            }
            mock_response.headers = {"X-Amz-Next-Token": "next_page_token"}
            mock_get.return_value = mock_response

            result = await account_service.list_profiles("test_token")

            assert "profiles" in result
            assert len(result["profiles"]) == 2
            assert "nextToken" in result
            assert result["nextToken"] == "next_page_token"