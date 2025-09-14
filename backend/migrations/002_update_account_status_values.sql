-- Migration: Update user_accounts status constraint for API v3.0
-- Description: Updates status constraint to include new Amazon Ads API v3.0 status values
-- Date: 2025-01-14

-- Drop existing constraint
ALTER TABLE user_accounts
DROP CONSTRAINT IF EXISTS user_accounts_status_check;

-- Add new constraint with updated status values
-- Mapping: CREATED->active, DISABLED->disabled, PARTIALLY_CREATED->partial, PENDING->pending
ALTER TABLE user_accounts
ADD CONSTRAINT user_accounts_status_check
CHECK (status IN ('active', 'inactive', 'suspended', 'pending', 'disabled', 'partial', 'disconnected'));

-- Update any existing records with old status values to new ones
UPDATE user_accounts
SET status = 'disabled'
WHERE status = 'suspended';

-- Add comment to metadata column explaining new structure
COMMENT ON COLUMN user_accounts.metadata IS 'JSONB field storing account metadata including:
- alternate_ids: Array of {countryCode, entityId, profileId}
- country_codes: Array of supported country codes
- errors: Object mapping country codes to error arrays
- profile_id: Primary profile ID
- country_code: Primary country code
- api_status: Original status from Amazon API (CREATED, DISABLED, PARTIALLY_CREATED, PENDING)';