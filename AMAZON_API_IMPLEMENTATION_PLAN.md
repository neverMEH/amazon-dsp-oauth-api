# Amazon API Implementation Plan

## Overview
This document outlines the implementation plan for missing Amazon Advertising API features identified in the current system.

## Priority 1: Critical Fixes

### 1.1 Fix Documentation Inconsistency in Code
**File**: `backend/app/api/v1/accounts.py` (line 184)
**Current Issue**: Docstring incorrectly states `GET https://advertising-api.amazon.com/am/accounts`
**Fix Required**:
```python
# Change docstring from:
# - URL: GET https://advertising-api.amazon.com/am/accounts
# To:
# - URL: POST https://advertising-api.amazon.com/adsAccounts/list
```
**Effort**: 5 minutes
**Impact**: Documentation accuracy

### 1.2 Add Profiles API Pagination
**File**: `backend/app/services/account_service.py`
**Implementation**:
```python
async def list_profiles(self, access_token: str, next_token: Optional[str] = None) -> Dict:
    """
    List advertising profiles with pagination support
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Amazon-Advertising-API-ClientId": settings.amazon_client_id,
        "Content-Type": "application/json"
    }

    params = {}
    if next_token:
        params["nextToken"] = next_token

    # Add pagination parameters
    params["maxResults"] = 100

    # Rest of implementation...
```
**Effort**: 2 hours
**Impact**: Handles accounts with many profiles

## Priority 2: New Feature - Account Registration

### 2.1 RegisterAdsAccount Endpoint
**Purpose**: Allow users to register/link new advertising accounts

#### API Endpoint
```python
# New file: backend/app/api/v1/account_registration.py

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel

router = APIRouter(prefix="/accounts", tags=["account-registration"])

class RegisterAccountRequest(BaseModel):
    marketplace_id: str
    advertiser_id: str
    account_type: str = "ADVERTISER"  # or "AGENCY"

class RegisterAccountResponse(BaseModel):
    account_id: str
    status: str
    message: str

@router.post("/register", response_model=RegisterAccountResponse)
async def register_amazon_account(
    request: RegisterAccountRequest = Body(...),
    current_user: Dict = Depends(RequireAuth),
    supabase = Depends(get_supabase_client)
):
    """
    Register a new Amazon Advertising account

    Amazon API: POST /adsAccounts/register
    """
    # Implementation details below
```

#### Service Layer
```python
# Add to backend/app/services/account_service.py

async def register_account(
    self,
    access_token: str,
    marketplace_id: str,
    advertiser_id: str,
    account_type: str = "ADVERTISER"
) -> Dict:
    """
    Register a new advertising account with Amazon

    Endpoint: POST /adsAccounts/register
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Amazon-Advertising-API-ClientId": settings.amazon_client_id,
        "Content-Type": "application/vnd.registeraccountrequest.v1+json",
        "Accept": "application/json"
    }

    request_body = {
        "marketplaceId": marketplace_id,
        "advertiserId": advertiser_id,
        "accountType": account_type
    }

    url = f"{self.base_url}/adsAccounts/register"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers=headers,
            json=request_body,
            timeout=30.0
        )

        # Handle response...
        return response.json()
```

**Effort**: 4 hours
**Impact**: Enable new account onboarding

## Priority 3: Reporting API Implementation

### 3.1 Core Reporting Service
**New File**: `backend/app/services/reporting_service.py`

