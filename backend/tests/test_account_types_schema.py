"""
Tests for account types database schema changes.
Tests the new columns: account_type, profile_id, entity_id, last_managed_at
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.amazon_account import AmazonAccount


class TestAccountTypesSchema:
    """Test suite for account types schema changes."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database for testing model validation."""
        return Mock()

    def test_account_type_column_accepts_valid_values(self, mock_db):
        """Test that account_type column accepts valid values (advertising, dsp, amc)."""
        # Test advertising type
        account_advertising = AmazonAccount(
            user_id="test-user-1",
            account_name="Test Sponsored Ads Account",
            amazon_account_id="ENTITY123",
            account_type="advertising",
            marketplace_id="ATVPDKIKX0DER"
        )
        assert account_advertising.account_type == "advertising"

        # Test DSP type
        account_dsp = AmazonAccount(
            user_id="test-user-1",
            account_name="Test DSP Account",
            amazon_account_id="DSP456",
            account_type="dsp",
            marketplace_id="ATVPDKIKX0DER"
        )
        assert account_dsp.account_type == "dsp"

        # Test AMC type
        account_amc = AmazonAccount(
            user_id="test-user-1",
            account_name="Test AMC Instance",
            amazon_account_id="AMC789",
            account_type="amc",
            marketplace_id="ATVPDKIKX0DER"
        )
        assert account_amc.account_type == "amc"

    def test_entity_id_column_stores_identifiers(self, mock_db):
        """Test that entity_id column stores Amazon entity identifiers."""
        account = AmazonAccount(
            user_id="test-user-2",
            account_name="Test Account",
            amazon_account_id="ACC123",
            entity_id="ENTITY_ABC_123",
            account_type="advertising",
            marketplace_id="ATVPDKIKX0DER"
        )
        assert account.entity_id == "ENTITY_ABC_123"

    def test_profile_id_column_stores_numeric_identifiers(self, mock_db):
        """Test that profile_id column stores numeric profile identifiers."""
        account = AmazonAccount(
            user_id="test-user-3",
            account_name="Test Account",
            amazon_account_id="ACC456",
            profile_id="123456789",
            account_type="advertising",
            marketplace_id="ATVPDKIKX0DER"
        )
        assert account.profile_id == "123456789"

    def test_last_managed_at_timestamp(self, mock_db):
        """Test that last_managed_at column stores management timestamps."""
        now = datetime.now(timezone.utc)
        account = AmazonAccount(
            user_id="test-user-4",
            account_name="Test Account",
            amazon_account_id="ACC789",
            account_type="advertising",
            marketplace_id="ATVPDKIKX0DER",
            last_managed_at=now
        )
        assert account.last_managed_at == now

    def test_multiple_account_types_per_user(self, mock_db):
        """Test that a user can have multiple accounts of different types."""
        user_id = "test-user-6"

        # Create accounts of each type
        account_advertising = AmazonAccount(
            user_id=user_id,
            account_name="Sponsored Ads Account",
            amazon_account_id="SP001",
            account_type="advertising",
            marketplace_id="ATVPDKIKX0DER"
        )
        account_dsp = AmazonAccount(
            user_id=user_id,
            account_name="DSP Account",
            amazon_account_id="DSP001",
            account_type="dsp",
            marketplace_id="ATVPDKIKX0DER"
        )
        account_amc = AmazonAccount(
            user_id=user_id,
            account_name="AMC Instance",
            amazon_account_id="AMC001",
            account_type="amc",
            marketplace_id="ATVPDKIKX0DER"
        )

        assert account_advertising.account_type == "advertising"
        assert account_dsp.account_type == "dsp"
        assert account_amc.account_type == "amc"
        assert account_advertising.user_id == user_id
        assert account_dsp.user_id == user_id
        assert account_amc.user_id == user_id

    def test_marketplaces_array_field(self, mock_db):
        """Test that marketplaces can be stored as JSON array in metadata."""
        account = AmazonAccount(
            user_id="test-user-7",
            account_name="Multi-marketplace Account",
            amazon_account_id="MKT001",
            account_type="advertising",
            marketplace_id="ATVPDKIKX0DER",
            metadata={
                "marketplaces": ["US", "CA", "MX"],
                "alternateIds": [
                    {"countryCode": "US", "profileId": 123456789},
                    {"countryCode": "CA", "profileId": 987654321}
                ]
            }
        )
        assert account.metadata["marketplaces"] == ["US", "CA", "MX"]
        assert len(account.metadata["alternateIds"]) == 2


class TestAccountTypeDetection:
    """Test account type detection from Amazon API responses."""

    def test_detect_sponsored_ads_account(self):
        """Test detection of Sponsored Ads account from API response."""
        api_response = {
            "adsAccountId": "ENTITY123",
            "accountName": "Test Advertiser",
            "alternateIds": [
                {"countryCode": "US", "profileId": 123456789}
            ],
            "countryCodes": ["US"],
            "status": "CREATED"
        }

        # Would be implemented in the service layer
        account_type = self._detect_account_type(api_response)
        assert account_type == "advertising"

    def test_detect_dsp_account(self):
        """Test detection of DSP account from API response."""
        api_response = {
            "advertiserId": "DSP123",
            "advertiserName": "Test DSP Advertiser",
            "advertiserType": "BRAND",
            "entityId": "DSP_ENTITY_456"
        }

        account_type = self._detect_account_type(api_response)
        assert account_type == "dsp"

    def test_detect_amc_instance(self):
        """Test detection of AMC instance from API response."""
        api_response = {
            "instanceId": "AMC789",
            "instanceName": "Test AMC Instance",
            "dataSetId": "dataset_xyz",
            "advertisers": [
                {"advertiserId": "ADV123", "type": "SPONSORED_ADS"},
                {"advertiserId": "DSP456", "type": "DSP"}
            ]
        }

        account_type = self._detect_account_type(api_response)
        assert account_type == "amc"

    def _detect_account_type(self, api_response):
        """Helper method to detect account type from API response."""
        if "adsAccountId" in api_response:
            return "advertising"
        elif "advertiserId" in api_response and "advertiserType" in api_response:
            return "dsp"
        elif "instanceId" in api_response and "dataSetId" in api_response:
            return "amc"
        return None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
