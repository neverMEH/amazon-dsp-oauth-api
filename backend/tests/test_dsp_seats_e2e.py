"""
End-to-End Test Scenarios for DSP Advertiser Seats Feature

This module tests the complete workflow from authentication through
seats retrieval to display functionality, including error scenarios.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone
import json
import time

from app.main import app


@pytest.fixture
def test_client():
    """Test client fixture for FastAPI app"""
    return TestClient(app)


class TestDSPSeatsE2EWorkflow:
    """Complete end-to-end test scenarios for DSP seats feature"""

    @pytest.fixture
    def mock_auth_user(self):
        """Mock authenticated user"""
        return {
            "user_id": "test_user_123",
            "email": "test@example.com",
            "clerk_user_id": "user_clerk_456"
        }

    @pytest.fixture
    def mock_dsp_account(self):
        """Mock DSP account"""
        return {
            "id": "acc_123",
            "user_id": "test_user_123",
            "amazon_account_id": "DSP_ADV_789",
            "account_type": "dsp",
            "status": "active",
            "account_name": "Test DSP Account",
            "metadata": {
                "seats_last_sync": datetime.now(timezone.utc).isoformat(),
                "seats_metadata": {
                    "total_seats": 5,
                    "exchanges": ["1", "2", "3"]
                }
            }
        }

    @pytest.fixture
    def mock_valid_token(self):
        """Mock valid OAuth token"""
        return {
            "access_token": "valid_access_token_123",
            "token_type": "Bearer",
            "expires_at": (datetime.now(timezone.utc).timestamp() + 3600),
            "scope": "advertising::dsp_campaigns"
        }

    @pytest.fixture
    def mock_seats_response(self):
        """Mock Amazon DSP seats API response"""
        return {
            "advertiserSeats": [
                {
                    "advertiserId": "DSP_ADV_789",
                    "currentSeats": [
                        {
                            "exchangeId": "1",
                            "exchangeName": "Google Ad Manager",
                            "dealCreationId": "DEAL_001",
                            "spendTrackingId": "SPEND_001"
                        },
                        {
                            "exchangeId": "2",
                            "exchangeName": "Microsoft Advertising Exchange",
                            "dealCreationId": "DEAL_002",
                            "spendTrackingId": "SPEND_002"
                        },
                        {
                            "exchangeId": "3",
                            "exchangeName": "The Trade Desk",
                            "dealCreationId": "DEAL_003",
                            "spendTrackingId": "SPEND_003"
                        }
                    ]
                }
            ],
            "nextToken": None
        }

    @pytest.mark.asyncio
    async def test_complete_dsp_seats_workflow_success(
        self,
        test_client: TestClient,
        mock_auth_user,
        mock_dsp_account,
        mock_valid_token,
        mock_seats_response
    ):
        """
        E2E Test Scenario 1: Complete successful workflow
        Tests: Authentication → Account lookup → Token validation → Seats retrieval → Display
        """
        with patch("app.api.v1.accounts.RequireAuth") as mock_auth:
            mock_auth.return_value = lambda: mock_auth_user

            with patch("app.api.v1.accounts.get_supabase_service_client") as mock_supabase:
                mock_client = MagicMock()
                mock_supabase.return_value = mock_client

                # Mock account lookup success
                mock_client.table().select().eq().eq().eq().execute.return_value = MagicMock(
                    data=[mock_dsp_account]
                )

                with patch("app.api.v1.accounts.get_user_token", new_callable=AsyncMock) as mock_get_token:
                    mock_get_token.return_value = mock_valid_token

                    with patch("app.api.v1.accounts.refresh_token_if_needed", new_callable=AsyncMock) as mock_refresh:
                        mock_refresh.return_value = mock_valid_token

                        with patch("app.services.dsp_amc_service.dsp_amc_service.list_advertiser_seats", new_callable=AsyncMock) as mock_list_seats:
                            mock_list_seats.return_value = mock_seats_response

                            # Execute the complete workflow
                            response = test_client.get(
                                "/api/v1/accounts/dsp/DSP_ADV_789/seats",
                                headers={"Authorization": "Bearer test_clerk_token"}
                            )

                            # Verify successful response
                            assert response.status_code == 200
                            data = response.json()

                            # Verify data structure
                            assert "advertiserSeats" in data
                            assert "timestamp" in data
                            assert "cached" in data

                            # Verify seats data
                            seats = data["advertiserSeats"][0]["currentSeats"]
                            assert len(seats) == 3

                            # Verify all exchanges present
                            exchange_names = [seat["exchangeName"] for seat in seats]
                            assert "Google Ad Manager" in exchange_names
                            assert "Microsoft Advertising Exchange" in exchange_names
                            assert "The Trade Desk" in exchange_names

                            # Verify all required fields present
                            for seat in seats:
                                assert "exchangeId" in seat
                                assert "exchangeName" in seat
                                assert "dealCreationId" in seat
                                assert "spendTrackingId" in seat

                            # Verify service call parameters
                            mock_list_seats.assert_called_once_with(
                                access_token="valid_access_token_123",
                                advertiser_id="DSP_ADV_789",
                                exchange_ids=None,
                                max_results=200,
                                next_token=None,
                                profile_id=None
                            )

    @pytest.mark.asyncio
    async def test_authentication_failure_workflow(
        self,
        test_client: TestClient
    ):
        """
        E2E Test Scenario 2: Authentication failure workflow
        Tests: Invalid auth → Error response
        """
        with patch("app.api.v1.accounts.RequireAuth") as mock_auth:
            # Mock authentication failure
            mock_auth.return_value = lambda: {"user_id": None}

            response = test_client.get(
                "/api/v1/accounts/dsp/DSP_ADV_789/seats",
                headers={"Authorization": "Bearer invalid_token"}
            )

            # Verify authentication error
            assert response.status_code == 404
            assert "User not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_account_not_found_workflow(
        self,
        test_client: TestClient,
        mock_auth_user
    ):
        """
        E2E Test Scenario 3: Account not found workflow
        Tests: Valid auth → Account lookup failure → Error response
        """
        with patch("app.api.v1.accounts.RequireAuth") as mock_auth:
            mock_auth.return_value = lambda: mock_auth_user

            with patch("app.api.v1.accounts.get_supabase_service_client") as mock_supabase:
                mock_client = MagicMock()
                mock_supabase.return_value = mock_client

                # Mock account not found
                mock_client.table().select().eq().eq().eq().execute.return_value = MagicMock(
                    data=[]
                )

                response = test_client.get(
                    "/api/v1/accounts/dsp/NONEXISTENT_ADV/seats",
                    headers={"Authorization": "Bearer test_clerk_token"}
                )

                # Verify account not found error
                assert response.status_code == 404
                assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_token_refresh_workflow(
        self,
        test_client: TestClient,
        mock_auth_user,
        mock_dsp_account,
        mock_seats_response
    ):
        """
        E2E Test Scenario 4: Token refresh workflow
        Tests: Auth → Account found → Expired token → Token refresh → Seats retrieval
        """
        # Mock expired token
        expired_token = {
            "access_token": "expired_token_123",
            "expires_at": (datetime.now(timezone.utc).timestamp() - 3600)  # Expired 1 hour ago
        }

        # Mock refreshed token
        refreshed_token = {
            "access_token": "refreshed_token_456",
            "expires_at": (datetime.now(timezone.utc).timestamp() + 3600)  # Valid for 1 hour
        }

        with patch("app.api.v1.accounts.RequireAuth") as mock_auth:
            mock_auth.return_value = lambda: mock_auth_user

            with patch("app.api.v1.accounts.get_supabase_service_client") as mock_supabase:
                mock_client = MagicMock()
                mock_supabase.return_value = mock_client
                mock_client.table().select().eq().eq().eq().execute.return_value = MagicMock(
                    data=[mock_dsp_account]
                )

                with patch("app.api.v1.accounts.get_user_token", new_callable=AsyncMock) as mock_get_token:
                    mock_get_token.return_value = expired_token

                    with patch("app.api.v1.accounts.refresh_token_if_needed", new_callable=AsyncMock) as mock_refresh:
                        mock_refresh.return_value = refreshed_token

                        with patch("app.services.dsp_amc_service.dsp_amc_service.list_advertiser_seats", new_callable=AsyncMock) as mock_list_seats:
                            mock_list_seats.return_value = mock_seats_response

                            response = test_client.get(
                                "/api/v1/accounts/dsp/DSP_ADV_789/seats",
                                headers={"Authorization": "Bearer test_clerk_token"}
                            )

                            # Verify successful response after token refresh
                            assert response.status_code == 200
                            data = response.json()
                            assert "advertiserSeats" in data

                            # Verify token refresh was called
                            mock_refresh.assert_called_once()

                            # Verify API call used refreshed token
                            mock_list_seats.assert_called_once_with(
                                access_token="refreshed_token_456",
                                advertiser_id="DSP_ADV_789",
                                exchange_ids=None,
                                max_results=200,
                                next_token=None,
                                profile_id=None
                            )

    @pytest.mark.asyncio
    async def test_pagination_workflow(
        self,
        test_client: TestClient,
        mock_auth_user,
        mock_dsp_account,
        mock_valid_token
    ):
        """
        E2E Test Scenario 5: Pagination workflow
        Tests: Auth → Paginated seats retrieval → Next page handling
        """
        # Mock first page response
        first_page_response = {
            "advertiserSeats": [
                {
                    "advertiserId": "DSP_ADV_789",
                    "currentSeats": [
                        {
                            "exchangeId": "1",
                            "exchangeName": "Google Ad Manager",
                            "dealCreationId": "DEAL_001",
                            "spendTrackingId": "SPEND_001"
                        }
                    ]
                }
            ],
            "nextToken": "next_page_token_123"
        }

        with patch("app.api.v1.accounts.RequireAuth") as mock_auth:
            mock_auth.return_value = lambda: mock_auth_user

            with patch("app.api.v1.accounts.get_supabase_service_client") as mock_supabase:
                mock_client = MagicMock()
                mock_supabase.return_value = mock_client
                mock_client.table().select().eq().eq().eq().execute.return_value = MagicMock(
                    data=[mock_dsp_account]
                )

                with patch("app.api.v1.accounts.get_user_token", new_callable=AsyncMock) as mock_get_token:
                    mock_get_token.return_value = mock_valid_token

                    with patch("app.api.v1.accounts.refresh_token_if_needed", new_callable=AsyncMock) as mock_refresh:
                        mock_refresh.return_value = mock_valid_token

                        with patch("app.services.dsp_amc_service.dsp_amc_service.list_advertiser_seats", new_callable=AsyncMock) as mock_list_seats:
                            mock_list_seats.return_value = first_page_response

                            # Test first page request
                            response = test_client.get(
                                "/api/v1/accounts/dsp/DSP_ADV_789/seats",
                                params={"max_results": 1},
                                headers={"Authorization": "Bearer test_clerk_token"}
                            )

                            # Verify first page response
                            assert response.status_code == 200
                            data = response.json()
                            assert "nextToken" in data
                            assert data["nextToken"] == "next_page_token_123"
                            assert len(data["advertiserSeats"][0]["currentSeats"]) == 1

                            # Verify pagination parameters
                            mock_list_seats.assert_called_once_with(
                                access_token="valid_access_token_123",
                                advertiser_id="DSP_ADV_789",
                                exchange_ids=None,
                                max_results=1,
                                next_token=None,
                                profile_id=None
                            )

    @pytest.mark.asyncio
    async def test_refresh_seats_workflow(
        self,
        test_client: TestClient,
        mock_auth_user,
        mock_dsp_account,
        mock_valid_token,
        mock_seats_response
    ):
        """
        E2E Test Scenario 6: Manual refresh workflow
        Tests: Auth → Force refresh → Database update → Sync log creation
        """
        with patch("app.api.v1.accounts.RequireAuth") as mock_auth:
            mock_auth.return_value = lambda: mock_auth_user

            with patch("app.api.v1.accounts.get_supabase_service_client") as mock_supabase:
                mock_client = MagicMock()
                mock_supabase.return_value = mock_client

                # Mock account lookup
                mock_client.table().select().eq().eq().eq().execute.return_value = MagicMock(
                    data=[mock_dsp_account]
                )

                # Mock sync log creation
                mock_client.table("dsp_seats_sync_log").insert().execute.return_value = MagicMock(
                    data=[{"id": "sync_log_456"}]
                )

                with patch("app.api.v1.accounts.get_user_token", new_callable=AsyncMock) as mock_get_token:
                    mock_get_token.return_value = mock_valid_token

                    with patch("app.api.v1.accounts.refresh_token_if_needed", new_callable=AsyncMock) as mock_refresh:
                        mock_refresh.return_value = mock_valid_token

                        with patch("app.services.dsp_amc_service.dsp_amc_service.list_advertiser_seats", new_callable=AsyncMock) as mock_list_seats:
                            mock_list_seats.return_value = mock_seats_response

                            # Execute refresh workflow
                            response = test_client.post(
                                "/api/v1/accounts/dsp/DSP_ADV_789/seats/refresh",
                                json={"force": True, "include_sync_log": True},
                                headers={"Authorization": "Bearer test_clerk_token"}
                            )

                            # Verify refresh response
                            assert response.status_code == 200
                            data = response.json()
                            assert data["success"] is True
                            assert "seats_updated" in data
                            assert "last_sync" in data
                            assert "sync_log_id" in data

    @pytest.mark.asyncio
    async def test_sync_history_workflow(
        self,
        test_client: TestClient,
        mock_auth_user,
        mock_dsp_account
    ):
        """
        E2E Test Scenario 7: Sync history retrieval workflow
        Tests: Auth → Account validation → Sync history query → Response
        """
        mock_sync_history = [
            {
                "id": "sync_1",
                "sync_status": "success",
                "seats_retrieved": 5,
                "exchanges_count": 3,
                "error_message": None,
                "created_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "id": "sync_2",
                "sync_status": "failed",
                "seats_retrieved": 0,
                "exchanges_count": 0,
                "error_message": "Rate limit exceeded",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        ]

        with patch("app.api.v1.accounts.RequireAuth") as mock_auth:
            mock_auth.return_value = lambda: mock_auth_user

            with patch("app.api.v1.accounts.get_supabase_service_client") as mock_supabase:
                mock_client = MagicMock()
                mock_supabase.return_value = mock_client

                # Mock account lookup
                mock_client.table("user_accounts").select().eq().eq().eq().execute.return_value = MagicMock(
                    data=[mock_dsp_account]
                )

                # Mock sync history lookup
                mock_client.table("dsp_seats_sync_log").select().eq().order().limit().execute.return_value = MagicMock(
                    data=mock_sync_history
                )

                # Mock count
                mock_client.table("dsp_seats_sync_log").select().eq().execute.return_value = MagicMock(
                    data=mock_sync_history
                )

                response = test_client.get(
                    "/api/v1/accounts/dsp/DSP_ADV_789/seats/sync-history",
                    params={"limit": 10, "offset": 0},
                    headers={"Authorization": "Bearer test_clerk_token"}
                )

                # Verify sync history response
                assert response.status_code == 200
                data = response.json()
                assert "sync_history" in data
                assert "total_count" in data
                assert len(data["sync_history"]) == 2
                assert data["sync_history"][0]["sync_status"] == "success"
                assert data["sync_history"][1]["sync_status"] == "failed"


class TestDSPSeatsErrorScenarios:
    """Error scenario testing for DSP seats feature"""

    @pytest.mark.asyncio
    async def test_rate_limit_error_scenario(self, test_client: TestClient):
        """
        E2E Error Scenario 1: Rate limiting
        Tests: Valid request → Rate limit hit → Proper error response with retry-after
        """
        mock_user = {"user_id": "user123"}
        mock_account = {
            "id": "acc123",
            "user_id": "user123",
            "amazon_account_id": "DSP123",
            "account_type": "dsp"
        }
        mock_token = {"access_token": "valid_token"}

        with patch("app.api.v1.accounts.RequireAuth") as mock_auth:
            mock_auth.return_value = lambda: mock_user

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
                            mock_list_seats.side_effect = RateLimitError(retry_after=60)

                            response = test_client.get(
                                "/api/v1/accounts/dsp/DSP123/seats",
                                headers={"Authorization": "Bearer test_clerk_token"}
                            )

                            # Verify rate limit error response
                            assert response.status_code == 429
                            assert "Rate limit exceeded" in response.json()["detail"]
                            assert response.headers["Retry-After"] == "60"

    @pytest.mark.asyncio
    async def test_token_refresh_failure_scenario(self, test_client: TestClient):
        """
        E2E Error Scenario 2: Token refresh failure
        Tests: Valid request → Token expired → Refresh fails → Auth error
        """
        mock_user = {"user_id": "user123"}
        mock_account = {
            "id": "acc123",
            "user_id": "user123",
            "amazon_account_id": "DSP123",
            "account_type": "dsp"
        }
        mock_token = {"access_token": "expired_token"}

        with patch("app.api.v1.accounts.RequireAuth") as mock_auth:
            mock_auth.return_value = lambda: mock_user

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
                            mock_list_seats.side_effect = TokenRefreshError("Refresh token expired")

                            response = test_client.get(
                                "/api/v1/accounts/dsp/DSP123/seats",
                                headers={"Authorization": "Bearer test_clerk_token"}
                            )

                            # Verify token refresh error response
                            assert response.status_code == 401
                            assert "Refresh token expired" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_amazon_api_error_scenario(self, test_client: TestClient):
        """
        E2E Error Scenario 3: Amazon API error
        Tests: Valid request → Amazon API returns error → Proper error handling
        """
        mock_user = {"user_id": "user123"}
        mock_account = {
            "id": "acc123",
            "user_id": "user123",
            "amazon_account_id": "DSP123",
            "account_type": "dsp"
        }
        mock_token = {"access_token": "valid_token"}

        with patch("app.api.v1.accounts.RequireAuth") as mock_auth:
            mock_auth.return_value = lambda: mock_user

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
                            from app.core.exceptions import AmazonDSPError
                            mock_list_seats.side_effect = AmazonDSPError("Advertiser not found", 404)

                            response = test_client.get(
                                "/api/v1/accounts/dsp/DSP123/seats",
                                headers={"Authorization": "Bearer test_clerk_token"}
                            )

                            # Verify Amazon API error response
                            assert response.status_code == 404
                            assert "Advertiser not found" in response.json()["detail"]