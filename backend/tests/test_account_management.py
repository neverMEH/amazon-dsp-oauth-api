"""
Unit tests for account management operations and API endpoints
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from fastapi import HTTPException, status
import json

from app.main import app
from app.schemas.amazon_account import (
    AmazonAccountResponse,
    AmazonAccountDetail,
    AccountHealthStatus,
    AccountDisconnectRequest,
    AccountReauthorizeRequest,
    UserPreferences,
    UserSettings
)


class TestAccountManagementEndpoints:
    """Test account management API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Test client fixture"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_auth_user(self):
        """Mock authenticated user"""
        return {
            "clerk_user_id": "user_test123",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User"
        }
    
    @pytest.fixture
    def mock_amazon_accounts(self):
        """Mock Amazon accounts data"""
        return [
            {
                "id": "acc_1",
                "user_id": "user_test123",
                "amazon_account_id": "amzn_123",
                "account_name": "Primary Account",
                "marketplace_id": "ATVPDKIKX0DER",
                "advertiser_id": "ADV123",
                "access_token": "encrypted_token_1",
                "refresh_token": "encrypted_refresh_1",
                "token_expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                "last_refreshed_at": datetime.now(timezone.utc).isoformat(),
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "id": "acc_2",
                "user_id": "user_test123",
                "amazon_account_id": "amzn_456",
                "account_name": "Secondary Account",
                "marketplace_id": "A1F83G8C2ARO7P",
                "advertiser_id": "ADV456",
                "access_token": "encrypted_token_2",
                "refresh_token": "encrypted_refresh_2",
                "token_expires_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
                "last_refreshed_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        ]
    
    def test_get_account_details_success(self, client, mock_auth_user, mock_amazon_accounts):
        """Test successfully retrieving connected Amazon account details"""
        with patch("app.middleware.clerk_auth.verify_token", return_value=mock_auth_user):
            with patch("app.services.account_service.AmazonAccountService.get_user_accounts", 
                      return_value=mock_amazon_accounts):
                response = client.get(
                    "/api/v1/accounts",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "accounts" in data
                assert len(data["accounts"]) == 2
                assert data["accounts"][0]["account_name"] == "Primary Account"
                assert data["accounts"][1]["account_name"] == "Secondary Account"
    
    def test_get_account_details_no_accounts(self, client, mock_auth_user):
        """Test retrieving account details when no accounts are connected"""
        with patch("app.middleware.clerk_auth.verify_token", return_value=mock_auth_user):
            with patch("app.services.account_service.AmazonAccountService.get_user_accounts", 
                      return_value=[]):
                response = client.get(
                    "/api/v1/accounts",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["accounts"] == []
    
    def test_get_account_details_unauthorized(self, client):
        """Test retrieving account details without authentication"""
        response = client.get("/api/v1/accounts")
        assert response.status_code == 401
    
    def test_get_single_account_detail(self, client, mock_auth_user, mock_amazon_accounts):
        """Test retrieving details for a single account"""
        with patch("app.middleware.clerk_auth.verify_token", return_value=mock_auth_user):
            with patch("app.services.account_service.AmazonAccountService.get_account_by_id", 
                      return_value=mock_amazon_accounts[0]):
                response = client.get(
                    "/api/v1/accounts/acc_1",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["id"] == "acc_1"
                assert data["account_name"] == "Primary Account"
    
    def test_disconnect_account_success(self, client, mock_auth_user):
        """Test successfully disconnecting an Amazon account"""
        with patch("app.middleware.clerk_auth.verify_token", return_value=mock_auth_user):
            with patch("app.services.account_service.AmazonAccountService.disconnect_account", 
                      return_value={"success": True, "message": "Account disconnected"}):
                response = client.delete(
                    "/api/v1/accounts/acc_1/disconnect",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "Account disconnected" in data["message"]
    
    def test_disconnect_account_not_found(self, client, mock_auth_user):
        """Test disconnecting a non-existent account"""
        with patch("app.middleware.clerk_auth.verify_token", return_value=mock_auth_user):
            with patch("app.services.account_service.AmazonAccountService.disconnect_account", 
                      side_effect=HTTPException(status_code=404, detail="Account not found")):
                response = client.delete(
                    "/api/v1/accounts/nonexistent",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 404
    
    def test_disconnect_account_cleanup(self, client, mock_auth_user):
        """Test account disconnection with proper cleanup"""
        with patch("app.middleware.clerk_auth.verify_token", return_value=mock_auth_user):
            with patch("app.services.account_service.AmazonAccountService.disconnect_account") as mock_disconnect:
                mock_disconnect.return_value = {"success": True, "tokens_revoked": True}
                
                response = client.delete(
                    "/api/v1/accounts/acc_1/disconnect",
                    headers={"Authorization": "Bearer test_token"},
                    json={"revoke_tokens": True}
                )
                
                assert response.status_code == 200
                mock_disconnect.assert_called_once()
    
    def test_get_account_health_status(self, client, mock_auth_user):
        """Test retrieving account health and token expiration status"""
        with patch("app.middleware.clerk_auth.verify_token", return_value=mock_auth_user):
            health_data = {
                "acc_1": {
                    "status": "healthy",
                    "token_expires_in": "23 hours",
                    "last_refresh": "1 hour ago",
                    "needs_reauth": False
                },
                "acc_2": {
                    "status": "expired",
                    "token_expires_in": "expired",
                    "last_refresh": "1 day ago",
                    "needs_reauth": True
                }
            }
            
            with patch("app.services.account_service.AmazonAccountService.get_accounts_health", 
                      return_value=health_data):
                response = client.get(
                    "/api/v1/accounts/health",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "health_status" in data
                assert data["health_status"]["acc_1"]["status"] == "healthy"
                assert data["health_status"]["acc_2"]["needs_reauth"] is True
    
    def test_reauthorize_account_success(self, client, mock_auth_user):
        """Test successful account re-authorization flow"""
        with patch("app.middleware.clerk_auth.verify_token", return_value=mock_auth_user):
            with patch("app.services.amazon_oauth_service.AmazonOAuthService.generate_reauth_url") as mock_reauth:
                mock_reauth.return_value = {
                    "auth_url": "https://www.amazon.com/ap/oa?client_id=test&state=reauth_state",
                    "state": "reauth_state"
                }
                
                response = client.post(
                    "/api/v1/accounts/acc_2/reauthorize",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "auth_url" in data
                assert "state" in data
    
    def test_reauthorize_active_token(self, client, mock_auth_user):
        """Test re-authorization attempt on account with active token"""
        with patch("app.middleware.clerk_auth.verify_token", return_value=mock_auth_user):
            with patch("app.services.account_service.AmazonAccountService.get_account_by_id") as mock_get:
                mock_account = Mock()
                mock_account.token_expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
                mock_get.return_value = mock_account
                
                response = client.post(
                    "/api/v1/accounts/acc_1/reauthorize",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 400
                data = response.json()
                assert "Token is still valid" in data["detail"]
    
    def test_get_user_settings(self, client, mock_auth_user):
        """Test retrieving user settings and preferences"""
        with patch("app.middleware.clerk_auth.verify_token", return_value=mock_auth_user):
            settings_data = {
                "user_id": "user_test123",
                "preferences": {
                    "notifications_enabled": True,
                    "auto_refresh_tokens": True,
                    "default_account_id": "acc_1",
                    "dashboard_layout": "grid",
                    "timezone": "America/New_York"
                },
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            with patch("app.services.user_service.UserService.get_user_settings", 
                      return_value=settings_data):
                response = client.get(
                    "/api/v1/settings",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["preferences"]["notifications_enabled"] is True
                assert data["preferences"]["default_account_id"] == "acc_1"
    
    def test_update_user_settings(self, client, mock_auth_user):
        """Test updating user settings and preferences"""
        with patch("app.middleware.clerk_auth.verify_token", return_value=mock_auth_user):
            update_data = {
                "preferences": {
                    "notifications_enabled": False,
                    "auto_refresh_tokens": True,
                    "default_account_id": "acc_2"
                }
            }
            
            with patch("app.services.user_service.UserService.update_user_settings", 
                      return_value={**update_data, "user_id": "user_test123"}):
                response = client.patch(
                    "/api/v1/settings",
                    headers={"Authorization": "Bearer test_token"},
                    json=update_data
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["preferences"]["notifications_enabled"] is False
                assert data["preferences"]["default_account_id"] == "acc_2"
    
    def test_batch_account_operations(self, client, mock_auth_user):
        """Test batch operations on multiple accounts"""
        with patch("app.middleware.clerk_auth.verify_token", return_value=mock_auth_user):
            batch_request = {
                "account_ids": ["acc_1", "acc_2"],
                "operation": "refresh_tokens"
            }
            
            with patch("app.services.account_service.AmazonAccountService.batch_refresh_tokens") as mock_batch:
                mock_batch.return_value = {
                    "success": 2,
                    "failed": 0,
                    "results": [
                        {"account_id": "acc_1", "status": "refreshed"},
                        {"account_id": "acc_2", "status": "refreshed"}
                    ]
                }
                
                response = client.post(
                    "/api/v1/accounts/batch",
                    headers={"Authorization": "Bearer test_token"},
                    json=batch_request
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] == 2
                assert data["failed"] == 0


class TestAccountHealthMonitoring:
    """Test account health monitoring functionality"""
    
    def test_calculate_token_expiration(self):
        """Test calculating token expiration time"""
        from app.services.account_service import AmazonAccountService
        service = AmazonAccountService()
        
        # Token expires in 1 hour
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        result = service._calculate_time_until_expiry(expires_at)
        assert "hour" in result or "59 minutes" in result
        
        # Token expired
        expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        result = service._calculate_time_until_expiry(expires_at)
        assert result == "expired"
        
        # Token expires in days
        expires_at = datetime.now(timezone.utc) + timedelta(days=2)
        result = service._calculate_time_until_expiry(expires_at)
        assert "2 days" in result or "1 day" in result
    
    def test_determine_health_status(self):
        """Test determining account health status"""
        from app.services.account_service import AmazonAccountService
        service = AmazonAccountService()
        
        # Healthy account
        account = Mock()
        account.token_expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        account.last_refreshed_at = datetime.now(timezone.utc)
        status = service._determine_health_status(account)
        assert status == "healthy"
        
        # Warning status (expires soon)
        account.token_expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
        status = service._determine_health_status(account)
        assert status == "warning"
        
        # Expired status
        account.token_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        status = service._determine_health_status(account)
        assert status == "expired"
        
        # Error status (no refresh for long time)
        account.token_expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        account.last_refreshed_at = datetime.now(timezone.utc) - timedelta(days=8)
        status = service._determine_health_status(account)
        assert status == "error"
    
    def test_monitor_all_accounts_health(self):
        """Test monitoring health of all user accounts"""
        from app.services.account_service import AmazonAccountService
        service = AmazonAccountService()
        
        accounts = [
            Mock(
                id="acc_1",
                token_expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
                last_refreshed_at=datetime.now(timezone.utc)
            ),
            Mock(
                id="acc_2",
                token_expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
                last_refreshed_at=datetime.now(timezone.utc) - timedelta(days=1)
            )
        ]
        
        with patch.object(service, 'get_user_accounts', return_value=accounts):
            health_report = service.get_accounts_health("user_123")
            
            assert "acc_1" in health_report
            assert "acc_2" in health_report
            assert health_report["acc_1"]["status"] == "healthy"
            assert health_report["acc_2"]["status"] == "expired"
            assert health_report["acc_2"]["needs_reauth"] is True


class TestAccountReauthorization:
    """Test account re-authorization flow"""
    
    def test_initiate_reauthorization(self):
        """Test initiating re-authorization for expired token"""
        from app.services.amazon_oauth_service import AmazonOAuthService
        service = AmazonOAuthService()
        
        account = Mock()
        account.id = "acc_123"
        account.amazon_account_id = "amzn_123"
        
        with patch.object(service, 'generate_authorization_url') as mock_gen:
            mock_gen.return_value = ("https://auth.url", "state_123")
            
            auth_url, state = service.initiate_reauthorization(account)
            
            assert auth_url == "https://auth.url"
            assert state == "state_123"
            mock_gen.assert_called_once()
    
    def test_complete_reauthorization(self):
        """Test completing re-authorization with new tokens"""
        from app.services.amazon_oauth_service import AmazonOAuthService
        service = AmazonOAuthService()
        
        with patch.object(service, 'exchange_code_for_token') as mock_exchange:
            mock_exchange.return_value = {
                "access_token": "new_access",
                "refresh_token": "new_refresh",
                "expires_in": 3600
            }
            
            with patch.object(service, 'update_account_tokens') as mock_update:
                result = service.complete_reauthorization("acc_123", "auth_code", "state_123")
                
                assert result["success"] is True
                mock_exchange.assert_called_once()
                mock_update.assert_called_once()
    
    def test_auto_reauthorization_check(self):
        """Test automatic re-authorization check for expiring tokens"""
        from app.services.account_service import AmazonAccountService
        service = AmazonAccountService()
        
        accounts = [
            Mock(
                id="acc_1",
                token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                auto_refresh_enabled=True
            ),
            Mock(
                id="acc_2",
                token_expires_at=datetime.now(timezone.utc) + timedelta(days=2),
                auto_refresh_enabled=True
            )
        ]
        
        with patch.object(service, 'get_all_accounts', return_value=accounts):
            with patch.object(service, 'refresh_token') as mock_refresh:
                service.check_and_refresh_expiring_tokens()
                
                # Should only refresh acc_1 (expires in 1 hour)
                assert mock_refresh.call_count == 1
                mock_refresh.assert_called_with("acc_1")


class TestUserPreferencesManagement:
    """Test user preferences and settings management"""
    
    def test_get_default_preferences(self):
        """Test getting default user preferences"""
        from app.services.user_service import UserService
        service = UserService()
        
        defaults = service.get_default_preferences()
        
        assert defaults["notifications_enabled"] is True
        assert defaults["auto_refresh_tokens"] is True
        assert defaults["dashboard_layout"] == "grid"
        assert defaults["timezone"] == "UTC"
    
    def test_validate_preferences(self):
        """Test validating user preferences"""
        from app.services.user_service import UserService
        service = UserService()
        
        # Valid preferences
        valid_prefs = {
            "notifications_enabled": False,
            "dashboard_layout": "list",
            "timezone": "America/Los_Angeles"
        }
        assert service.validate_preferences(valid_prefs) is True
        
        # Invalid layout
        invalid_prefs = {
            "dashboard_layout": "invalid_layout"
        }
        assert service.validate_preferences(invalid_prefs) is False
        
        # Invalid timezone
        invalid_prefs = {
            "timezone": "Invalid/Timezone"
        }
        assert service.validate_preferences(invalid_prefs) is False
    
    def test_merge_preferences(self):
        """Test merging user preferences with defaults"""
        from app.services.user_service import UserService
        service = UserService()
        
        user_prefs = {
            "notifications_enabled": False,
            "default_account_id": "acc_123"
        }
        
        merged = service.merge_with_defaults(user_prefs)
        
        assert merged["notifications_enabled"] is False  # User preference
        assert merged["default_account_id"] == "acc_123"  # User preference
        assert merged["auto_refresh_tokens"] is True  # Default
        assert merged["dashboard_layout"] == "grid"  # Default
    
    def test_update_preference_single_field(self):
        """Test updating a single preference field"""
        from app.services.user_service import UserService
        service = UserService()
        
        existing = {
            "notifications_enabled": True,
            "auto_refresh_tokens": True,
            "dashboard_layout": "grid"
        }
        
        update = {"notifications_enabled": False}
        
        with patch.object(service, 'get_user_settings', return_value={"preferences": existing}):
            with patch.object(service, 'save_user_settings') as mock_save:
                service.update_user_preference("user_123", "notifications_enabled", False)
                
                saved_prefs = mock_save.call_args[0][1]["preferences"]
                assert saved_prefs["notifications_enabled"] is False
                assert saved_prefs["auto_refresh_tokens"] is True  # Unchanged


class TestAccountListingAndFiltering:
    """Test account listing with filtering and pagination"""
    
    def test_list_accounts_with_pagination(self):
        """Test listing accounts with pagination"""
        from app.services.account_service import AmazonAccountService
        service = AmazonAccountService()
        
        # Create 10 mock accounts
        mock_accounts = [
            Mock(id=f"acc_{i}", account_name=f"Account {i}")
            for i in range(10)
        ]
        
        with patch.object(service, 'get_all_user_accounts', return_value=mock_accounts):
            # First page
            result = service.list_accounts("user_123", page=1, per_page=5)
            assert len(result["accounts"]) == 5
            assert result["total"] == 10
            assert result["page"] == 1
            assert result["has_next"] is True
            
            # Second page
            result = service.list_accounts("user_123", page=2, per_page=5)
            assert len(result["accounts"]) == 5
            assert result["page"] == 2
            assert result["has_next"] is False
    
    def test_filter_accounts_by_status(self):
        """Test filtering accounts by active status"""
        from app.services.account_service import AmazonAccountService
        service = AmazonAccountService()
        
        accounts = [
            Mock(id="acc_1", is_active=True),
            Mock(id="acc_2", is_active=False),
            Mock(id="acc_3", is_active=True)
        ]
        
        with patch.object(service, 'get_all_user_accounts', return_value=accounts):
            # Active only
            result = service.list_accounts("user_123", filter_active=True)
            assert len(result["accounts"]) == 2
            
            # Inactive only
            result = service.list_accounts("user_123", filter_active=False)
            assert len(result["accounts"]) == 1
    
    def test_sort_accounts(self):
        """Test sorting accounts by different fields"""
        from app.services.account_service import AmazonAccountService
        service = AmazonAccountService()
        
        accounts = [
            Mock(id="acc_1", account_name="Zebra", created_at=datetime(2024, 1, 1)),
            Mock(id="acc_2", account_name="Alpha", created_at=datetime(2024, 2, 1)),
            Mock(id="acc_3", account_name="Beta", created_at=datetime(2024, 1, 15))
        ]
        
        with patch.object(service, 'get_all_user_accounts', return_value=accounts):
            # Sort by name
            result = service.list_accounts("user_123", sort_by="name")
            assert result["accounts"][0].account_name == "Alpha"
            assert result["accounts"][2].account_name == "Zebra"
            
            # Sort by created date
            result = service.list_accounts("user_123", sort_by="created_at")
            assert result["accounts"][0].created_at == datetime(2024, 1, 1)
            assert result["accounts"][2].created_at == datetime(2024, 2, 1)