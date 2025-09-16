"""
Account type schemas for multi-type account support (Sponsored Ads, DSP, AMC)
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from enum import Enum


class AccountType(str, Enum):
    """Enum for account types"""
    ADVERTISING = "advertising"  # Sponsored Ads
    DSP = "dsp"
    AMC = "amc"


class AccountTypeFilter(BaseModel):
    """Filter for account types"""
    account_types: Optional[List[AccountType]] = Field(
        None,
        description="Filter by specific account types"
    )
    has_profile_id: Optional[bool] = Field(None, description="Filter accounts with profile ID")
    has_entity_id: Optional[bool] = Field(None, description="Filter accounts with entity ID")
    managed_recently: Optional[bool] = Field(
        None,
        description="Filter accounts managed in last 30 days"
    )


class SponsoredAdsAccountResponse(BaseModel):
    """Response schema for Sponsored Ads accounts"""
    id: str = Field(..., description="Account UUID")
    user_id: str = Field(..., description="Owner user ID")
    account_name: str = Field(..., description="Display name")
    profile_id: Optional[str] = Field(None, description="Amazon profile ID")
    entity_id: Optional[str] = Field(None, description="Amazon entity ID")
    marketplaces: List[str] = Field(default_factory=list, description="List of marketplaces")
    last_managed_at: Optional[datetime] = Field(None, description="Last management selection")
    status: str = Field("active", description="Account status")
    account_type: Literal["advertising"] = Field("advertising", description="Account type")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    last_synced_at: Optional[datetime] = Field(None, description="Last sync timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "660e8400-e29b-41d4-a716-446655440001",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "account_name": "My Sponsored Ads Account",
                "profile_id": "123456789",
                "entity_id": "ENTITY123ABC",
                "marketplaces": ["US", "CA", "MX"],
                "last_managed_at": "2025-09-14T15:30:00Z",
                "status": "active",
                "account_type": "advertising",
                "metadata": {
                    "alternateIds": [
                        {"countryCode": "US", "profileId": 123456789},
                        {"countryCode": "CA", "profileId": 987654321}
                    ]
                },
                "last_synced_at": "2025-09-15T10:00:00Z"
            }
        }


class DSPAccountResponse(BaseModel):
    """Response schema for DSP accounts"""
    id: str = Field(..., description="Account UUID")
    user_id: str = Field(..., description="Owner user ID")
    account_name: str = Field(..., description="Display name")
    entity_id: str = Field(..., description="DSP entity ID")
    profile_id: Optional[str] = Field(None, description="DSP profile ID")
    marketplace: str = Field(..., description="Primary marketplace")
    account_type: Literal["dsp"] = Field("dsp", description="Account type")
    advertiser_type: Optional[str] = Field(None, description="Advertiser type (brand/agency)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    last_synced_at: Optional[datetime] = Field(None, description="Last sync timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "770e8400-e29b-41d4-a716-446655440002",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "account_name": "My DSP Account",
                "entity_id": "DSP_ENTITY_456",
                "profile_id": "987654321",
                "marketplace": "US",
                "account_type": "dsp",
                "advertiser_type": "brand",
                "metadata": {
                    "seats": 5,
                    "line_items_count": 23,
                    "access_level": "admin"
                },
                "last_synced_at": "2025-09-15T10:00:00Z"
            }
        }


class AMCAccountResponse(BaseModel):
    """Response schema for AMC accounts/instances"""
    id: str = Field(..., description="Account UUID")
    user_id: str = Field(..., description="Owner user ID")
    instance_name: str = Field(..., description="AMC instance name")
    instance_id: str = Field(..., description="AMC instance ID")
    account_type: Literal["amc"] = Field("amc", description="Account type")
    data_set_id: str = Field(..., description="AMC data set ID")
    status: str = Field("active", description="Instance status")
    associated_accounts: Dict[str, List[Dict[str, str]]] = Field(
        default_factory=dict,
        description="Associated Sponsored Ads and DSP accounts"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    last_synced_at: Optional[datetime] = Field(None, description="Last sync timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "880e8400-e29b-41d4-a716-446655440003",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "instance_name": "My AMC Instance",
                "instance_id": "AMC_INSTANCE_789",
                "account_type": "amc",
                "data_set_id": "dataset_xyz",
                "status": "active",
                "associated_accounts": {
                    "sponsored_ads": [
                        {
                            "account_name": "SP Account 1",
                            "profile_id": "123456789",
                            "entity_id": "ENTITY123ABC"
                        }
                    ],
                    "dsp": [
                        {
                            "account_name": "DSP Account 1",
                            "profile_id": "987654321",
                            "entity_id": "DSP_ENTITY_456"
                        }
                    ]
                },
                "metadata": {
                    "region": "us-east-1",
                    "storage_used_gb": 125.5,
                    "query_credits": 1000
                },
                "last_synced_at": "2025-09-15T10:00:00Z"
            }
        }


class AccountRelationship(BaseModel):
    """Schema for account relationships"""
    parent_account_id: str = Field(..., description="Parent account UUID")
    child_account_id: str = Field(..., description="Child account UUID")
    relationship_type: Literal[
        "sponsored_to_dsp",
        "sponsored_to_amc",
        "dsp_to_amc"
    ] = Field(..., description="Type of relationship")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional relationship data")

    @validator('parent_account_id')
    def validate_not_self_reference(cls, v, values):
        if 'child_account_id' in values and v == values['child_account_id']:
            raise ValueError('Parent and child account IDs cannot be the same')
        return v


class SetManagedRequest(BaseModel):
    """Request to set an account as managed"""
    account_id: str = Field(..., description="Account UUID to mark as managed")

    class Config:
        json_schema_extra = {
            "example": {
                "account_id": "660e8400-e29b-41d4-a716-446655440001"
            }
        }


class SetManagedResponse(BaseModel):
    """Response after setting account as managed"""
    success: bool = Field(..., description="Operation success status")
    account_id: str = Field(..., description="Account UUID")
    last_managed_at: datetime = Field(..., description="New management timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "account_id": "660e8400-e29b-41d4-a716-446655440001",
                "last_managed_at": "2025-09-15T10:00:00Z"
            }
        }


class DSPSeatInfo(BaseModel):
    """Information about a DSP seat on an exchange"""
    exchange_id: str = Field(..., description="Unique identifier of the exchange")
    exchange_name: str = Field(..., description="Name of the exchange")
    deal_creation_id: Optional[str] = Field(None, description="SeatId for buyer identification")
    spend_tracking_id: Optional[str] = Field(None, description="SeatId for buyer tracking")

    class Config:
        json_schema_extra = {
            "example": {
                "exchange_id": "1",
                "exchange_name": "Google Ad Manager",
                "deal_creation_id": "DEAL-ABC-123",
                "spend_tracking_id": "TRACK-XYZ-789"
            }
        }


class DSPAdvertiserSeats(BaseModel):
    """DSP advertiser seats information"""
    advertiser_id: str = Field(..., description="DSP advertiser ID")
    current_seats: List[DSPSeatInfo] = Field(..., description="Current seat allocations")

    class Config:
        json_schema_extra = {
            "example": {
                "advertiser_id": "123456789",
                "current_seats": [
                    {
                        "exchange_id": "1",
                        "exchange_name": "Google Ad Manager",
                        "deal_creation_id": "DEAL-ABC-123",
                        "spend_tracking_id": "TRACK-XYZ-789"
                    }
                ]
            }
        }


class DSPSeatsResponse(BaseModel):
    """Response for DSP Seats API"""
    advertiser_seats: List[DSPAdvertiserSeats] = Field(..., alias="advertiserSeats", description="List of advertiser seats")
    next_token: Optional[str] = Field(None, alias="nextToken", description="Pagination token")
    timestamp: datetime = Field(..., description="Response timestamp")
    cached: bool = Field(False, description="Whether response is from cache")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "advertiserSeats": [
                    {
                        "advertiserId": "123456789",
                        "currentSeats": [
                            {
                                "exchangeId": "1",
                                "exchangeName": "Google Ad Manager",
                                "dealCreationId": "DEAL-ABC-123",
                                "spendTrackingId": "TRACK-XYZ-789"
                            }
                        ]
                    }
                ],
                "nextToken": "eyJsYXN0S2V5IjoiMTIzIn0=",
                "timestamp": "2025-09-16T10:30:00Z",
                "cached": False
            }
        }


class DSPSeatsRefreshRequest(BaseModel):
    """Request to refresh DSP seats data"""
    force: bool = Field(True, description="Force refresh bypassing cache")
    include_sync_log: bool = Field(False, description="Include sync log entry in response")

    class Config:
        json_schema_extra = {
            "example": {
                "force": True,
                "include_sync_log": False
            }
        }


class DSPSeatsRefreshResponse(BaseModel):
    """Response after refreshing DSP seats"""
    success: bool = Field(..., description="Operation success status")
    seats_updated: int = Field(..., description="Number of seats updated")
    last_sync: datetime = Field(..., description="Timestamp of sync")
    sync_log_id: Optional[str] = Field(None, description="Sync log entry ID")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "seats_updated": 5,
                "last_sync": "2025-09-16T10:30:00Z",
                "sync_log_id": "uuid-here"
            }
        }


class DSPSyncHistoryEntry(BaseModel):
    """Entry in DSP seats sync history"""
    id: str = Field(..., description="Sync log ID")
    sync_status: Literal["success", "failed", "partial"] = Field(..., description="Sync status")
    seats_retrieved: int = Field(..., description="Number of seats retrieved")
    exchanges_count: int = Field(..., description="Number of exchanges")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Sync timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "sync-log-uuid",
                "sync_status": "success",
                "seats_retrieved": 5,
                "exchanges_count": 2,
                "error_message": None,
                "created_at": "2025-09-16T10:30:00Z"
            }
        }


class DSPSyncHistoryResponse(BaseModel):
    """Response for DSP seats sync history"""
    sync_history: List[DSPSyncHistoryEntry] = Field(..., description="List of sync history entries")
    total_count: int = Field(..., description="Total number of entries")
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Page offset")

    class Config:
        json_schema_extra = {
            "example": {
                "sync_history": [
                    {
                        "id": "sync-log-uuid",
                        "sync_status": "success",
                        "seats_retrieved": 5,
                        "exchanges_count": 2,
                        "error_message": None,
                        "created_at": "2025-09-16T10:30:00Z"
                    }
                ],
                "total_count": 25,
                "limit": 10,
                "offset": 0
            }
        }


class AccountsSyncRequest(BaseModel):
    """Request to sync accounts from Amazon APIs"""
    account_types: List[AccountType] = Field(
        default_factory=lambda: [AccountType.ADVERTISING, AccountType.DSP, AccountType.AMC],
        description="Account types to sync"
    )
    force_refresh: bool = Field(False, description="Force refresh even if recently synced")

    class Config:
        json_schema_extra = {
            "example": {
                "account_types": ["advertising", "dsp", "amc"],
                "force_refresh": False
            }
        }


class AccountsSyncResponse(BaseModel):
    """Response from account sync operation"""
    sync_id: str = Field(..., description="Sync operation ID")
    status: Literal["in_progress", "completed", "failed"] = Field(..., description="Sync status")
    account_types: List[str] = Field(..., description="Account types being synced")
    started_at: datetime = Field(..., description="Sync start timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "sync_id": "990e8400-e29b-41d4-a716-446655440004",
                "status": "in_progress",
                "account_types": ["advertising", "dsp", "amc"],
                "started_at": "2025-09-15T10:00:00Z"
            }
        }


class AccountsSyncStatus(BaseModel):
    """Status of account sync operation"""
    sync_id: str = Field(..., description="Sync operation ID")
    status: Literal["in_progress", "completed", "failed"] = Field(..., description="Overall status")
    results: Dict[str, Dict[str, Any]] = Field(..., description="Results per account type")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "sync_id": "990e8400-e29b-41d4-a716-446655440004",
                "status": "completed",
                "results": {
                    "advertising": {
                        "status": "success",
                        "accounts_synced": 15,
                        "errors": []
                    },
                    "dsp": {
                        "status": "success",
                        "accounts_synced": 3,
                        "errors": []
                    },
                    "amc": {
                        "status": "no_access",
                        "accounts_synced": 0,
                        "errors": ["User does not have AMC access"]
                    }
                },
                "completed_at": "2025-09-15T10:05:00Z"
            }
        }