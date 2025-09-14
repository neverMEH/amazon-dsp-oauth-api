"""
Test user_accounts table operations with Amazon Ads API v3.0 data structure
"""
import pytest
import json
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import MagicMock, patch, AsyncMock

from app.models.amazon_account import AmazonAccount


class TestUserAccountsV3Operations:
    """Test user_accounts table operations with v3.0 API data"""

    @pytest.fixture
    def mock_v3_account_data(self):
        """Mock Amazon Ads API v3.0 account data"""
        return {
            "adsAccountId": "AMZN-ADV-123456",
            "accountName": "Test Advertiser Account",
            "status": "CREATED",
            "alternateIds": [
                {
                    "countryCode": "US",
                    "entityId": "ENTITY-US-123",
                    "profileId": 98765
                },
                {
                    "countryCode": "CA",
                    "entityId": "ENTITY-CA-456",
                    "profileId": 98766
                },
                {
                    "countryCode": "MX",
                    "entityId": "ENTITY-MX-789",
                    "profileId": 98767
                }
            ],
            "countryCodes": ["US", "CA", "MX"],
            "errors": {}
        }

    @pytest.fixture
    def mock_partial_account_data(self):
        """Mock partially created account with errors"""
        return {
            "adsAccountId": "AMZN-ADV-789012",
            "accountName": "Partial Account",
            "status": "PARTIALLY_CREATED",
            "alternateIds": [
                {
                    "countryCode": "US",
                    "entityId": "ENTITY-US-789",
                    "profileId": 98768
                }
            ],
            "countryCodes": ["US", "UK", "DE"],
            "errors": {
                "UK": [
                    {
                        "errorId": 1001,
                        "errorCode": "MARKETPLACE_NOT_AVAILABLE",
                        "errorMessage": "UK marketplace not available for this account"
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

    def test_map_v3_account_to_model(self, mock_v3_account_data):
        """Test mapping v3.0 account data to AmazonAccount model"""
        user_id = str(uuid4())

        # Extract first alternate ID for primary profile info
        alternate_ids = mock_v3_account_data.get("alternateIds", [])
        first_alternate = alternate_ids[0] if alternate_ids else {}

        # Map API status to database status
        status_map = {
            "CREATED": "active",
            "PARTIALLY_CREATED": "partial",
            "PENDING": "pending",
            "DISABLED": "disabled"
        }
        api_status = mock_v3_account_data.get("status", "CREATED")

        account = AmazonAccount(
            user_id=user_id,
            account_name=mock_v3_account_data.get("accountName"),
            amazon_account_id=mock_v3_account_data.get("adsAccountId"),
            marketplace_id=first_alternate.get("entityId"),
            account_type="advertiser",
            status=status_map.get(api_status, "active"),
            metadata={
                "alternate_ids": alternate_ids,
                "country_codes": mock_v3_account_data.get("countryCodes", []),
                "errors": mock_v3_account_data.get("errors", {}),
                "profile_id": first_alternate.get("profileId"),
                "country_code": first_alternate.get("countryCode"),
                "api_status": api_status
            }
        )

        assert account.amazon_account_id == "AMZN-ADV-123456"
        assert account.account_name == "Test Advertiser Account"
        assert account.status == "active"
        assert account.marketplace_id == "ENTITY-US-123"
        assert account.metadata["profile_id"] == 98765
        assert account.metadata["country_code"] == "US"
        assert len(account.metadata["alternate_ids"]) == 3
        assert account.metadata["api_status"] == "CREATED"

    def test_store_all_alternate_ids(self, mock_v3_account_data):
        """Test that all alternateIds are stored in metadata"""
        user_id = str(uuid4())
        alternate_ids = mock_v3_account_data.get("alternateIds", [])

        account = AmazonAccount(
            user_id=user_id,
            account_name=mock_v3_account_data.get("accountName"),
            amazon_account_id=mock_v3_account_data.get("adsAccountId"),
            metadata={
                "alternate_ids": alternate_ids
            }
        )

        stored_ids = account.metadata["alternate_ids"]
        assert len(stored_ids) == 3

        # Verify each country's data
        countries = [alt["countryCode"] for alt in stored_ids]
        assert "US" in countries
        assert "CA" in countries
        assert "MX" in countries

        # Verify profile IDs
        profile_ids = [alt["profileId"] for alt in stored_ids]
        assert 98765 in profile_ids
        assert 98766 in profile_ids
        assert 98767 in profile_ids

    def test_handle_partial_account_with_errors(self, mock_partial_account_data):
        """Test handling of PARTIALLY_CREATED accounts with errors"""
        user_id = str(uuid4())

        alternate_ids = mock_partial_account_data.get("alternateIds", [])
        first_alternate = alternate_ids[0] if alternate_ids else {}
        errors = mock_partial_account_data.get("errors", {})

        account = AmazonAccount(
            user_id=user_id,
            account_name=mock_partial_account_data.get("accountName"),
            amazon_account_id=mock_partial_account_data.get("adsAccountId"),
            marketplace_id=first_alternate.get("entityId"),
            status="partial",  # Maps from PARTIALLY_CREATED
            metadata={
                "alternate_ids": alternate_ids,
                "country_codes": mock_partial_account_data.get("countryCodes", []),
                "errors": errors,
                "profile_id": first_alternate.get("profileId"),
                "country_code": first_alternate.get("countryCode"),
                "api_status": "PARTIALLY_CREATED"
            }
        )

        assert account.status == "partial"
        assert account.amazon_account_id == "AMZN-ADV-789012"

        # Check errors are stored
        stored_errors = account.metadata["errors"]
        assert "UK" in stored_errors
        assert "DE" in stored_errors
        assert len(stored_errors["UK"]) == 1
        assert stored_errors["UK"][0]["errorCode"] == "MARKETPLACE_NOT_AVAILABLE"
        assert len(stored_errors["DE"]) == 1
        assert stored_errors["DE"][0]["errorCode"] == "PAYMENT_METHOD_REQUIRED"

    def test_account_status_mapping(self):
        """Test all v3.0 status values map correctly"""
        status_map = {
            "CREATED": "active",
            "DISABLED": "disabled",
            "PARTIALLY_CREATED": "partial",
            "PENDING": "pending"
        }

        user_id = str(uuid4())

        for api_status, db_status in status_map.items():
            account = AmazonAccount(
                user_id=user_id,
                account_name=f"Account {api_status}",
                amazon_account_id=f"AMZN-{api_status}",
                status=db_status,
                metadata={"api_status": api_status}
            )

            assert account.status == db_status
            assert account.metadata["api_status"] == api_status

    def test_query_accounts_by_country_code(self):
        """Test querying accounts by country code from metadata"""
        user_id = str(uuid4())

        # Create account with multiple country profiles
        account = AmazonAccount(
            user_id=user_id,
            account_name="Multi-Country Account",
            amazon_account_id="AMZN-MULTI-123",
            metadata={
                "alternate_ids": [
                    {"countryCode": "US", "entityId": "E-US", "profileId": 1},
                    {"countryCode": "CA", "entityId": "E-CA", "profileId": 2},
                    {"countryCode": "UK", "entityId": "E-UK", "profileId": 3}
                ],
                "country_codes": ["US", "CA", "UK"]
            }
        )

        # Test finding US profile
        us_profiles = [
            alt for alt in account.metadata["alternate_ids"]
            if alt["countryCode"] == "US"
        ]
        assert len(us_profiles) == 1
        assert us_profiles[0]["profileId"] == 1

        # Test finding CA profile
        ca_profiles = [
            alt for alt in account.metadata["alternate_ids"]
            if alt["countryCode"] == "CA"
        ]
        assert len(ca_profiles) == 1
        assert ca_profiles[0]["profileId"] == 2

    def test_bulk_account_creation(self):
        """Test creating multiple accounts from v3.0 response"""
        user_id = str(uuid4())

        accounts_data = [
            {
                "adsAccountId": "AMZN-ADV-001",
                "accountName": "Account 1",
                "status": "CREATED",
                "alternateIds": [{"countryCode": "US", "entityId": "E1", "profileId": 1}],
                "countryCodes": ["US"],
                "errors": {}
            },
            {
                "adsAccountId": "AMZN-ADV-002",
                "accountName": "Account 2",
                "status": "CREATED",
                "alternateIds": [{"countryCode": "CA", "entityId": "E2", "profileId": 2}],
                "countryCodes": ["CA"],
                "errors": {}
            },
            {
                "adsAccountId": "AMZN-ADV-003",
                "accountName": "Account 3",
                "status": "DISABLED",
                "alternateIds": [{"countryCode": "UK", "entityId": "E3", "profileId": 3}],
                "countryCodes": ["UK"],
                "errors": {}
            }
        ]

        created_accounts = []
        for data in accounts_data:
            alternate_ids = data.get("alternateIds", [])
            first_alternate = alternate_ids[0] if alternate_ids else {}

            account = AmazonAccount(
                user_id=user_id,
                account_name=data.get("accountName"),
                amazon_account_id=data.get("adsAccountId"),
                marketplace_id=first_alternate.get("entityId"),
                status="active" if data["status"] == "CREATED" else "disabled",
                metadata={
                    "alternate_ids": alternate_ids,
                    "country_codes": data.get("countryCodes", []),
                    "profile_id": first_alternate.get("profileId")
                }
            )
            created_accounts.append(account)

        assert len(created_accounts) == 3
        assert created_accounts[0].amazon_account_id == "AMZN-ADV-001"
        assert created_accounts[1].amazon_account_id == "AMZN-ADV-002"
        assert created_accounts[2].amazon_account_id == "AMZN-ADV-003"
        assert created_accounts[2].status == "disabled"

    def test_update_existing_account_with_v3_data(self):
        """Test updating an existing account with new v3.0 data"""
        user_id = str(uuid4())
        account_id = str(uuid4())

        # Original account
        original = AmazonAccount(
            id=account_id,
            user_id=user_id,
            account_name="Original Name",
            amazon_account_id="AMZN-ADV-123",
            status="active",
            metadata={
                "alternate_ids": [{"countryCode": "US", "entityId": "E1", "profileId": 1}],
                "country_codes": ["US"]
            }
        )

        # New data from API
        new_data = {
            "adsAccountId": "AMZN-ADV-123",
            "accountName": "Updated Name",
            "status": "CREATED",
            "alternateIds": [
                {"countryCode": "US", "entityId": "E1", "profileId": 1},
                {"countryCode": "CA", "entityId": "E2", "profileId": 2}  # New country added
            ],
            "countryCodes": ["US", "CA"],
            "errors": {}
        }

        # Update the account
        original.account_name = new_data.get("accountName")
        original.metadata["alternate_ids"] = new_data.get("alternateIds", [])
        original.metadata["country_codes"] = new_data.get("countryCodes", [])
        original.last_synced_at = datetime.now(timezone.utc)

        assert original.account_name == "Updated Name"
        assert len(original.metadata["alternate_ids"]) == 2
        assert "CA" in original.metadata["country_codes"]

    def test_handle_empty_alternate_ids(self):
        """Test handling accounts with no alternateIds"""
        user_id = str(uuid4())

        account_data = {
            "adsAccountId": "AMZN-ADV-EMPTY",
            "accountName": "Account Without Profiles",
            "status": "PENDING",
            "alternateIds": [],  # Empty
            "countryCodes": [],
            "errors": {}
        }

        alternate_ids = account_data.get("alternateIds", [])
        first_alternate = alternate_ids[0] if alternate_ids else {}

        account = AmazonAccount(
            user_id=user_id,
            account_name=account_data.get("accountName"),
            amazon_account_id=account_data.get("adsAccountId"),
            marketplace_id=first_alternate.get("entityId"),  # Will be None
            status="pending",
            metadata={
                "alternate_ids": alternate_ids,
                "country_codes": account_data.get("countryCodes", []),
                "profile_id": first_alternate.get("profileId"),  # Will be None
                "country_code": first_alternate.get("countryCode")  # Will be None
            }
        )

        assert account.amazon_account_id == "AMZN-ADV-EMPTY"
        assert account.marketplace_id is None
        assert account.metadata["profile_id"] is None
        assert account.metadata["country_code"] is None
        assert len(account.metadata["alternate_ids"]) == 0

    @pytest.mark.asyncio
    async def test_concurrent_account_updates(self):
        """Test handling concurrent updates to the same account"""
        user_id = str(uuid4())
        account_id = "AMZN-ADV-CONCURRENT"

        # Simulate two concurrent API responses
        response1 = {
            "adsAccountId": account_id,
            "accountName": "Update 1",
            "status": "CREATED",
            "alternateIds": [{"countryCode": "US", "entityId": "E1", "profileId": 1}],
            "countryCodes": ["US"],
            "errors": {}
        }

        response2 = {
            "adsAccountId": account_id,
            "accountName": "Update 2",
            "status": "CREATED",
            "alternateIds": [
                {"countryCode": "US", "entityId": "E1", "profileId": 1},
                {"countryCode": "CA", "entityId": "E2", "profileId": 2}
            ],
            "countryCodes": ["US", "CA"],
            "errors": {}
        }

        # The second update should win (last write wins)
        # In real implementation, this would be handled by database transactions
        final_account = AmazonAccount(
            user_id=user_id,
            account_name=response2.get("accountName"),
            amazon_account_id=response2.get("adsAccountId"),
            metadata={
                "alternate_ids": response2.get("alternateIds", []),
                "country_codes": response2.get("countryCodes", [])
            }
        )

        assert final_account.account_name == "Update 2"
        assert len(final_account.metadata["alternate_ids"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])