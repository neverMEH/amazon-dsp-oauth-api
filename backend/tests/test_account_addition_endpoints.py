"""
Tests for account-type-specific addition endpoints
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
import json


class TestSponsoredAdsAddEndpoint:
    """Test POST /api/v1/accounts/sponsored-ads/add endpoint"""

    def setup_method(self):
        """Set up test fixtures"""
        from app.main import app
        self.client = TestClient(app)

    @patch('app.services.token_service.TokenService.get_active_token')
    @patch('app.services.account_addition_service.AccountService.fetch_and_store_sponsored_ads')
    def test_add_sponsored_ads_with_existing_tokens(self, mock_fetch, mock_get_token):
        """Test adding Sponsored Ads accounts when user has valid tokens"""
        # Mock valid token
        mock_get_token.return_value = {
            "access_token": "valid_token",
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "scope": "advertising::campaign_management advertising::account_management advertising::dsp_campaigns"
        }

        # Mock successful account fetch
        mock_fetch.return_value = {
            "accounts": [
                {
                    "id": "uuid-1",
                    "account_name": "Test Account 1",
                    "amazon_account_id": "ENTITY123",
                    "account_type": "advertising",
                    "status": "active"
                },
                {
                    "id": "uuid-2",
                    "account_name": "Test Account 2",
                    "amazon_account_id": "ENTITY456",
                    "account_type": "advertising",
                    "status": "active"
                }
            ],
            "accounts_added": 2
        }

        # Make request with auth header
        response = self.client.post(
            "/api/v1/accounts/sponsored-ads/add",
            headers={"Authorization": "Bearer test-clerk-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["requires_auth"] == False
        assert data["accounts_added"] == 2
        assert len(data["accounts"]) == 2

    @patch('app.services.token_service.TokenService.get_active_token')
    def test_add_sponsored_ads_no_tokens(self, mock_get_token):
        """Test adding Sponsored Ads accounts when user has no tokens"""
        # Mock no token
        mock_get_token.return_value = None

        response = self.client.post(
            "/api/v1/accounts/sponsored-ads/add",
            headers={"Authorization": "Bearer test-clerk-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["requires_auth"] == True
        assert "auth_url" in data
        assert "state" in data

    @patch('app.services.token_service.TokenService.get_active_token')
    def test_add_sponsored_ads_expired_token(self, mock_get_token):
        """Test adding Sponsored Ads accounts when token is expired"""
        # Mock expired token
        mock_get_token.return_value = {
            "access_token": "expired_token",
            "expires_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            "scope": "advertising::campaign_management advertising::account_management"
        }

        response = self.client.post(
            "/api/v1/accounts/sponsored-ads/add",
            headers={"Authorization": "Bearer test-clerk-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["requires_auth"] == True
        assert "auth_url" in data


class TestDSPAddEndpoint:
    """Test POST /api/v1/accounts/dsp/add endpoint"""

    def setup_method(self):
        """Set up test fixtures"""
        from app.main import app
        self.client = TestClient(app)

    @patch('app.services.token_service.TokenService.get_active_token')
    @patch('app.services.account_addition_service.AccountService.fetch_and_store_dsp_advertisers')
    def test_add_dsp_with_existing_tokens(self, mock_fetch, mock_get_token):
        """Test adding DSP advertisers when user has valid tokens with DSP scope"""
        # Mock valid token with DSP scope
        mock_get_token.return_value = {
            "access_token": "valid_token",
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "scope": "advertising::campaign_management advertising::account_management advertising::dsp_campaigns"
        }

        # Mock successful advertiser fetch
        mock_fetch.return_value = {
            "advertisers": [
                {
                    "id": "uuid-1",
                    "account_name": "DSP Advertiser 1",
                    "amazon_account_id": "AD123",
                    "account_type": "dsp",
                    "status": "active"
                }
            ],
            "advertisers_added": 1
        }

        response = self.client.post(
            "/api/v1/accounts/dsp/add",
            headers={"Authorization": "Bearer test-clerk-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["requires_auth"] == False
        assert data["advertisers_added"] == 1
        assert len(data["advertisers"]) == 1

    @patch('app.services.token_service.TokenService.get_active_token')
    def test_add_dsp_missing_scope(self, mock_get_token):
        """Test adding DSP advertisers when token lacks DSP scope"""
        # Mock token without DSP scope
        mock_get_token.return_value = {
            "access_token": "valid_token",
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "scope": "advertising::campaign_management advertising::account_management"
        }

        response = self.client.post(
            "/api/v1/accounts/dsp/add",
            headers={"Authorization": "Bearer test-clerk-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["requires_auth"] == True
        assert data.get("reason") == "missing_dsp_scope"
        assert "auth_url" in data

    def test_add_dsp_no_auth(self):
        """Test adding DSP advertisers without authentication"""
        response = self.client.post("/api/v1/accounts/dsp/add")

        assert response.status_code == 401


class TestAccountDeletion:
    """Test DELETE /api/v1/accounts/{account_id} endpoint"""

    def setup_method(self):
        """Set up test fixtures"""
        from app.main import app
        self.client = TestClient(app)

    @patch('app.services.account_addition_service.AccountService.delete_account')
    def test_delete_account_success(self, mock_delete):
        """Test successful account deletion"""
        mock_delete.return_value = {"success": True}

        response = self.client.delete(
            "/api/v1/accounts/test-account-id",
            headers={"Authorization": "Bearer test-clerk-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "Account successfully deleted" in data["message"]

    @patch('app.services.account_addition_service.AccountService.delete_account')
    def test_delete_account_not_found(self, mock_delete):
        """Test deleting non-existent account"""
        mock_delete.side_effect = ValueError("Account not found")

        response = self.client.delete(
            "/api/v1/accounts/non-existent-id",
            headers={"Authorization": "Bearer test-clerk-token"}
        )

        assert response.status_code == 404

    def test_delete_account_no_auth(self):
        """Test account deletion without authentication"""
        response = self.client.delete("/api/v1/accounts/test-id")
        assert response.status_code == 401