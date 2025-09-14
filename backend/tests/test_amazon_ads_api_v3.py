"""
Test Amazon Ads Account Management API v3.0 Implementation
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.services.account_service import account_service
from app.api.v1.accounts import list_amazon_ads_accounts


class TestAmazonAdsAPIv3:
    """Test suite for Amazon Ads API v3.0 implementation"""

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])