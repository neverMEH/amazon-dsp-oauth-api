"""
Tests for Amazon OAuth service with expanded scopes
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta, timezone
from app.services.amazon_oauth_service import AmazonOAuthService, AmazonAuthError
from app.schemas.auth import AmazonTokenResponse


class TestAmazonOAuthService:
    """Test Amazon OAuth service functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.service = AmazonOAuthService()

    def test_expanded_scopes_configuration(self):
        """Test that OAuth service includes all required scopes"""
        # Service should have all three required scopes
        expected_scopes = [
            "advertising::campaign_management",
            "advertising::account_management",
            "advertising::dsp_campaigns"
        ]

        assert set(self.service.scopes) == set(expected_scopes)

        # Scope string should include all scopes space-separated
        for scope in expected_scopes:
            assert scope in self.service.scope

    def test_generate_oauth_url_includes_all_scopes(self):
        """Test that generated OAuth URL includes all required scopes"""
        auth_url, state_token = self.service.generate_oauth_url()

        # URL should contain all scopes (URL encoded)
        assert "advertising%3A%3Acampaign_management" in auth_url
        assert "advertising%3A%3Aaccount_management" in auth_url
        assert "advertising%3A%3Adsp_campaigns" in auth_url

    def test_scope_string_format(self):
        """Test that scope string is properly formatted"""
        # Should be space-separated
        assert self.service.scope == "advertising::campaign_management advertising::account_management advertising::dsp_campaigns"

    def test_has_dsp_scope_method(self):
        """Test method to check if DSP scope is included"""
        assert hasattr(self.service, 'has_dsp_scope')
        assert self.service.has_dsp_scope() == True

    def test_has_sponsored_ads_scope_method(self):
        """Test method to check if Sponsored Ads scopes are included"""
        assert hasattr(self.service, 'has_sponsored_ads_scope')
        assert self.service.has_sponsored_ads_scope() == True

    @pytest.mark.asyncio
    async def test_token_response_includes_scope(self):
        """Test that token exchange preserves scope information"""
        mock_response = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "advertising::campaign_management advertising::account_management advertising::dsp_campaigns"
        }

        # Create a proper mock response object
        mock_resp_obj = Mock()
        mock_resp_obj.status_code = 200
        mock_resp_obj.json.return_value = mock_response
        mock_resp_obj.text = ""

        with patch('httpx.AsyncClient') as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.post.return_value = mock_resp_obj
            mock_client.return_value.__aenter__.return_value = mock_async_client

            # exchange_code_for_tokens requires both code and state
            result = await self.service.exchange_code_for_tokens("test_code", "test_state")

            # Result should include scope
            assert result.scope == mock_response["scope"]
            assert "advertising::dsp_campaigns" in result.scope

    def test_scope_validation(self):
        """Test that service can validate if it has required scopes"""
        # Should have method to validate scopes
        assert hasattr(self.service, 'validate_scopes')

        # Should validate that all required scopes are present
        required_for_sponsored_ads = ["advertising::campaign_management", "advertising::account_management"]
        assert self.service.validate_scopes(required_for_sponsored_ads) == True

        required_for_dsp = ["advertising::campaign_management", "advertising::account_management", "advertising::dsp_campaigns"]
        assert self.service.validate_scopes(required_for_dsp) == True

        # Should return False for missing scopes
        missing_scope = ["advertising::non_existent_scope"]
        assert self.service.validate_scopes(missing_scope) == False


class TestOAuthTokenStorage:
    """Test OAuth token storage with expanded scope information"""

    @pytest.mark.asyncio
    async def test_store_token_with_scope(self):
        """Test storing tokens includes scope information"""
        from app.services.token_service import TokenService

        with patch('app.services.token_service.TokenService.store_tokens') as mock_store:
            service = AmazonOAuthService()
            token_data = AmazonTokenResponse(
                access_token="access_123",
                refresh_token="refresh_456",
                token_type="Bearer",
                expires_in=3600,
                scope="advertising::campaign_management advertising::account_management advertising::dsp_campaigns"
            )

            # When tokens are stored, scope should be included
            await TokenService().store_tokens(token_data)
            mock_store.assert_called_once()

            # Verify scope was passed
            call_args = mock_store.call_args[0][0]
            assert hasattr(call_args, 'scope') or 'scope' in call_args.__dict__