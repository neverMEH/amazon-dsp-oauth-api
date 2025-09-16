import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone
import httpx
from app.services.dsp_amc_service import dsp_amc_service
from app.core.exceptions import TokenRefreshError, RateLimitError


@pytest.mark.asyncio
async def test_list_advertiser_seats_success():
    """Test successful retrieval of DSP advertiser seats"""
    mock_response = {
        "advertiserSeats": [
            {
                "advertiserId": "DSP123",
                "currentSeats": [
                    {
                        "exchangeId": "1",
                        "exchangeName": "Google Ad Manager",
                        "dealCreationId": "DEAL123",
                        "spendTrackingId": "TRACK456"
                    },
                    {
                        "exchangeId": "2",
                        "exchangeName": "Amazon Publisher Services",
                        "dealCreationId": None,
                        "spendTrackingId": "APS-TRACK-789"
                    }
                ]
            }
        ],
        "nextToken": None
    }

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance

        mock_post = MagicMock()
        mock_post.status_code = 200
        mock_post.json = MagicMock(return_value=mock_response)
        mock_instance.post.return_value = mock_post

        result = await dsp_amc_service.list_advertiser_seats(
            access_token="test_token",
            advertiser_id="DSP123"
        )

        assert result == mock_response
        assert len(result["advertiserSeats"]) == 1
        assert result["advertiserSeats"][0]["advertiserId"] == "DSP123"
        assert len(result["advertiserSeats"][0]["currentSeats"]) == 2

        # Verify the correct headers were sent
        mock_instance.post.assert_called_once()
        call_args = mock_instance.post.call_args
        headers = call_args.kwargs["headers"]
        assert headers["Amazon-Ads-AccountId"] == "DSP123"
        assert headers["Amazon-Advertising-API-ClientId"] is not None
        assert headers["Authorization"] == "Bearer test_token"


@pytest.mark.asyncio
async def test_list_advertiser_seats_with_filters():
    """Test listing advertiser seats with exchange filters and pagination"""
    mock_response = {
        "advertiserSeats": [
            {
                "advertiserId": "DSP456",
                "currentSeats": [
                    {
                        "exchangeId": "1",
                        "exchangeName": "Google Ad Manager",
                        "dealCreationId": "DEAL789",
                        "spendTrackingId": "TRACK123"
                    }
                ]
            }
        ],
        "nextToken": "eyJsYXN0S2V5IjoiMTIzIn0="
    }

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance

        mock_post = MagicMock()
        mock_post.status_code = 200
        mock_post.json = MagicMock(return_value=mock_response)
        mock_instance.post.return_value = mock_post

        result = await dsp_amc_service.list_advertiser_seats(
            access_token="test_token",
            advertiser_id="DSP456",
            exchange_ids=["1", "2"],
            max_results=50,
            next_token="previous_token",
            profile_id="12345"
        )

        assert result["nextToken"] == "eyJsYXN0S2V5IjoiMTIzIn0="

        # Verify request payload
        call_args = mock_instance.post.call_args
        payload = call_args.kwargs["json"]
        assert payload["exchangeIdFilter"] == ["1", "2"]
        assert payload["maxResults"] == 50
        assert payload["nextToken"] == "previous_token"

        # Verify optional profile header was included
        headers = call_args.kwargs["headers"]
        assert headers["Amazon-Advertising-API-Scope"] == "12345"


@pytest.mark.asyncio
async def test_list_advertiser_seats_token_expired():
    """Test handling of expired token (401 response)"""
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance

        mock_post = MagicMock()
        mock_post.status_code = 401
        mock_instance.post.return_value = mock_post

        with pytest.raises(TokenRefreshError) as exc_info:
            await dsp_amc_service.list_advertiser_seats(
                access_token="expired_token",
                advertiser_id="DSP123"
            )

        assert "Access token expired or invalid" in str(exc_info.value)


@pytest.mark.asyncio
async def test_list_advertiser_seats_insufficient_permissions():
    """Test handling of insufficient permissions (403 response)"""
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance

        mock_post = MagicMock()
        mock_post.status_code = 403
        mock_post.json = MagicMock(return_value={
            "errors": [{"errorCode": "FORBIDDEN", "errorMessage": "Insufficient permissions"}]
        })
        mock_instance.post.return_value = mock_post

        result = await dsp_amc_service.list_advertiser_seats(
            access_token="test_token",
            advertiser_id="DSP123"
        )

        # Should return empty result with error message
        assert result["advertiserSeats"] == []
        assert "Insufficient permissions" in result["error"]


