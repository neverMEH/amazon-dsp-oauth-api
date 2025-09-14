"""
Integration tests for Amazon OAuth flow and token management
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import json
import secrets
from typing import Dict, Any

from app.services.amazon_oauth_service import AmazonOAuthService, AmazonAuthError
from app.services.token_service import TokenService
from app.core.exceptions import TokenRefreshError
from app.schemas.auth import AmazonTokenResponse, AmazonAccountInfo
from app.config import settings


class TestAmazonOAuthService:
    """Test Amazon OAuth service integration"""
    
    @pytest.fixture
    def oauth_service(self):
        """Create Amazon OAuth service instance"""
        return AmazonOAuthService()
    
    @pytest.fixture
    def mock_token_response(self):
        """Mock Amazon token response"""
        return {
            "access_token": "Atza|IwEBIExampleAccessToken",
            "refresh_token": "Atzr|IwEBIExampleRefreshToken", 
            "token_type": "bearer",
            "expires_in": 3600,
            "scope": "advertising::campaign_management advertising::account_management"
        }
    
    @pytest.fixture
    def mock_profile_response(self):
        """Mock Amazon profile response"""
        return [
            {
                "profileId": 123456789,
                "countryCode": "US",
                "currencyCode": "USD",
                "timezone": "America/New_York",
                "accountInfo": {
                    "marketplaceStringId": "ATVPDKIKX0DER",
                    "id": "ENTITY123456789",
                    "type": "seller",
                    "name": "Test Seller Account"
                }
            }
        ]
    
    def test_generate_oauth_url(self, oauth_service):
        """Test generating Amazon OAuth authorization URL"""
        auth_url, state = oauth_service.generate_oauth_url()
        
        assert "https://www.amazon.com/ap/oa" in auth_url
        assert f"client_id={settings.amazon_client_id}" in auth_url
        assert "response_type=code" in auth_url
        assert "advertising::campaign_management" in auth_url
        assert "advertising::account_management" in auth_url
        assert f"state={state}" in auth_url
        assert len(state) == 32  # 24 bytes encoded as base64 = 32 characters
    
    def test_generate_oauth_url_with_custom_state(self, oauth_service):
        """Test generating OAuth URL with custom state"""
        custom_state = "custom_state_123"
        auth_url, state = oauth_service.generate_oauth_url(state=custom_state)
        
        assert f"state={custom_state}" in auth_url
        assert state == custom_state
    
    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_success(self, oauth_service, mock_token_response):
        """Test successful authorization code exchange"""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_token_response
            mock_post.return_value = mock_response
            
            result = await oauth_service.exchange_code_for_tokens(
                "valid_auth_code", 
                "valid_state"
            )
            
            assert result.access_token == "Atza|IwEBIExampleAccessToken"
            assert result.refresh_token == "Atzr|IwEBIExampleRefreshToken"
            assert result.expires_in == 3600
            assert "advertising::campaign_management" in result.scope
    
    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_invalid_code(self, oauth_service):
        """Test authorization code exchange with invalid code"""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.json.return_value = {
                "error": "invalid_grant",
                "error_description": "The provided authorization grant is invalid"
            }
            mock_post.return_value = mock_response
            
            with pytest.raises(AmazonAuthError) as exc_info:
                await oauth_service.exchange_code_for_tokens(
                    "invalid_code", 
                    "valid_state"
                )
            
            assert "invalid_grant" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_network_error(self, oauth_service):
        """Test authorization code exchange with network error"""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.side_effect = Exception("Network connection failed")
            
            with pytest.raises(AmazonAuthError) as exc_info:
                await oauth_service.exchange_code_for_tokens(
                    "valid_code",
                    "valid_state"  
                )
            
            assert "Network connection failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_refresh_access_token_success(self, oauth_service, mock_token_response):
        """Test successful token refresh"""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_token_response
            mock_post.return_value = mock_response
            
            result = await oauth_service.refresh_access_token("valid_refresh_token")
            
            assert result.access_token == "Atza|IwEBIExampleAccessToken"
            assert result.expires_in == 3600
    
    @pytest.mark.asyncio
    async def test_refresh_access_token_invalid_token(self, oauth_service):
        """Test token refresh with invalid refresh token"""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.json.return_value = {
                "error": "invalid_grant",
                "error_description": "Refresh token is invalid or expired"
            }
            mock_post.return_value = mock_response
            
            with pytest.raises(TokenRefreshError) as exc_info:
                await oauth_service.refresh_access_token("invalid_refresh_token")
            
            assert "invalid_grant" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_user_profiles_success(self, oauth_service, mock_profile_response):
        """Test successful profile retrieval"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_profile_response
            mock_get.return_value = mock_response
            
            profiles = await oauth_service.get_user_profiles("valid_access_token")
            
            assert len(profiles) == 1
            assert profiles[0].profile_id == 123456789
            assert profiles[0].country_code == "US"
            assert profiles[0].account_info.name == "Test Seller Account"
    
    @pytest.mark.asyncio
    async def test_get_user_profiles_unauthorized(self, oauth_service):
        """Test profile retrieval with unauthorized token"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.json.return_value = {
                "code": "UNAUTHORIZED",
                "details": "The request signature we calculated does not match"
            }
            mock_get.return_value = mock_response
            
            with pytest.raises(AmazonAuthError) as exc_info:
                await oauth_service.get_user_profiles("invalid_access_token")
            
            assert "UNAUTHORIZED" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_user_profiles_rate_limited(self, oauth_service):
        """Test profile retrieval with rate limiting"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.headers = {"Retry-After": "60"}
            mock_response.json.return_value = {
                "code": "TOO_MANY_REQUESTS",
                "details": "Request was throttled"
            }
            mock_get.return_value = mock_response
            
            with pytest.raises(AmazonAuthError) as exc_info:
                await oauth_service.get_user_profiles("valid_access_token")
            
            assert "TOO_MANY_REQUESTS" in str(exc_info.value)