```python
from typing import Dict, List, Optional
from datetime import datetime, date
import httpx
import structlog
from app.config import settings

logger = structlog.get_logger()

class AmazonReportingService:
    """Handle Amazon Advertising Reporting API operations"""

    def __init__(self):
        self.base_url = "https://advertising-api.amazon.com"
        self.api_version = "v3"

    async def create_report(
        self,
        access_token: str,
        profile_id: str,
        report_type: str,
        date_range: Dict,
        metrics: List[str],
        dimensions: Optional[List[str]] = None
    ) -> str:
        """
        Create a new report request

        Endpoint: POST /reporting/reports
        Returns: Report ID
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Amazon-Advertising-API-ClientId": settings.amazon_client_id,
            "Amazon-Advertising-API-Scope": profile_id,
            "Content-Type": "application/vnd.createreportrequest.v3+json"
        }

        request_body = {
            "reportType": report_type,  # e.g., "campaigns", "adGroups", "keywords"
            "timeUnit": "DAILY",
            "format": "JSON",
            "groupBy": dimensions or ["campaignId"],
            "columns": metrics,
            "reportDate": date_range.get("endDate"),
            "creativeType": "all"
        }

        url = f"{self.base_url}/{self.api_version}/reports"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json=request_body,
                timeout=30.0
            )

            if response.status_code == 202:
                return response.json()["reportId"]
            else:
                raise Exception(f"Report creation failed: {response.status_code}")

    async def get_report_status(
        self,
        access_token: str,
        profile_id: str,
        report_id: str
    ) -> Dict:
        """
        Check report generation status

        Endpoint: GET /reporting/reports/{reportId}
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Amazon-Advertising-API-ClientId": settings.amazon_client_id,
            "Amazon-Advertising-API-Scope": profile_id
        }

        url = f"{self.base_url}/{self.api_version}/reports/{report_id}"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=headers,
                timeout=30.0
            )

            return response.json()

    async def download_report(
        self,
        access_token: str,
        profile_id: str,
        report_id: str
    ) -> Dict:
        """
        Download completed report

        Endpoint: GET /reporting/reports/{reportId}/download
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Amazon-Advertising-API-ClientId": settings.amazon_client_id,
            "Amazon-Advertising-API-Scope": profile_id,
            "Accept": "application/vnd.reportresource.v3+json"
        }

        url = f"{self.base_url}/{self.api_version}/reports/{report_id}/download"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=headers,
                timeout=60.0  # Longer timeout for downloads
            )

            if response.status_code == 200:
                # Check if response is gzipped
                if response.headers.get("Content-Encoding") == "gzip":
                    import gzip
                    import json
                    content = gzip.decompress(response.content)
                    return json.loads(content)
                else:
                    return response.json()
            else:
                raise Exception(f"Report download failed: {response.status_code}")

# Singleton instance
reporting_service = AmazonReportingService()
```

### 3.2 Reporting API Endpoints
```python
# New file: backend/app/api/v1/reports.py

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Dict, List, Optional
from datetime import datetime, date
from pydantic import BaseModel

router = APIRouter(prefix="/reports", tags=["reporting"])

class CreateReportRequest(BaseModel):
    profile_id: str
    report_type: str  # "campaigns", "adGroups", "keywords", "productAds"
    start_date: date
    end_date: date
    metrics: List[str]  # ["impressions", "clicks", "cost", "conversions"]
    dimensions: Optional[List[str]] = None

class ReportResponse(BaseModel):
    report_id: str
    status: str
    created_at: datetime
    download_url: Optional[str] = None

@router.post("/create", response_model=ReportResponse)
async def create_report(
    request: CreateReportRequest = Body(...),
    current_user: Dict = Depends(RequireAuth),
    supabase = Depends(get_supabase_client)
):
    """Create a new advertising report"""
    # Get user token
    token_data = await get_user_token(user_id, supabase)

    # Create report
    report_id = await reporting_service.create_report(
        access_token=token_data["access_token"],
        profile_id=request.profile_id,
        report_type=request.report_type,
        date_range={
            "startDate": request.start_date.isoformat(),
            "endDate": request.end_date.isoformat()
        },
        metrics=request.metrics,
        dimensions=request.dimensions
    )

    # Store report request in database
    supabase.table("report_requests").insert({
        "user_id": user_id,
        "report_id": report_id,
        "profile_id": request.profile_id,
        "report_type": request.report_type,
        "status": "PENDING",
        "created_at": datetime.utcnow().isoformat()
    }).execute()

    return ReportResponse(
        report_id=report_id,
        status="PENDING",
        created_at=datetime.utcnow()
    )

@router.get("/{report_id}/status")
async def get_report_status(
    report_id: str,
    current_user: Dict = Depends(RequireAuth),
    supabase = Depends(get_supabase_client)
):
    """Check report generation status"""
    # Implementation...

@router.get("/{report_id}/download")
async def download_report(
    report_id: str,
    current_user: Dict = Depends(RequireAuth),
    supabase = Depends(get_supabase_client)
):
    """Download completed report"""
    # Implementation...
```

**Effort**: 8 hours
**Impact**: Enable performance reporting and analytics

## Priority 4: DSP Campaign Management

