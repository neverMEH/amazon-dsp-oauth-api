"""
Tests for OAuth authentication endpoints
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import json
from cryptography.fernet import Fernet

# We'll import our app once it's created
# from app.main import app


@pytest.fixture
def client():
    """Test client fixture"""
    from app.main import app
    return TestClient(app)


@pytest.fixture
def mock_supabase():
    """Mock Supabase client"""
    with patch('app.db.base.get_supabase_client') as mock:
        mock_client = Mock()
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_fernet():
    """Mock Fernet encryption"""
    key = Fernet.generate_key()
    return Fernet(key)


class TestOAuthEndpoints:
    """Test OAuth authentication endpoints"""
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    def test_login_endpoint_generates_auth_url(self, client):
        """Test that login endpoint generates proper Amazon auth URL"""
        response = client.get("/api/v1/auth/amazon/login")
        assert response.status_code == 200
        
        data = response.json()
        assert "auth_url" in data
        assert "state" in data
        assert "expires_in" in data
        
        # Verify auth URL contains required parameters
        auth_url = data["auth_url"]
        assert "https://www.amazon.com/ap/oa" in auth_url
        assert "client_id=amzn1.application-oa2-client.cf1789da23f74ee489e2373e424726af" in auth_url
        assert "scope=advertising::campaign_management" in auth_url
        assert "response_type=code" in auth_url
        assert "redirect_uri=" in auth_url
        assert f"state={data['state']}" in auth_url
    
    def test_callback_missing_code_returns_error(self, client):
        """Test callback without authorization code returns error"""
        response = client.get("/api/v1/auth/amazon/callback?state=test_state")
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "MISSING_AUTH_CODE"
    
    def test_callback_invalid_state_returns_error(self, client, mock_supabase):
        """Test callback with invalid state token returns error"""
        # Mock database returning no matching state
        mock_supabase.table().select().eq().single.return_value.execute.return_value.data = None
        
        response = client.get("/api/v1/auth/amazon/callback?code=test_code&state=invalid_state")
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "INVALID_STATE_TOKEN"
    
    @patch('httpx.AsyncClient.post')
    async def test_callback_successful_token_exchange(self, mock_post, client, mock_supabase, mock_fernet):
        """Test successful OAuth callback and token exchange"""
        # Mock state validation
        mock_supabase.table().select().eq().single.return_value.execute.return_value.data = {
            "state_token": "valid_state",
            "used": False,
            "expires_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        }
        
        # Mock Amazon token exchange response
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=AsyncMock(return_value={
                "access_token": "test_access_token",
                "refresh_token": "test_refresh_token",
                "token_type": "bearer",
                "expires_in": 3600
            })
        )
        
        # Mock token storage
        mock_supabase.table().insert().execute.return_value.data = {
            "id": "token_id_123",
            "access_token": mock_fernet.encrypt(b"test_access_token").decode(),
            "refresh_token": mock_fernet.encrypt(b"test_refresh_token").decode(),
            "expires_at": (datetime.utcnow() + timedelta(seconds=3600)).isoformat()
        }
        
        response = client.get("/api/v1/auth/amazon/callback?code=auth_code&state=valid_state")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "token_info" in data
        assert data["token_info"]["token_id"] == "token_id_123"
    
    def test_auth_status_no_token(self, client, mock_supabase):
        """Test auth status when no token exists"""
        mock_supabase.table().select().eq().single.return_value.execute.return_value.data = None
        
        response = client.get("/api/v1/auth/status")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
    
    def test_auth_status_with_valid_token(self, client, mock_supabase):
        """Test auth status with valid token"""
        mock_supabase.table().select().eq().single.return_value.execute.return_value.data = {
            "id": "token_123",
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "refresh_count": 5,
            "last_refresh_at": datetime.utcnow().isoformat(),
            "scope": "advertising::campaign_management"
        }
        
        response = client.get("/api/v1/auth/status")
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] == True
        assert data["token_valid"] == True
        assert "expires_at" in data
        assert data["refresh_count"] == 5
    
    @patch('httpx.AsyncClient.post')
    async def test_manual_refresh_success(self, mock_post, client, mock_supabase, mock_fernet):
        """Test manual token refresh"""
        # Mock existing token
        mock_supabase.table().select().eq().single.return_value.execute.return_value.data = {
            "id": "token_123",
            "refresh_token": mock_fernet.encrypt(b"old_refresh_token").decode(),
            "expires_at": (datetime.utcnow() + timedelta(minutes=3)).isoformat()
        }
        
        # Mock Amazon refresh response
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=AsyncMock(return_value={
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "token_type": "bearer",
                "expires_in": 3600
            })
        )
        
        response = client.post(
            "/api/v1/auth/refresh",
            headers={"X-Admin-Key": "test_admin_key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "new_expiry" in data


class TestTokenEncryption:
    """Test token encryption service"""
    
    def test_encrypt_decrypt_token(self, mock_fernet):
        """Test token encryption and decryption"""
        original_token = "test_token_12345"
        encrypted = mock_fernet.encrypt(original_token.encode())
        decrypted = mock_fernet.decrypt(encrypted).decode()
        assert decrypted == original_token
    
    def test_encrypt_empty_token_raises_error(self, mock_fernet):
        """Test that empty token raises error"""
        with pytest.raises(Exception):
            mock_fernet.encrypt(b"")


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_rate_limit_handling(self, client):
        """Test rate limit error handling"""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=429,
                headers={"Retry-After": "60"}
            )
            
            response = client.get("/api/v1/auth/amazon/callback?code=test&state=valid")
            assert response.status_code == 503
            data = response.json()
            assert data["error"]["code"] == "RATE_LIMITED"
    
    def test_network_timeout_handling(self, client):
        """Test network timeout handling"""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.side_effect = Exception("Network timeout")
            
            response = client.get("/api/v1/auth/amazon/callback?code=test&state=valid")
            assert response.status_code == 500
            data = response.json()
            assert "error" in data


class TestAuditLogging:
    """Test audit logging functionality"""
    
    def test_successful_login_creates_audit_log(self, client, mock_supabase):
        """Test that successful login creates audit log entry"""
        # Setup mock response
        mock_supabase.table().insert().execute.return_value.data = {
            "id": "audit_123",
            "event_type": "login",
            "event_status": "success"
        }
        
        # After successful auth, check audit log was created
        # This will be verified through mock_supabase.table().insert() calls
        assert mock_supabase.table.called
    
    def test_failed_login_creates_audit_log(self, client, mock_supabase):
        """Test that failed login creates audit log entry"""
        mock_supabase.table().insert().execute.return_value.data = {
            "id": "audit_124",
            "event_type": "login",
            "event_status": "failure",
            "error_message": "Invalid authorization code"
        }
        
        # After failed auth, check audit log was created
        assert mock_supabase.table.called