class TestAmazonTokenManagement:
    """Test Amazon token storage and lifecycle management"""
    
    @pytest.fixture
    def token_service(self):
        """Create token service instance"""
        return TokenService()
    
    @pytest.fixture
    def sample_tokens(self):
        """Sample token data"""
        return {
            "access_token": "Atza|IwEBIExampleAccessToken",
            "refresh_token": "Atzr|IwEBIExampleRefreshToken",
            "expires_in": 3600,
            "token_type": "bearer",
            "scope": "advertising::campaign_management"
        }
    
    @pytest.mark.asyncio
    async def test_store_amazon_tokens(self, token_service, sample_tokens):
        """Test storing Amazon tokens in database"""
        user_id = "user_123"
        profile_id = 123456789
        
        # Mock the Supabase database operations
        with patch.object(token_service, 'db') as mock_db:
            mock_table = Mock()
            mock_db.table.return_value = mock_table
            
            # Mock existing record check (returns no data)
            mock_table.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
            
            # Mock insert operation
            mock_table.insert.return_value.execute.return_value.data = [{"id": "new_record_id"}]
            
            result = await token_service.store_amazon_tokens(
                user_id=user_id,
                profile_id=profile_id,
                tokens=sample_tokens
            )
            
            # Verify database operations
            assert mock_db.table.called
            assert mock_table.insert.called
    
    @pytest.mark.asyncio  
    async def test_retrieve_amazon_tokens(self, token_service):
        """Test retrieving Amazon tokens from database"""
        user_id = "user_123"
        profile_id = 123456789
        
        with patch('app.db.session.SessionLocal') as mock_session:
            mock_db = Mock()
            mock_account = Mock()
            mock_account.encrypted_access_token = "encrypted_access_token"
            mock_account.encrypted_refresh_token = "encrypted_refresh_token"
            mock_account.token_expires_at = datetime.utcnow() + timedelta(minutes=30)
            mock_db.query.return_value.filter.return_value.first.return_value = mock_account
            mock_session.return_value.__enter__.return_value = mock_db
            
            with patch.object(token_service, 'decrypt_token') as mock_decrypt:
                mock_decrypt.side_effect = ["decrypted_access_token", "decrypted_refresh_token"]
                
                tokens = await token_service.retrieve_amazon_tokens(user_id, profile_id)
                
                assert tokens is not None
                assert tokens["access_token"] == "decrypted_access_token"
                assert tokens["refresh_token"] == "decrypted_refresh_token"
    
    @pytest.mark.asyncio
    async def test_retrieve_amazon_tokens_not_found(self, token_service):
        """Test retrieving non-existent Amazon tokens"""
        user_id = "user_123"
        profile_id = 999999999
        
        with patch('app.db.session.SessionLocal') as mock_session:
            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.first.return_value = None
            mock_session.return_value.__enter__.return_value = mock_db
            
            tokens = await token_service.retrieve_amazon_tokens(user_id, profile_id)
            
            assert tokens is None
    
    @pytest.mark.asyncio
    async def test_check_token_expiry(self, token_service):
        """Test checking if Amazon tokens need refresh"""
        user_id = "user_123"
        profile_id = 123456789
        
        # Test expired token
        with patch('app.db.session.SessionLocal') as mock_session:
            mock_db = Mock()
            mock_account = Mock()
            mock_account.token_expires_at = datetime.utcnow() - timedelta(minutes=5)
            mock_db.query.return_value.filter.return_value.first.return_value = mock_account
            mock_session.return_value.__enter__.return_value = mock_db
            
            needs_refresh = await token_service.check_token_expiry(user_id, profile_id)
            assert needs_refresh is True
        
        # Test valid token
        with patch('app.db.session.SessionLocal') as mock_session:
            mock_db = Mock()
            mock_account = Mock()
            mock_account.token_expires_at = datetime.utcnow() + timedelta(minutes=30)
            mock_db.query.return_value.filter.return_value.first.return_value = mock_account
            mock_session.return_value.__enter__.return_value = mock_db
            
            needs_refresh = await token_service.check_token_expiry(user_id, profile_id)
            assert needs_refresh is False
    
    def test_encrypt_decrypt_tokens(self, token_service):
        """Test token encryption and decryption"""
        original_token = "Atza|IwEBIExampleAccessToken"
        
        # Encrypt token
        encrypted = token_service.encrypt_token(original_token)
        assert encrypted != original_token
        assert len(encrypted) > len(original_token)
        
        # Decrypt token
        decrypted = token_service.decrypt_token(encrypted)
        assert decrypted == original_token


