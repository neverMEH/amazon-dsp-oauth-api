import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone
import json

from app.main import app


@pytest.fixture
def test_client():
    """Test client fixture for FastAPI app"""
    return TestClient(app)


def get_error_message(response_data):
    """Extract error message from response regardless of format"""
    if "detail" in response_data:
        return response_data["detail"]
    elif "error" in response_data and "message" in response_data["error"]:
        return response_data["error"]["message"]
    else:
        return str(response_data)


@pytest.mark.asyncio
async def test_get_dsp_advertiser_seats_success(test_client: TestClient):
    """Test successful retrieval of DSP advertiser seats via API endpoint"""
    mock_user = {
        "user_id": "user123",
        "email": "test@example.com"
    }

    mock_account = {
        "id": "account123",
        "user_id": "user123",
        "amazon_account_id": "DSP123",
        "account_type": "dsp",
        "metadata": {}
    }

    mock_token = {
        "access_token": "valid_token",
        "expires_at": datetime.now(timezone.utc).isoformat()
    }

    mock_seats_response = {
        "advertiserSeats": [
            {
                "advertiserId": "DSP123",
                "currentSeats": [
                    {
                        "exchangeId": "1",
                        "exchangeName": "Google Ad Manager",
                        "dealCreationId": "DEAL123",
                        "spendTrackingId": "TRACK456"
                    }
                ]
            }
        ],
        "nextToken": None
    }

    with patch("app.middleware.clerk_auth.clerk_middleware.get_current_user", new_callable=AsyncMock) as mock_auth:
        mock_auth.return_value = mock_user

        with patch("app.api.v1.accounts.get_supabase_service_client") as mock_supabase:
            mock_client = MagicMock()
            mock_supabase.return_value = mock_client

            # Mock account lookup
            mock_client.table().select().eq().eq().eq().execute.return_value = MagicMock(
                data=[mock_account]
            )

            # Mock token lookup
            with patch("app.api.v1.accounts.get_user_token", new_callable=AsyncMock) as mock_get_token:
                mock_get_token.return_value = mock_token

                with patch("app.api.v1.accounts.refresh_token_if_needed", new_callable=AsyncMock) as mock_refresh:
                    mock_refresh.return_value = mock_token

                    with patch("app.services.dsp_amc_service.dsp_amc_service.list_advertiser_seats", new_callable=AsyncMock) as mock_list_seats:
                        mock_list_seats.return_value = mock_seats_response

                        response = test_client.get(
                            "/api/v1/accounts/dsp/DSP123/seats",
                            headers={"Authorization": "Bearer test_clerk_token"}
                        )

                        assert response.status_code == 200
                        data = response.json()
                        assert "advertiserSeats" in data
                        assert len(data["advertiserSeats"]) == 1
                        assert data["advertiserSeats"][0]["advertiserId"] == "DSP123"
                        assert "timestamp" in data
                        assert data["cached"] is False

                        # Verify service was called with correct parameters
                        mock_list_seats.assert_called_once_with(
                            access_token="valid_token",
                            advertiser_id="DSP123",
                            exchange_ids=None,
                            max_results=200,
                            next_token=None,
                            profile_id=None
                        )