### 4.1 DSP Campaign Service
```python
# New file: backend/app/services/dsp_campaign_service.py

class DSPCampaignService:
    """Handle DSP campaign management operations"""

    async def list_campaigns(
        self,
        access_token: str,
        profile_id: str,
        advertiser_id: str
    ) -> List[Dict]:
        """List all DSP campaigns"""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Amazon-Advertising-API-ClientId": settings.amazon_client_id,
            "Amazon-DSP-Advertiser-Id": advertiser_id,
            "Content-Type": "application/json"
        }

        url = f"{self.base_url}/dsp/campaigns"
        # Implementation...

    async def create_campaign(
        self,
        access_token: str,
        profile_id: str,
        campaign_data: Dict
    ) -> Dict:
        """Create a new DSP campaign"""
        # Implementation...

    async def update_campaign(
        self,
        access_token: str,
        profile_id: str,
        campaign_id: str,
        updates: Dict
    ) -> Dict:
        """Update DSP campaign settings"""
        # Implementation...
```

**Effort**: 12 hours
**Impact**: Full DSP campaign management

## Priority 5: Enhanced Rate Limiting

### 5.1 Rate Limiter with Exponential Backoff
```python
# New file: backend/app/core/rate_limiter.py

import asyncio
from typing import Optional, Callable
import time
import random

class ExponentialBackoffRateLimiter:
    """
    Rate limiter with exponential backoff for Amazon API calls
    """

    def __init__(
        self,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.request_times = []
        self.rate_limit = 2  # requests per second

    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ):
        """
        Execute function with automatic retry and exponential backoff
        """
        for attempt in range(self.max_retries):
            try:
                # Check rate limit
                await self._check_rate_limit()

                # Execute function
                result = await func(*args, **kwargs)

                # Record successful request
                self.request_times.append(time.time())

                return result

            except RateLimitError as e:
                if attempt == self.max_retries - 1:
                    raise

                # Calculate backoff delay
                delay = min(
                    self.base_delay * (2 ** attempt) + random.uniform(0, 1),
                    self.max_delay
                )

                # Use Retry-After header if available
                if hasattr(e, 'retry_after'):
                    delay = max(delay, e.retry_after)

                logger.warning(
                    f"Rate limited, retrying in {delay}s",
                    attempt=attempt + 1,
                    max_retries=self.max_retries
                )

                await asyncio.sleep(delay)

    async def _check_rate_limit(self):
        """Check and enforce rate limit"""
        now = time.time()

        # Remove old requests outside the window
        self.request_times = [
            t for t in self.request_times
            if now - t < 1.0  # 1 second window
        ]

        # Check if we're at the limit
        if len(self.request_times) >= self.rate_limit:
            # Calculate wait time
            oldest_request = min(self.request_times)
            wait_time = 1.0 - (now - oldest_request)

            if wait_time > 0:
                await asyncio.sleep(wait_time)

# Usage in service
rate_limiter = ExponentialBackoffRateLimiter()

# Wrap API calls
async def list_accounts_with_retry(access_token: str):
    return await rate_limiter.execute_with_retry(
        account_service.list_ads_accounts,
        access_token
    )
```

**Effort**: 4 hours
**Impact**: Better handling of API rate limits

## Priority 6: Proactive Token Refresh

### 6.1 Background Token Refresher
```python
# New file: backend/app/services/token_refresh_scheduler.py

import asyncio
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler

class TokenRefreshScheduler:
    """
    Proactively refresh tokens before expiration
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.refresh_buffer = timedelta(minutes=10)  # Refresh 10 min before expiry

    async def start(self):
        """Start the scheduler"""
        self.scheduler.add_job(
            self.refresh_expiring_tokens,
            'interval',
            minutes=5,  # Check every 5 minutes
            id='token_refresh_job'
        )
        self.scheduler.start()

    async def refresh_expiring_tokens(self):
        """Check and refresh tokens that are about to expire"""
        supabase = get_supabase_client()

        # Get tokens expiring soon
        expiry_threshold = datetime.now(timezone.utc) + self.refresh_buffer

        result = supabase.table("oauth_tokens").select("*").lt(
            "expires_at", expiry_threshold.isoformat()
        ).execute()

        for token_record in result.data:
            try:
                # Decrypt refresh token
                refresh_token = token_service.decrypt_token(
                    token_record["encrypted_refresh_token"]
                )

                # Refresh the token
                new_tokens = await amazon_oauth_service.refresh_access_token(
                    refresh_token
                )

                # Update database
                new_expires = datetime.now(timezone.utc) + timedelta(
                    seconds=new_tokens.expires_in
                )

                supabase.table("oauth_tokens").update({
                    "encrypted_access_token": token_service.encrypt_token(
                        new_tokens.access_token
                    ),
                    "encrypted_refresh_token": token_service.encrypt_token(
                        new_tokens.refresh_token
                    ),
                    "expires_at": new_expires.isoformat(),
                    "last_refresh": datetime.now(timezone.utc).isoformat(),
                    "refresh_count": token_record["refresh_count"] + 1
                }).eq("id", token_record["id"]).execute()

                logger.info(
                    "Proactively refreshed token",
                    user_id=token_record["user_id"],
                    new_expiry=new_expires.isoformat()
                )

            except Exception as e:
                logger.error(
                    "Failed to refresh token proactively",
                    user_id=token_record["user_id"],
                    error=str(e)
                )

# Initialize in main.py
token_refresher = TokenRefreshScheduler()

@app.on_event("startup")
async def startup_event():
    await token_refresher.start()
```