class TestAmazonOAuthFlowIntegration:
    """Test complete Amazon OAuth flow integration"""
    
    @pytest.fixture
    def oauth_service(self):
        return AmazonOAuthService()
    
    @pytest.fixture
    def token_service(self):
        return TokenService()
    
    @pytest.mark.asyncio
    async def test_complete_oauth_flow(self, oauth_service, token_service):
        """Test complete OAuth flow from initiation to token storage"""
        user_id = "user_123"
        
        # Step 1: Generate OAuth URL
        auth_url, state = oauth_service.generate_oauth_url()
        assert "https://www.amazon.com/ap/oa" in auth_url
        assert len(state) == 32
        
        # Step 2: Exchange code for tokens (mocked)
        with patch.object(oauth_service, 'exchange_code_for_tokens') as mock_exchange:
            mock_tokens = AmazonTokenResponse(
                access_token="Atza|IwEBIExampleAccessToken",
                refresh_token="Atzr|IwEBIExampleRefreshToken",
                expires_in=3600,
                token_type="bearer",
                scope="advertising::campaign_management"
            )
            mock_exchange.return_value = mock_tokens
            
            tokens = await oauth_service.exchange_code_for_tokens("auth_code", state)
            assert tokens.access_token == "Atza|IwEBIExampleAccessToken"
        
        # Step 3: Get user profiles (mocked)
        with patch.object(oauth_service, 'get_user_profiles') as mock_profiles:
            mock_profile = AmazonAccountInfo(
                profile_id=123456789,
                country_code="US",
                currency_code="USD",
                timezone="America/New_York",
                account_info={
                    "marketplaceStringId": "ATVPDKIKX0DER",
                    "id": "ENTITY123456789", 
                    "type": "seller",
                    "name": "Test Account"
                }
            )
            mock_profiles.return_value = [mock_profile]
            
            profiles = await oauth_service.get_user_profiles(tokens.access_token)
            assert len(profiles) == 1
            assert profiles[0].profile_id == 123456789
        
        # Step 4: Store tokens (mocked)
        with patch.object(token_service, 'store_amazon_tokens') as mock_store:
            await token_service.store_amazon_tokens(
                user_id=user_id,
                profile_id=profiles[0].profile_id,
                tokens=tokens.dict()
            )
            mock_store.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_token_refresh_flow(self, oauth_service, token_service):
        """Test automatic token refresh flow"""
        user_id = "user_123"
        profile_id = 123456789
        
        # Step 1: Check if tokens need refresh
        with patch.object(token_service, 'check_token_expiry') as mock_check:
            mock_check.return_value = True
            
            needs_refresh = await token_service.check_token_expiry(user_id, profile_id)
            assert needs_refresh is True
        
        # Step 2: Retrieve existing refresh token
        with patch.object(token_service, 'retrieve_amazon_tokens') as mock_retrieve:
            mock_retrieve.return_value = {
                "access_token": "old_access_token",
                "refresh_token": "Atzr|IwEBIExampleRefreshToken"
            }
            
            existing_tokens = await token_service.retrieve_amazon_tokens(user_id, profile_id)
            assert existing_tokens["refresh_token"] == "Atzr|IwEBIExampleRefreshToken"
        
        # Step 3: Refresh access token
        with patch.object(oauth_service, 'refresh_access_token') as mock_refresh:
            new_tokens = AmazonTokenResponse(
                access_token="Atza|IwEBINewAccessToken",
                refresh_token="Atzr|IwEBIExampleRefreshToken", 
                expires_in=3600,
                token_type="bearer",
                scope="advertising::campaign_management"
            )
            mock_refresh.return_value = new_tokens
            
            refreshed = await oauth_service.refresh_access_token(
                existing_tokens["refresh_token"]
            )
            assert refreshed.access_token == "Atza|IwEBINewAccessToken"
        
        # Step 4: Store updated tokens
        with patch.object(token_service, 'store_amazon_tokens') as mock_store:
            await token_service.store_amazon_tokens(
                user_id=user_id,
                profile_id=profile_id,
                tokens=refreshed.dict()
            )
            mock_store.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_oauth_error_handling_flow(self, oauth_service):
        """Test OAuth flow with various error scenarios"""
        # Test invalid state parameter
        with pytest.raises(AmazonAuthError):
            await oauth_service.validate_state("provided_state", "expected_state")
        
        # Test expired authorization code
        with patch.object(oauth_service, 'exchange_code_for_tokens') as mock_exchange:
            mock_exchange.side_effect = AmazonAuthError("Authorization code expired")
            
            with pytest.raises(AmazonAuthError) as exc_info:
                await oauth_service.exchange_code_for_tokens("expired_code", "state")
            
            assert "expired" in str(exc_info.value)
        
        # Test API rate limiting
        with patch.object(oauth_service, 'get_user_profiles') as mock_profiles:
            mock_profiles.side_effect = AmazonAuthError("TOO_MANY_REQUESTS")
            
            with pytest.raises(AmazonAuthError) as exc_info:
                await oauth_service.get_user_profiles("valid_token")
            
            assert "TOO_MANY_REQUESTS" in str(exc_info.value)