@pytest.mark.asyncio
async def test_get_dsp_advertiser_seats_with_filters(test_client: TestClient):
    """Test retrieving DSP seats with exchange filters and pagination"""
    mock_user = {"user_id": "user123"}
    mock_account = {
        "id": "account123",
        "user_id": "user123",
        "amazon_account_id": "DSP456",
        "account_type": "dsp"
    }
    mock_token = {"access_token": "valid_token"}

    with patch("app.middleware.clerk_auth.clerk_middleware.get_current_user", new_callable=AsyncMock) as mock_auth:
        mock_auth.return_value = mock_user

        with patch("app.api.v1.accounts.get_supabase_service_client") as mock_supabase:
            mock_client = MagicMock()
            mock_supabase.return_value = mock_client
            mock_client.table().select().eq().eq().eq().execute.return_value = MagicMock(
                data=[mock_account]
            )

            with patch("app.api.v1.accounts.get_user_token", new_callable=AsyncMock) as mock_get_token:
                mock_get_token.return_value = mock_token

                with patch("app.api.v1.accounts.refresh_token_if_needed", new_callable=AsyncMock) as mock_refresh:
                    mock_refresh.return_value = mock_token

                    with patch("app.services.dsp_amc_service.dsp_amc_service.list_advertiser_seats", new_callable=AsyncMock) as mock_list_seats:
                        mock_list_seats.return_value = {"advertiserSeats": [], "nextToken": "token123"}

                        response = test_client.get(
                            "/api/v1/accounts/dsp/DSP456/seats",
                            params={
                                "exchange_ids": ["1", "2"],
                                "max_results": 50,
                                "next_token": "prev_token",
                                "profile_id": "12345"
                            },
                            headers={"Authorization": "Bearer test_clerk_token"}
                        )

                        assert response.status_code == 200

                        # Verify service was called with filters
                        mock_list_seats.assert_called_once_with(
                            access_token="valid_token",
                            advertiser_id="DSP456",
                            exchange_ids=["1", "2"],
                            max_results=50,
                            next_token="prev_token",
                            profile_id="12345"
                        )


@pytest.mark.asyncio
async def test_get_dsp_advertiser_seats_not_found(test_client: TestClient):
    """Test 404 response when DSP advertiser not found"""
    mock_user = {"user_id": "user123"}

    with patch("app.middleware.clerk_auth.clerk_middleware.get_current_user", new_callable=AsyncMock) as mock_auth:
        mock_auth.return_value = mock_user

        with patch("app.api.v1.accounts.get_supabase_service_client") as mock_supabase:
            mock_client = MagicMock()
            mock_supabase.return_value = mock_client

            # Mock empty account lookup
            mock_client.table().select().eq().eq().eq().execute.return_value = MagicMock(
                data=[]
            )

            response = test_client.get(
                "/api/v1/accounts/dsp/NONEXISTENT/seats",
                headers={"Authorization": "Bearer test_clerk_token"}
            )

            assert response.status_code == 404
            error_msg = get_error_message(response.json())
            assert "not found" in error_msg.lower()


