"""
Amazon DSP Campaign Insights API Service
"""
import httpx
from typing import Dict, List, Optional, Any
import structlog
from datetime import datetime, timezone, timedelta

from app.config import settings
from app.core.exceptions import (
    TokenRefreshError, 
    RateLimitError, 
    APIQuotaExceededError,
    DSPPermissionError
)

logger = structlog.get_logger()


class CampaignInsightsService:
    """Handle Amazon DSP Campaign Insights API operations"""
    
    def __init__(self):
        """Initialize campaign insights service"""
        self.base_url = "https://advertising-api.amazon.com"
        self.dsp_api_version = "v1"
        
    async def get_campaigns(
        self, 
        access_token: str, 
        profile_id: str,
        advertiser_id: str,
        limit: int = 100,
        next_token: Optional[str] = None,
        campaign_ids: Optional[List[str]] = None
    ) -> Dict:
        """
        Retrieve DSP campaigns
        
        Endpoint Details:
        - URL: GET /dsp/campaigns
        - Required Headers: Authorization, Amazon-Advertising-API-ClientId, Amazon-Advertising-API-Scope
        - Query Parameters: advertiserId, nextToken, maxResults, campaignIds
        
        Args:
            access_token: Valid access token
            profile_id: The profile ID for scope
            advertiser_id: The advertiser ID
            limit: Maximum results (1-100)
            next_token: Pagination token
            campaign_ids: Filter by specific campaign IDs
            
        Returns:
            Dict containing campaigns and pagination info
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Amazon-Advertising-API-ClientId": settings.amazon_client_id,
            "Amazon-Advertising-API-Scope": profile_id,
            "Content-Type": "application/json"
        }
        
        params = {
            "advertiserId": advertiser_id,
            "maxResults": min(limit, 100)
        }
        
        if next_token:
            params["nextToken"] = next_token
            
        if campaign_ids:
            params["campaignIds"] = ",".join(campaign_ids)
        
        url = f"{self.base_url}/dsp/campaigns"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=30.0
                )
                
                await self._handle_api_errors(response, profile_id, "get_campaigns")
                
                campaigns_data = response.json()
                
                logger.info(
                    "Successfully retrieved campaigns",
                    profile_id=profile_id,
                    advertiser_id=advertiser_id,
                    campaign_count=len(campaigns_data.get("campaigns", []))
                )
                
                return campaigns_data
                
        except httpx.TimeoutException:
            logger.error("Campaigns request timeout", profile_id=profile_id)
            raise Exception("Request timeout")
        except httpx.RequestError as e:
            logger.error("Campaigns request network error", profile_id=profile_id, error=str(e))
            raise Exception(f"Network error: {str(e)}")
    
    async def get_campaign_metrics(
        self,
        access_token: str,
        profile_id: str,
        advertiser_id: str,
        start_date: str,
        end_date: str,
        campaign_ids: Optional[List[str]] = None,
        metrics: Optional[List[str]] = None
    ) -> Dict:
        """
        Get campaign performance metrics
        
        Endpoint Details:
        - URL: POST /dsp/reports
        - Required Headers: Authorization, Amazon-Advertising-API-ClientId, Amazon-Advertising-API-Scope
        
        Args:
            access_token: Valid access token
            profile_id: The profile ID for scope
            advertiser_id: The advertiser ID
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format)
            campaign_ids: Filter by specific campaign IDs
            metrics: List of metrics to retrieve
            
        Returns:
            Dict containing report data
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Amazon-Advertising-API-ClientId": settings.amazon_client_id,
            "Amazon-Advertising-API-Scope": profile_id,
            "Content-Type": "application/json"
        }
        
        # Default metrics for campaign insights
        default_metrics = [
            "impressions",
            "clicks",
            "clickThroughRate",
            "totalCost",
            "eCPM",
            "eCPC",
            "conversions",
            "conversionRate",
            "costPerConversion",
            "reach",
            "frequency"
        ]
        
        report_request = {
            "reportType": "CAMPAIGN",
            "timeUnit": "DAILY",
            "format": "JSON",
            "startDate": start_date,
            "endDate": end_date,
            "advertiserId": advertiser_id,
            "metrics": metrics or default_metrics
        }
        
        if campaign_ids:
            report_request["campaignIds"] = campaign_ids
        
        url = f"{self.base_url}/dsp/reports"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=report_request,
                    timeout=60.0  # Reports can take longer
                )
                
                await self._handle_api_errors(response, profile_id, "get_campaign_metrics")
                
                report_response = response.json()
                
                logger.info(
                    "Successfully requested campaign metrics report",
                    profile_id=profile_id,
                    advertiser_id=advertiser_id,
                    report_id=report_response.get("reportId")
                )
                
                return report_response
                
        except httpx.TimeoutException:
            logger.error("Campaign metrics request timeout", profile_id=profile_id)
            raise Exception("Request timeout")
        except httpx.RequestError as e:
            logger.error("Campaign metrics request network error", profile_id=profile_id, error=str(e))
            raise Exception(f"Network error: {str(e)}")
    
    async def get_report_status(
        self,
        access_token: str,
        profile_id: str,
        report_id: str
    ) -> Dict:
        """
        Check report generation status
        
        Args:
            access_token: Valid access token
            profile_id: The profile ID for scope
            report_id: The report ID to check
            
        Returns:
            Dict containing report status
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Amazon-Advertising-API-ClientId": settings.amazon_client_id,
            "Amazon-Advertising-API-Scope": profile_id,
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}/dsp/reports/{report_id}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=headers,
                    timeout=30.0
                )
                
                await self._handle_api_errors(response, profile_id, "get_report_status")
                
                status_data = response.json()
                
                logger.info(
                    "Retrieved report status",
                    profile_id=profile_id,
                    report_id=report_id,
                    status=status_data.get("status")
                )
                
                return status_data
                
        except httpx.TimeoutException:
            logger.error("Report status request timeout", profile_id=profile_id, report_id=report_id)
            raise Exception("Request timeout")
        except httpx.RequestError as e:
            logger.error("Report status request network error", profile_id=profile_id, error=str(e))
            raise Exception(f"Network error: {str(e)}")
    
    async def download_report(
        self,
        access_token: str,
        profile_id: str,
        download_url: str
    ) -> Dict:
        """
        Download completed report data
        
        Args:
            access_token: Valid access token
            profile_id: The profile ID for scope
            download_url: The URL to download report from
            
        Returns:
            Dict containing report data
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Amazon-Advertising-API-ClientId": settings.amazon_client_id,
            "Amazon-Advertising-API-Scope": profile_id
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    download_url,
                    headers=headers,
                    timeout=60.0
                )
                
                if response.status_code != 200:
                    logger.error(
                        "Report download failed",
                        profile_id=profile_id,
                        status_code=response.status_code,
                        url=download_url
                    )
                    raise Exception(f"Download failed: {response.status_code}")
                
                # Handle JSON response
                if response.headers.get("content-type", "").startswith("application/json"):
                    report_data = response.json()
                else:
                    # Handle other formats (CSV, etc.)
                    report_data = {"raw_data": response.text}
                
                logger.info(
                    "Successfully downloaded report",
                    profile_id=profile_id,
                    data_size=len(str(report_data))
                )
                
                return report_data
                
        except httpx.TimeoutException:
            logger.error("Report download timeout", profile_id=profile_id)
            raise Exception("Download timeout")
        except httpx.RequestError as e:
            logger.error("Report download network error", profile_id=profile_id, error=str(e))
            raise Exception(f"Network error: {str(e)}")
    
    async def _handle_api_errors(self, response: httpx.Response, profile_id: str, operation: str):
        """Handle common API errors"""
        if response.status_code == 200:
            return
            
        error_data = {}
        try:
            error_data = response.json()
        except:
            error_data = {"error": response.text}
        
        if response.status_code == 401:
            logger.error("Unauthorized", profile_id=profile_id, operation=operation)
            raise TokenRefreshError("Access token expired or invalid")
        
        elif response.status_code == 403:
            logger.error("DSP access forbidden", profile_id=profile_id, operation=operation)
            raise DSPPermissionError(profile_id)
        
        elif response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            quota_type = response.headers.get("X-RateLimit-Type", "requests")
            logger.warning("Rate limit exceeded", retry_after=retry_after, quota_type=quota_type)
            raise APIQuotaExceededError(quota_type, response.headers.get("X-RateLimit-Reset"))
        
        elif response.status_code >= 500:
            logger.error("Server error", status_code=response.status_code, error=error_data)
            raise Exception(f"Server error: {response.status_code}")
        
        else:
            logger.error("API error", status_code=response.status_code, error=error_data)
            raise Exception(f"API Error: {response.status_code} - {error_data}")


# Create singleton instance
campaign_insights_service = CampaignInsightsService()