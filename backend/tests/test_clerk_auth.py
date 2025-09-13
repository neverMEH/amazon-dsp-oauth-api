"""
Test Clerk authentication integration
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import json
import jwt
from typing import Dict, Any

from app.services.clerk_service import ClerkService, ClerkWebhookHandler
from app.middleware.clerk_auth import ClerkAuthMiddleware
from app.schemas.user import UserCreate
from app.config import settings


class TestClerkService:
    """Test Clerk service integration"""
    
    @pytest.fixture
    def clerk_service(self):
        """Create Clerk service instance"""
        return ClerkService()
    
    @pytest.fixture
    def mock_clerk_user(self):
        """Mock Clerk user data"""
        return {
            "id": "user_2abc123def456",
            "email_addresses": [
                {
                    "id": "email_123",
                    "email_address": "test@example.com",
                    "verification": {"status": "verified"}
                }
            ],
            "first_name": "John",
            "last_name": "Doe",
            "profile_image_url": "https://img.clerk.com/avatar.jpg",
            "created_at": 1610000000000,
            "updated_at": 1610000000000
        }
    
    @pytest.mark.asyncio
    async def test_verify_session_token_valid(self, clerk_service):
        """Test verifying a valid Clerk session token"""
        # Create a mock JWT token
        payload = {
            "sub": "user_2abc123def456",
            "email": "test@example.com",
            "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp(),
            "iat": datetime.utcnow().timestamp(),
            "iss": "https://clerk.example.com"
        }
        
        with patch.object(clerk_service, 'verify_jwt') as mock_verify:
            mock_verify.return_value = payload
            
            result = await clerk_service.verify_session_token("valid_token")
            
            assert result is not None
            assert result["sub"] == "user_2abc123def456"
            assert result["email"] == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_verify_session_token_expired(self, clerk_service):
        """Test verifying an expired Clerk session token"""
        # Create an expired token
        payload = {
            "sub": "user_2abc123def456",
            "email": "test@example.com",
            "exp": (datetime.utcnow() - timedelta(hours=1)).timestamp(),
            "iat": (datetime.utcnow() - timedelta(hours=2)).timestamp()
        }
        
        with patch.object(clerk_service, 'verify_jwt') as mock_verify:
            mock_verify.side_effect = jwt.ExpiredSignatureError("Token expired")
            
            result = await clerk_service.verify_session_token("expired_token")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_user_from_clerk(self, clerk_service, mock_clerk_user):
        """Test fetching user data from Clerk API"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_clerk_user
            mock_get.return_value = mock_response
            
            user = await clerk_service.get_user("user_2abc123def456")
            
            assert user is not None
            assert user.clerk_user_id == "user_2abc123def456"
            assert user.email == "test@example.com"
            assert user.first_name == "John"
            assert user.last_name == "Doe"
    
    @pytest.mark.asyncio
    async def test_sync_user_with_database(self, clerk_service, mock_clerk_user):
        """Test syncing Clerk user with local database"""
        with patch('app.services.user_service.UserService.get_or_create_user') as mock_create:
            mock_create.return_value = AsyncMock()
            
            with patch.object(clerk_service, 'get_user') as mock_get_user:
                mock_get_user.return_value = UserCreate(
                    clerk_user_id="user_2abc123def456",
                    email="test@example.com",
                    first_name="John",
                    last_name="Doe"
                )
                
                result = await clerk_service.sync_user_with_database("user_2abc123def456")
                
                assert result is True
                mock_create.assert_called_once()