**Effort**: 3 hours
**Impact**: Prevent token expiration errors

## Implementation Timeline

### Phase 1 (Week 1) - Critical Fixes
- [ ] Fix documentation inconsistencies (Priority 1.1)
- [ ] Add Profiles API pagination (Priority 1.2)
- [ ] Implement proactive token refresh (Priority 6)

### Phase 2 (Week 2) - Core Features
- [ ] Implement Account Registration endpoint (Priority 2)
- [ ] Add enhanced rate limiting (Priority 5)

### Phase 3 (Week 3-4) - Reporting
- [ ] Implement Reporting API service (Priority 3)
- [ ] Add reporting endpoints
- [ ] Create report storage schema

### Phase 4 (Week 5-6) - DSP Features
- [ ] Implement DSP Campaign Service (Priority 4)
- [ ] Add campaign management endpoints
- [ ] Integrate with existing account structure

## Database Schema Additions

### For Reporting
```sql
CREATE TABLE report_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    report_id VARCHAR(255) UNIQUE NOT NULL,
    profile_id VARCHAR(255) NOT NULL,
    report_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING',
    request_data JSONB,
    response_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    download_url TEXT
);

CREATE INDEX idx_report_requests_user_id ON report_requests(user_id);
CREATE INDEX idx_report_requests_status ON report_requests(status);
```

### For DSP Campaigns
```sql
CREATE TABLE dsp_campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    account_id UUID REFERENCES user_accounts(id) ON DELETE CASCADE,
    campaign_id VARCHAR(255) UNIQUE NOT NULL,
    campaign_name VARCHAR(255) NOT NULL,
    status VARCHAR(50),
    budget DECIMAL(15, 2),
    start_date DATE,
    end_date DATE,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_dsp_campaigns_user_id ON dsp_campaigns(user_id);
CREATE INDEX idx_dsp_campaigns_account_id ON dsp_campaigns(account_id);
```

## Testing Strategy

### Unit Tests
- Test each new service method
- Mock Amazon API responses
- Test error handling and retries

### Integration Tests
- Test full flow from API endpoint to database
- Test rate limiting behavior
- Test token refresh scenarios

### Load Tests
- Test rate limiter under high load
- Test pagination with large datasets
- Test concurrent report generation

## Monitoring & Observability

### Metrics to Track
- API call success/failure rates
- Token refresh success rates
- Average response times per endpoint
- Rate limit hits per hour
- Report generation times

### Logging
- Add structured logging for all new features
- Include correlation IDs for request tracking
- Log all API errors with context

### Alerts
- Token refresh failures
- High rate limit hit frequency
- Report generation failures
- Account registration errors

## Security Considerations

1. **API Key Rotation**: Implement mechanism to rotate API credentials
2. **Audit Logging**: Log all account registration and campaign changes
3. **Data Encryption**: Ensure all sensitive campaign data is encrypted
4. **Access Control**: Implement fine-grained permissions for DSP features
5. **Rate Limiting**: Implement per-user rate limits to prevent abuse

## Rollback Plan

Each feature should be:
1. Feature-flagged for gradual rollout
2. Backwards compatible with existing code
3. Tested in staging environment first
4. Monitored closely after deployment

## Success Criteria

- [ ] All API endpoints match Amazon's specifications
- [ ] No increase in error rates after deployment
- [ ] Token refresh happens proactively 99% of the time
- [ ] Rate limiting reduces 429 errors by 90%
- [ ] Report generation success rate > 95%
- [ ] DSP campaign management fully functional

## Next Steps

1. Review and approve implementation plan
2. Set up development environment for testing
3. Create feature branches for each priority
4. Begin Phase 1 implementation
5. Schedule weekly progress reviews