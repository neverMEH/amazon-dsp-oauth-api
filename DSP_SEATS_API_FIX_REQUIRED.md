# DSP Seats API Fix Required

## Issue Found
The DSP Seats API is returning an error when called:
```
NO_PARENT_ENTITY_ID_OR_ADVERTISER_ID_FOR_ADVERTISER_CONTEXT
When calling as an advertiser 'parentEntityId' header must be provided along with 'Amazon-Ads-AccountId', with advertiserId
```

## Current Implementation
File: `backend/app/services/dsp_amc_service.py`
Lines: 377-383

```python
headers = {
    "Authorization": f"Bearer {access_token}",
    "Amazon-Advertising-API-ClientId": settings.amazon_client_id,
    "Amazon-Ads-AccountId": advertiser_id,  # REQUIRED
    "Content-Type": "application/json",
    "Accept": "application/json"
}
```

## Required Fix
The API requires an additional header `parentEntityId` when calling from an advertiser context. This needs to be added to the headers.

## Possible Solutions

### Option 1: Add Parent Entity ID from DSP Advertiser Response
The DSP advertiser response might contain a parent entity ID that we need to store and use.

### Option 2: Use Profile-Based Context
Instead of advertiser context, use profile-based context by:
- Using the profile ID in the scope header
- Potentially different endpoint or request structure

### Option 3: Get Parent Entity from Account Mapping
The advertising accounts response includes `entityId` fields in the `alternateIds` array. These might be the parent entity IDs needed.

Example from sync test:
```json
{
  "alternateIds": [
    {
      "countryCode": "US",
      "profileId": 3810822089931808
    },
    {
      "countryCode": "US",
      "entityId": "ENTITY2SE4T62ZTC23S"  // <-- This might be the parentEntityId
    }
  ]
}
```

## Recommended Action
1. Check if the entityId from the advertising accounts can be used as parentEntityId
2. Modify the DSP service to:
   - Accept an optional parent_entity_id parameter
   - Add the parentEntityId header when provided
   - Map advertisers to their parent entities

## Code Change Needed
```python
# In list_advertiser_seats method
headers = {
    "Authorization": f"Bearer {access_token}",
    "Amazon-Advertising-API-ClientId": settings.amazon_client_id,
    "Amazon-Ads-AccountId": advertiser_id,
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# Add parent entity if available
if parent_entity_id:
    headers["parentEntityId"] = parent_entity_id
```

## Testing Plan
1. Find the correct parent entity ID for an advertiser
2. Test the API call with the parentEntityId header
3. Verify seats data is returned successfully
4. Update sync process to populate seats_metadata

---

*This fix is required to enable DSP seats data synchronization*