@pytest.mark.asyncio
async def test_get_dsp_advertiser_seats_unauthorized(test_client: TestClient):
    """Test 401 response when user not authenticated"""
    mock_user = {"user_id": None}  # No user_id

    with patch("app.middleware.clerk_auth.clerk_middleware.get_current_user", new_callable=AsyncMock) as mock_auth:
        mock_auth.return_value = mock_user

        response = test_client.get(
            "/api/v1/accounts/dsp/DSP123/seats",
            headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code == 404
        error_msg = get_error_message(response.json())
        assert "User not found" in error_msg or "not found" in error_msg.lower()


@pytest.mark.asyncio
async def test_refresh_dsp_seats_success(test_client: TestClient):
    """Test force refresh of DSP seats data"""
    mock_user = {"user_id": "user123"}
    mock_account = {
        "id": "account123",
        "user_id": "user123",
        "amazon_account_id": "DSP123",
        "account_type": "dsp"
    }
    mock_token = {"access_token": "valid_token"}

    mock_seats_response = {
        "advertiserSeats": [
            {
                "advertiserId": "DSP123",
                "currentSeats": [
                    {"exchangeId": "1", "exchangeName": "GAM"}
                ]
            }
        ]
    }

    with patch("app.middleware.clerk_auth.clerk_middleware.get_current_user", new_callable=AsyncMock) as mock_auth:
        mock_auth.return_value = mock_user

        with patch("app.api.v1.accounts.get_supabase_service_client") as mock_supabase:
            mock_client = MagicMock()
            mock_supabase.return_value = mock_client

            # Mock table method to handle different queries properly
            def mock_table(table_name):
                if table_name == "user_accounts":
                    table_mock = MagicMock()
                    table_mock.select().eq().eq().eq().execute.return_value = MagicMock(data=[mock_account])
                    return table_mock
                elif table_name == "dsp_seats_sync_log":
                    table_mock = MagicMock()
                    # Mock recent sync check (return empty to allow refresh)
                    table_mock.select().eq().eq().gte().execute.return_value = MagicMock(data=[])
                    # Mock sync log creation
                    table_mock.insert().execute.return_value = MagicMock(data=[{"id": "sync123"}])
                    # Mock update operations
                    table_mock.update().eq().execute.return_value = MagicMock(data=[])
                    return table_mock
                else:
                    return MagicMock()

            mock_client.table.side_effect = mock_table

            with patch("app.api.v1.accounts.get_user_token", new_callable=AsyncMock) as mock_get_token:
                mock_get_token.return_value = mock_token

                with patch("app.api.v1.accounts.refresh_token_if_needed", new_callable=AsyncMock) as mock_refresh:
                    mock_refresh.return_value = mock_token

                    with patch("app.services.dsp_amc_service.dsp_amc_service.list_advertiser_seats", new_callable=AsyncMock) as mock_list_seats:
                        mock_list_seats.return_value = mock_seats_response

                        response = test_client.post(
                            "/api/v1/accounts/dsp/DSP123/seats/refresh",
                            json={"force": True, "include_sync_log": False},
                            headers={"Authorization": "Bearer test_clerk_token"}
                        )

                        assert response.status_code == 200
                        data = response.json()
                        assert data["success"] is True
                        assert data["seats_updated"] == 1
                        assert "last_sync" in data
                        assert "sync_log_id" in data


@pytest.mark.asyncio
async def test_get_sync_history_success(test_client: TestClient):
    """Test retrieving sync history for DSP seats"""
    mock_user = {"user_id": "user123"}
    mock_account = {
        "id": "account123",
        "user_id": "user123",
        "amazon_account_id": "DSP123",
        "account_type": "dsp"
    }

    mock_sync_logs = [
        {
            "id": "log1",
            "sync_status": "success",
            "seats_retrieved": 5,
            "exchanges_count": 2,
            "error_message": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "log2",
            "sync_status": "failed",
            "seats_retrieved": 0,
            "exchanges_count": 0,
            "error_message": "Rate limit exceeded",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]

    with patch("app.middleware.clerk_auth.clerk_middleware.get_current_user", new_callable=AsyncMock) as mock_auth:
        mock_auth.return_value = mock_user

        with patch("app.api.v1.accounts.get_supabase_service_client") as mock_supabase:
            mock_client = MagicMock()
            mock_supabase.return_value = mock_client

            # Mock table method to return different mock objects for different tables
            def mock_table(table_name):
                if table_name == "user_accounts":
                    table_mock = MagicMock()
                    table_mock.select().eq().eq().eq().execute.return_value = MagicMock(data=[mock_account])
                    return table_mock
                elif table_name == "dsp_seats_sync_log":
                    table_mock = MagicMock()

                    # Create separate query chains for count and paginated queries
                    def mock_select(*args, **kwargs):
                        query_chain = MagicMock()
                        query_chain.eq.return_value = query_chain  # user_account_id
                        query_chain.eq.return_value = query_chain  # advertiser_id
                        query_chain.execute.return_value = MagicMock(data=mock_sync_logs)  # Count query

                        # Chain for paginated query
                        order_chain = MagicMock()
                        order_chain.range.return_value = order_chain
                        order_chain.execute.return_value = MagicMock(data=mock_sync_logs)
                        query_chain.order.return_value = order_chain

                        return query_chain

                    table_mock.select.side_effect = mock_select
                    return table_mock
                else:
                    return MagicMock()

            mock_client.table.side_effect = mock_table

            response = test_client.get(
                "/api/v1/accounts/dsp/DSP123/seats/sync-history",
                params={"limit": 10, "offset": 0},
                headers={"Authorization": "Bearer test_clerk_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert "sync_history" in data
            assert len(data["sync_history"]) == 2
            assert data["sync_history"][0]["sync_status"] == "success"
            assert data["sync_history"][1]["sync_status"] == "failed"
            assert data["total_count"] == 2


@pytest.mark.asyncio
async def test_get_dsp_advertiser_seats_rate_limit(test_client: TestClient):
    """Test rate limit handling for DSP seats endpoint"""
    mock_user = {"user_id": "user123"}
    mock_account = {
        "id": "account123",
        "user_id": "user123",
        "amazon_account_id": "DSP123",
        "account_type": "dsp"
    }
    mock_token = {"access_token": "valid_token"}

    with patch("app.middleware.clerk_auth.clerk_middleware.get_current_user", new_callable=AsyncMock) as mock_auth:
        mock_auth.return_value = mock_user

        with patch("app.api.v1.accounts.get_supabase_service_client") as mock_supabase:
            mock_client = MagicMock()
            mock_supabase.return_value = mock_client
            mock_client.table().select().eq().eq().eq().execute.return_value = MagicMock(
                data=[mock_account]
            )

            with patch("app.api.v1.accounts.get_user_token", new_callable=AsyncMock) as mock_get_token:
                mock_get_token.return_value = mock_token

                with patch("app.api.v1.accounts.refresh_token_if_needed", new_callable=AsyncMock) as mock_refresh:
                    mock_refresh.return_value = mock_token

                    with patch("app.services.dsp_amc_service.dsp_amc_service.list_advertiser_seats", new_callable=AsyncMock) as mock_list_seats:
                        from app.core.exceptions import RateLimitError
                        mock_list_seats.side_effect = RateLimitError(30)

                        response = test_client.get(
                            "/api/v1/accounts/dsp/DSP123/seats",
                            headers={"Authorization": "Bearer test_clerk_token"}
                        )

                        assert response.status_code == 429
                        error_msg = get_error_message(response.json())
                        assert "Rate limit exceeded" in error_msg or "rate limit" in error_msg.lower()
                        assert response.headers["Retry-After"] == "30"


@pytest.mark.asyncio
async def test_get_dsp_advertiser_seats_token_refresh_failure(test_client: TestClient):
    """Test handling of token refresh failure"""
    mock_user = {"user_id": "user123"}
    mock_account = {
        "id": "account123",
        "user_id": "user123",
        "amazon_account_id": "DSP123",
        "account_type": "dsp"
    }
    mock_token = {"access_token": "expired_token"}

    with patch("app.middleware.clerk_auth.clerk_middleware.get_current_user", new_callable=AsyncMock) as mock_auth:
        mock_auth.return_value = mock_user

        with patch("app.api.v1.accounts.get_supabase_service_client") as mock_supabase:
            mock_client = MagicMock()
            mock_supabase.return_value = mock_client
            mock_client.table().select().eq().eq().eq().execute.return_value = MagicMock(
                data=[mock_account]
            )

            with patch("app.api.v1.accounts.get_user_token", new_callable=AsyncMock) as mock_get_token:
                mock_get_token.return_value = mock_token

                with patch("app.api.v1.accounts.refresh_token_if_needed", new_callable=AsyncMock) as mock_refresh:
                    mock_refresh.return_value = mock_token

                    with patch("app.services.dsp_amc_service.dsp_amc_service.list_advertiser_seats", new_callable=AsyncMock) as mock_list_seats:
                        from app.core.exceptions import TokenRefreshError
                        mock_list_seats.side_effect = TokenRefreshError("Token refresh failed")

                        response = test_client.get(
                            "/api/v1/accounts/dsp/DSP123/seats",
                            headers={"Authorization": "Bearer test_clerk_token"}
                        )

                        assert response.status_code == 401
                        error_msg = get_error_message(response.json())
                        assert "Token refresh failed" in error_msg or "refresh" in error_msg.lower()