class TestClerkWebhookHandler:
    """Test Clerk webhook handling"""
    
    @pytest.fixture
    def webhook_handler(self):
        """Create webhook handler instance"""
        return ClerkWebhookHandler()
    
    @pytest.fixture
    def webhook_headers(self):
        """Mock webhook headers"""
        return {
            "svix-id": "msg_123",
            "svix-timestamp": str(int(datetime.utcnow().timestamp())),
            "svix-signature": "v1,g0hM9SsE+OTPJTGt/tmIKtSyZlE3uFJELVlNIOLJ1OE="
        }
    
    def test_verify_webhook_signature_valid(self, webhook_handler, webhook_headers):
        """Test verifying a valid webhook signature"""
        payload = json.dumps({"type": "user.created", "data": {}})
        
        with patch.object(webhook_handler, 'verify_signature') as mock_verify:
            mock_verify.return_value = True
            
            result = webhook_handler.verify_webhook(payload, webhook_headers)
            
            assert result is True
    
    def test_verify_webhook_signature_invalid(self, webhook_handler, webhook_headers):
        """Test verifying an invalid webhook signature"""
        payload = json.dumps({"type": "user.created", "data": {}})
        webhook_headers["svix-signature"] = "invalid_signature"
        
        with patch.object(webhook_handler, 'verify_signature') as mock_verify:
            mock_verify.return_value = False
            
            result = webhook_handler.verify_webhook(payload, webhook_headers)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_handle_user_created_event(self, webhook_handler):
        """Test handling user.created webhook event"""
        event_data = {
            "type": "user.created",
            "data": {
                "id": "user_new123",
                "email_addresses": [
                    {"email_address": "new@example.com", "verification": {"status": "verified"}}
                ],
                "first_name": "Jane",
                "last_name": "Smith"
            }
        }
        
        with patch('app.services.user_service.UserService.create_user') as mock_create:
            mock_create.return_value = AsyncMock()
            
            result = await webhook_handler.handle_event(event_data)
            
            assert result is True
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_user_updated_event(self, webhook_handler):
        """Test handling user.updated webhook event"""
        event_data = {
            "type": "user.updated",
            "data": {
                "id": "user_existing123",
                "email_addresses": [
                    {"email_address": "updated@example.com", "verification": {"status": "verified"}}
                ],
                "first_name": "Updated",
                "last_name": "User"
            }
        }
        
        with patch('app.services.user_service.UserService.update_user') as mock_update:
            mock_update.return_value = AsyncMock()
            
            result = await webhook_handler.handle_event(event_data)
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_handle_user_deleted_event(self, webhook_handler):
        """Test handling user.deleted webhook event"""
        event_data = {
            "type": "user.deleted",
            "data": {
                "id": "user_deleted123",
                "deleted": True
            }
        }
        
        with patch('app.services.user_service.UserService.delete_user') as mock_delete:
            mock_delete.return_value = AsyncMock()
            
            result = await webhook_handler.handle_event(event_data)
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_handle_session_created_event(self, webhook_handler):
        """Test handling session.created webhook event"""
        event_data = {
            "type": "session.created",
            "data": {
                "user_id": "user_session123",
                "status": "active",
                "created_at": datetime.utcnow().timestamp()
            }
        }
        
        with patch('app.services.user_service.UserService.update_last_login') as mock_login:
            mock_login.return_value = AsyncMock()
            
            result = await webhook_handler.handle_event(event_data)
            
            assert result is True


class TestClerkAuthMiddleware:
    """Test Clerk authentication middleware"""
    
    @pytest.fixture
    def middleware(self):
        """Create middleware instance"""
        return ClerkAuthMiddleware()
    
    @pytest.fixture
    def mock_request(self):
        """Create mock request"""
        request = Mock()
        request.headers = {}
        request.cookies = {}
        return request
    
    @pytest.mark.asyncio
    async def test_authenticate_request_with_valid_token(self, middleware, mock_request):
        """Test authenticating request with valid token"""
        mock_request.headers["Authorization"] = "Bearer valid_token"
        
        with patch.object(ClerkService, 'verify_session_token') as mock_verify:
            mock_verify.return_value = {
                "sub": "user_123",
                "email": "test@example.com"
            }
            
            user = await middleware.authenticate_request(mock_request)
            
            assert user is not None
            assert user["sub"] == "user_123"
    
    @pytest.mark.asyncio
    async def test_authenticate_request_with_invalid_token(self, middleware, mock_request):
        """Test authenticating request with invalid token"""
        mock_request.headers["Authorization"] = "Bearer invalid_token"
        
        with patch.object(ClerkService, 'verify_session_token') as mock_verify:
            mock_verify.return_value = None
            
            user = await middleware.authenticate_request(mock_request)
            
            assert user is None
    
    @pytest.mark.asyncio
    async def test_authenticate_request_with_cookie(self, middleware, mock_request):
        """Test authenticating request with session cookie"""
        mock_request.cookies["__session"] = "cookie_token"
        
        with patch.object(ClerkService, 'verify_session_token') as mock_verify:
            mock_verify.return_value = {
                "sub": "user_cookie",
                "email": "cookie@example.com"
            }
            
            user = await middleware.authenticate_request(mock_request)
            
            assert user is not None
            assert user["sub"] == "user_cookie"
    
    @pytest.mark.asyncio
    async def test_authenticate_request_no_credentials(self, middleware, mock_request):
        """Test authenticating request with no credentials"""
        user = await middleware.authenticate_request(mock_request)
        
        assert user is None
    
    def test_extract_token_from_header(self, middleware):
        """Test extracting token from Authorization header"""
        # Test Bearer token
        token = middleware.extract_token_from_header("Bearer abc123")
        assert token == "abc123"
        
        # Test without Bearer prefix
        token = middleware.extract_token_from_header("abc123")
        assert token == "abc123"
        
        # Test empty header
        token = middleware.extract_token_from_header("")
        assert token is None
    
    @pytest.mark.asyncio
    async def test_require_auth_decorator(self, middleware):
        """Test require_auth decorator"""
        from app.middleware.clerk_auth import require_auth
        
        @require_auth
        async def protected_endpoint(current_user: Dict[str, Any]):
            return {"user": current_user}
        
        # Test with authenticated user
        with patch.object(ClerkAuthMiddleware, 'authenticate_request') as mock_auth:
            mock_auth.return_value = {"sub": "user_123", "email": "test@example.com"}
            
            request = Mock()
            result = await protected_endpoint(request)
            
            assert result["user"]["sub"] == "user_123"
        
        # Test without authenticated user
        with patch.object(ClerkAuthMiddleware, 'authenticate_request') as mock_auth:
            mock_auth.return_value = None
            
            request = Mock()
            with pytest.raises(Exception) as exc_info:
                await protected_endpoint(request)
            
            assert "Unauthorized" in str(exc_info.value)