@pytest.mark.asyncio
async def test_list_advertiser_seats_rate_limit_exceeded():
    """Test handling of rate limit exceeded (429 response)"""
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance

        mock_post = MagicMock()
        mock_post.status_code = 429
        mock_post.headers = {"Retry-After": "30"}
        mock_instance.post.return_value = mock_post

        with pytest.raises(RateLimitError) as exc_info:
            await dsp_amc_service.list_advertiser_seats(
                access_token="test_token",
                advertiser_id="DSP123"
            )

        assert exc_info.value.retry_after == 30


@pytest.mark.asyncio
async def test_list_advertiser_seats_invalid_advertiser():
    """Test handling of invalid advertiser ID (400 response)"""
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance

        mock_post = MagicMock()
        mock_post.status_code = 400
        mock_post.text = '{"errors": [{"errorCode": "INVALID_ADVERTISER", "errorMessage": "Advertiser ID not found"}]}'
        mock_post.json = MagicMock(return_value={
            "errors": [{"errorCode": "INVALID_ADVERTISER", "errorMessage": "Advertiser ID not found"}]
        })
        mock_instance.post.return_value = mock_post

        with pytest.raises(ValueError) as exc_info:
            await dsp_amc_service.list_advertiser_seats(
                access_token="test_token",
                advertiser_id="INVALID"
            )

        assert "Invalid request" in str(exc_info.value)


@pytest.mark.asyncio
async def test_list_advertiser_seats_timeout():
    """Test handling of request timeout"""
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance

        mock_instance.post.side_effect = httpx.TimeoutException("Request timeout")

        with pytest.raises(Exception) as exc_info:
            await dsp_amc_service.list_advertiser_seats(
                access_token="test_token",
                advertiser_id="DSP123"
            )

        assert "Request timeout" in str(exc_info.value)


@pytest.mark.asyncio
async def test_list_advertiser_seats_network_error():
    """Test handling of network errors"""
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance

        mock_instance.post.side_effect = httpx.RequestError("Network error")

        with pytest.raises(Exception) as exc_info:
            await dsp_amc_service.list_advertiser_seats(
                access_token="test_token",
                advertiser_id="DSP123"
            )

        assert "Network error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_list_advertiser_seats_max_results_boundary():
    """Test that max_results is capped at 200"""
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance

        mock_post = MagicMock()
        mock_post.status_code = 200
        mock_post.json = MagicMock(return_value={"advertiserSeats": [], "nextToken": None})
        mock_instance.post.return_value = mock_post

        await dsp_amc_service.list_advertiser_seats(
            access_token="test_token",
            advertiser_id="DSP123",
            max_results=500  # Exceeds maximum
        )

        # Verify max_results was capped at 200
        call_args = mock_instance.post.call_args
        payload = call_args.kwargs["json"]
        assert payload["maxResults"] == 200


@pytest.mark.asyncio
async def test_list_advertiser_seats_empty_response():
    """Test handling of empty advertiser seats response"""
    mock_response = {
        "advertiserSeats": [],
        "nextToken": None
    }

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance

        mock_post = MagicMock()
        mock_post.status_code = 200
        mock_post.json = MagicMock(return_value=mock_response)
        mock_instance.post.return_value = mock_post

        result = await dsp_amc_service.list_advertiser_seats(
            access_token="test_token",
            advertiser_id="DSP789"
        )

        assert result["advertiserSeats"] == []
        assert result["nextToken"] is None


@pytest.mark.asyncio
async def test_list_advertiser_seats_server_error():
    """Test handling of server errors (500 response)"""
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance

        mock_post = MagicMock()
        mock_post.status_code = 500
        mock_post.text = '{"errors": [{"errorCode": "INTERNAL_ERROR", "errorMessage": "Internal server error"}]}'
        mock_post.json = MagicMock(return_value={
            "errors": [{"errorCode": "INTERNAL_ERROR", "errorMessage": "Internal server error"}]
        })
        mock_instance.post.return_value = mock_post

        with pytest.raises(Exception) as exc_info:
            await dsp_amc_service.list_advertiser_seats(
                access_token="test_token",
                advertiser_id="DSP123"
            )

        assert "API Error: 500" in str(exc_info.value)