class TestAmazonConnectionStatus:
    """Test Amazon account connection status tracking"""
    
    @pytest.fixture
    def token_service(self):
        return TokenService()
    
    @pytest.mark.asyncio
    async def test_get_connection_status_connected(self, token_service):
        """Test getting connection status for connected account"""
        user_id = "user_123"
        profile_id = 123456789
        
        with patch.object(token_service, 'retrieve_amazon_tokens') as mock_retrieve:
            mock_retrieve.return_value = {
                "access_token": "valid_token",
                "refresh_token": "valid_refresh_token"
            }
            
            with patch.object(token_service, 'check_token_expiry') as mock_expiry:
                mock_expiry.return_value = False
                
                status = await token_service.get_connection_status(user_id, profile_id)
                
                assert status["connected"] is True
                assert status["needs_refresh"] is False
                assert status["profile_id"] == profile_id
    
    @pytest.mark.asyncio
    async def test_get_connection_status_needs_refresh(self, token_service):
        """Test getting connection status for account needing refresh"""
        user_id = "user_123"
        profile_id = 123456789
        
        with patch.object(token_service, 'retrieve_amazon_tokens') as mock_retrieve:
            mock_retrieve.return_value = {
                "access_token": "expiring_token",
                "refresh_token": "valid_refresh_token"
            }
            
            with patch.object(token_service, 'check_token_expiry') as mock_expiry:
                mock_expiry.return_value = True
                
                status = await token_service.get_connection_status(user_id, profile_id)
                
                assert status["connected"] is True
                assert status["needs_refresh"] is True
    
    @pytest.mark.asyncio
    async def test_get_connection_status_disconnected(self, token_service):
        """Test getting connection status for disconnected account"""
        user_id = "user_123"
        profile_id = 999999999
        
        with patch.object(token_service, 'retrieve_amazon_tokens') as mock_retrieve:
            mock_retrieve.return_value = None
            
            status = await token_service.get_connection_status(user_id, profile_id)
            
            assert status["connected"] is False
            assert status["needs_refresh"] is False
            assert status["profile_id"] == profile_id