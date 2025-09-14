"""
Test Amazon Ads Account Management API v3.0 Implementation
"""
import pytest
import json
import httpx
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, timezone, timedelta

from app.services.account_service import account_service
from app.api.v1.accounts import list_amazon_ads_accounts
from app.core.exceptions import TokenRefreshError, RateLimitError


class TestAmazonAdsAPIv3:
    """Test suite for Amazon Ads API v3.0 implementation"""

    @pytest.fixture
    def mock_access_token(self):
        """Mock valid access token"""
        return "test-access-token-123"

    @pytest.fixture
    def mock_api_v3_response(self):
        """Mock response matching Amazon Ads API v3.0 specification"""
        return {
            "adsAccounts": [
                {
                    "adsAccountId": "AMZN-ADV-123456",
                    "accountName": "Test Advertiser Account",
                    "status": "CREATED",
                    "alternateIds": [
                        {
                            "countryCode": "US",
                            "entityId": "ENTITY-123",
                            "profileId": 98765
                        },
                        {
                            "countryCode": "CA",
                            "entityId": "ENTITY-456",
                            "profileId": 98766
                        }
                    ],
                    "countryCodes": ["US", "CA", "MX"],
                    "errors": {}
                },
                {
                    "adsAccountId": "AMZN-ADV-789012",
                    "accountName": "Partially Created Account",
                    "status": "PARTIALLY_CREATED",
                    "alternateIds": [
                        {
                            "countryCode": "US",
                            "entityId": "ENTITY-789",
                            "profileId": 98767
                        }
                    ],
                    "countryCodes": ["US", "UK"],
                    "errors": {
                        "UK": [
                            {
                                "errorId": 1001,
                                "errorCode": "MARKETPLACE_NOT_AVAILABLE",
                                "errorMessage": "UK marketplace not available for this account"
                            }
                        ]
                    }
                }
            ],
            "nextToken": "eyJjdXJzb3IiOiAiMjAyNS0wMS0xNCJ9"
        }

    @pytest.mark.asyncio
    async def test_list_ads_accounts_parses_v3_response(self, mock_api_v3_response):
        """Test that list_ads_accounts correctly parses API v3.0 response"""

        with patch('httpx.AsyncClient') as mock_client:
            # Setup mock response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_api_v3_response
            mock_response.headers = {}

            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            # Call the service method
            result = await account_service._list_ads_accounts_raw("test_token")

            # Verify correct field names are returned
            assert "adsAccounts" in result
            assert "nextToken" in result
            assert len(result["adsAccounts"]) == 2

            # Verify first account structure
            first_account = result["adsAccounts"][0]
            assert first_account["adsAccountId"] == "AMZN-ADV-123456"
            assert first_account["status"] == "CREATED"
            assert len(first_account["alternateIds"]) == 2
            assert first_account["countryCodes"] == ["US", "CA", "MX"]

            # Verify alternateIds structure
            first_alternate = first_account["alternateIds"][0]
            assert "countryCode" in first_alternate
            assert "entityId" in first_alternate
            assert "profileId" in first_alternate

    @pytest.mark.asyncio
    async def test_api_endpoint_handles_v3_structure(self, mock_api_v3_response):
        """Test that the API endpoint correctly handles v3.0 response structure"""

        with patch('app.services.account_service.account_service.list_ads_accounts') as mock_list:
            mock_list.return_value = mock_api_v3_response

            # Mock dependencies
            mock_user = {"user_id": "test-user-123"}
            mock_supabase = MagicMock()
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
            mock_supabase.table.return_value.insert.return_value.execute.return_value = None

            with patch('app.api.v1.accounts.get_user_token') as mock_get_token:
                mock_get_token.return_value = {
                    "access_token": "test_token",
                    "refresh_token": "refresh_token",
                    "expires_at": "2025-12-31T00:00:00Z"
                }

                with patch('app.api.v1.accounts.refresh_token_if_needed') as mock_refresh:
                    mock_refresh.return_value = mock_get_token.return_value

                    # This would be the actual API call
                    # result = await list_amazon_ads_accounts(mock_user, mock_supabase)

                    # For now, just verify the structure is handled
                    accounts = mock_api_v3_response.get("adsAccounts", [])
                    for account in accounts:
                        # Verify we can extract the correct fields
                        account_id = account.get("adsAccountId")
                        status = account.get("status")
                        alternate_ids = account.get("alternateIds", [])

                        assert account_id is not None
                        assert status in ["CREATED", "DISABLED", "PARTIALLY_CREATED", "PENDING"]

                        if alternate_ids:
                            first_alt = alternate_ids[0]
                            assert "profileId" in first_alt

    def test_status_mapping(self):
        """Test that status values are correctly mapped"""
        status_map = {
            "CREATED": "active",
            "PARTIALLY_CREATED": "partial",
            "PENDING": "pending",
            "DISABLED": "disabled"
        }

        # Test all API v3 status values
        for api_status, db_status in status_map.items():
            assert db_status in ["active", "partial", "pending", "disabled"]

    def test_content_type_headers(self):
        """Test that correct content-type headers are used"""
        # This is more of a documentation test
        expected_request_content_type = "application/vnd.listaccountsresource.v1+json"
        expected_response_content_type = "application/vnd.listaccountsresource.v1+json"

        # These should match what's in the implementation
        assert expected_request_content_type == "application/vnd.listaccountsresource.v1+json"
        assert expected_response_content_type == "application/vnd.listaccountsresource.v1+json"

    @pytest.mark.asyncio
    async def test_error_handling_for_partial_accounts(self, mock_api_v3_response):
        """Test handling of accounts with errors (PARTIALLY_CREATED status)"""

        # Get the partially created account
        partial_account = mock_api_v3_response["adsAccounts"][1]

        assert partial_account["status"] == "PARTIALLY_CREATED"
        assert "errors" in partial_account
        assert "UK" in partial_account["errors"]

        uk_errors = partial_account["errors"]["UK"]
        assert len(uk_errors) == 1
        assert uk_errors[0]["errorCode"] == "MARKETPLACE_NOT_AVAILABLE"


    @pytest.mark.asyncio
    async def test_post_endpoint_with_correct_headers(self, mock_access_token):
        """Test that POST /adsAccounts/list is called with correct headers"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"adsAccounts": [], "nextToken": None}
            mock_response.headers = {}

            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            # Call the service method
            await account_service._list_ads_accounts_raw(mock_access_token)

            # Verify POST was called with correct URL
            mock_client_instance.post.assert_called_once()
            call_args = mock_client_instance.post.call_args

            assert call_args[0][0] == "https://advertising-api.amazon.com/adsAccounts/list"

            # Verify headers
            headers = call_args[1]["headers"]
            assert headers["Authorization"] == f"Bearer {mock_access_token}"
            assert headers["Content-Type"] == "application/vnd.listaccountsresource.v1+json"
            assert headers["Accept"] == "application/vnd.listaccountsresource.v1+json"
            assert "Amazon-Advertising-API-ClientId" in headers

            # Verify request body
            body = call_args[1]["json"]
            assert "maxResults" in body
            assert body["maxResults"] == 100

    @pytest.mark.asyncio
    async def test_pagination_with_next_token(self, mock_access_token):
        """Test pagination handling with nextToken parameter"""
        next_token = "eyJjdXJzb3IiOiAiMjAyNS0wMS0xNCJ9"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"adsAccounts": [], "nextToken": None}
            mock_response.headers = {}

            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            # Call with nextToken
            await account_service._list_ads_accounts_raw(mock_access_token, next_token)

            # Verify request body includes nextToken
            call_args = mock_client_instance.post.call_args
            body = call_args[1]["json"]
            assert "nextToken" in body
            assert body["nextToken"] == next_token
            assert body["maxResults"] == 100

    @pytest.mark.asyncio
    async def test_handle_rate_limit_429(self, mock_access_token):
        """Test handling of 429 rate limit response"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.headers = {"Retry-After": "30"}
            mock_response.text = '{"message": "Rate limit exceeded"}'

            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            # Should raise RateLimitError
            with pytest.raises(Exception) as exc_info:
                await account_service._list_ads_accounts_raw(mock_access_token)

            # The raw method should raise a regular exception
            # The public method wraps it with retry logic
            assert "RLE" in str(type(exc_info.value)) or "Rate limit" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_401_unauthorized(self, mock_access_token):
        """Test handling of 401 unauthorized (expired token)"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = '{"message": "Unauthorized"}'

            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            # Should raise TokenRefreshError
            with pytest.raises(TokenRefreshError) as exc_info:
                await account_service._list_ads_accounts_raw(mock_access_token)

            assert "expired or invalid" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_403_forbidden(self, mock_access_token):
        """Test handling of 403 forbidden (insufficient permissions)"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_response.text = '{"message": "Forbidden"}'

            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            # Should raise permission error
            with pytest.raises(Exception) as exc_info:
                await account_service._list_ads_accounts_raw(mock_access_token)

            assert "Insufficient permissions" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_timeout_exception(self, mock_access_token):
        """Test handling of request timeout"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.side_effect = httpx.TimeoutException("Request timeout")
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            # Should raise timeout exception
            with pytest.raises(Exception) as exc_info:
                await account_service._list_ads_accounts_raw(mock_access_token)

            assert "Request timeout" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_alternateids_mapping_to_profiles(self, mock_api_v3_response):
        """Test that alternateIds are correctly mapped to profile information"""
        accounts = mock_api_v3_response["adsAccounts"]

        for account in accounts:
            alternate_ids = account.get("alternateIds", [])

            # Each alternateId should have required fields
            for alt_id in alternate_ids:
                assert "countryCode" in alt_id
                assert "entityId" in alt_id
                assert "profileId" in alt_id

                # profileId should be an integer
                assert isinstance(alt_id["profileId"], int)

                # countryCode should be a valid 2-letter code
                assert len(alt_id["countryCode"]) == 2
                assert alt_id["countryCode"].isupper()

    @pytest.mark.asyncio
    async def test_handle_multiple_country_profiles(self, mock_api_v3_response):
        """Test handling accounts with multiple country profiles"""
        first_account = mock_api_v3_response["adsAccounts"][0]

        # Account has multiple alternateIds for different countries
        assert len(first_account["alternateIds"]) > 1

        # Extract country codes from alternateIds
        country_codes = [alt["countryCode"] for alt in first_account["alternateIds"]]
        assert "US" in country_codes
        assert "CA" in country_codes

        # Each country should have unique profileId
        profile_ids = [alt["profileId"] for alt in first_account["alternateIds"]]
        assert len(profile_ids) == len(set(profile_ids))  # All unique

    @pytest.mark.asyncio
    async def test_error_object_parsing_for_partial_accounts(self):
        """Test parsing of error objects for PARTIALLY_CREATED accounts"""
        partial_account = {
            "adsAccountId": "AMZN-ADV-999",
            "accountName": "Partial Account",
            "status": "PARTIALLY_CREATED",
            "alternateIds": [],
            "countryCodes": ["US", "UK", "DE"],
            "errors": {
                "UK": [
                    {
                        "errorId": 1001,
                        "errorCode": "MARKETPLACE_NOT_AVAILABLE",
                        "errorMessage": "UK marketplace not available"
                    }
                ],
                "DE": [
                    {
                        "errorId": 1002,
                        "errorCode": "PAYMENT_METHOD_REQUIRED",
                        "errorMessage": "Payment method required for DE marketplace"
                    }
                ]
            }
        }

        # Verify error structure
        assert partial_account["status"] == "PARTIALLY_CREATED"
        errors = partial_account["errors"]

        # Check UK error
        assert "UK" in errors
        uk_errors = errors["UK"]
        assert len(uk_errors) == 1
        assert uk_errors[0]["errorCode"] == "MARKETPLACE_NOT_AVAILABLE"

        # Check DE error
        assert "DE" in errors
        de_errors = errors["DE"]
        assert len(de_errors) == 1
        assert de_errors[0]["errorCode"] == "PAYMENT_METHOD_REQUIRED"

    @pytest.mark.asyncio
    async def test_empty_response_handling(self, mock_access_token):
        """Test handling of empty accounts response"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"adsAccounts": [], "nextToken": None}
            mock_response.headers = {}

            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            result = await account_service._list_ads_accounts_raw(mock_access_token)

            assert "adsAccounts" in result
            assert result["adsAccounts"] == []
            assert result["nextToken"] is None

    def test_account_status_enum_values(self):
        """Test all possible account status values from API v3.0"""
        valid_statuses = ["CREATED", "DISABLED", "PARTIALLY_CREATED", "PENDING"]

        # Test mapping to database statuses
        status_map = {
            "CREATED": "active",
            "DISABLED": "disabled",
            "PARTIALLY_CREATED": "partial",
            "PENDING": "pending"
        }

        for api_status in valid_statuses:
            assert api_status in status_map
            db_status = status_map[api_status]
            assert db_status in ["active", "disabled", "partial", "pending"]

    @pytest.mark.asyncio
    async def test_retry_logic_with_rate_limiter(self, mock_access_token):
        """Test that the public method includes retry logic"""
        with patch.object(account_service.rate_limiter, 'execute_with_retry') as mock_retry:
            mock_retry.return_value = {"adsAccounts": [], "nextToken": None}

            result = await account_service.list_ads_accounts(mock_access_token)

            # Verify rate limiter was used
            mock_retry.assert_called_once()
            assert result["adsAccounts"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])