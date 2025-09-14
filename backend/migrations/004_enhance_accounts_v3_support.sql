-- Migration: Enhanced account storage for Amazon Ads API v3.0
-- Date: 2025-09-14
-- Description: Add indexes and constraints for v3.0 account data structure

-- Add indexes for improved query performance on user_accounts table
CREATE INDEX IF NOT EXISTS idx_user_accounts_amazon_account_id
    ON user_accounts(amazon_account_id);

CREATE INDEX IF NOT EXISTS idx_user_accounts_status
    ON user_accounts(status);

CREATE INDEX IF NOT EXISTS idx_user_accounts_last_synced
    ON user_accounts(last_synced_at);

-- Add index for JSONB metadata queries
CREATE INDEX IF NOT EXISTS idx_user_accounts_metadata
    ON user_accounts USING GIN (metadata);

-- Add specific indexes for common metadata queries
CREATE INDEX IF NOT EXISTS idx_user_accounts_metadata_profile_id
    ON user_accounts ((metadata->>'profile_id'));

CREATE INDEX IF NOT EXISTS idx_user_accounts_metadata_country_code
    ON user_accounts ((metadata->>'country_code'));

CREATE INDEX IF NOT EXISTS idx_user_accounts_metadata_api_status
    ON user_accounts ((metadata->>'api_status'));

-- Add composite index for user queries
CREATE INDEX IF NOT EXISTS idx_user_accounts_user_status
    ON user_accounts(user_id, status);

-- Update status check constraint to include new values
ALTER TABLE user_accounts
    DROP CONSTRAINT IF EXISTS user_accounts_status_check;

ALTER TABLE user_accounts
    ADD CONSTRAINT user_accounts_status_check
    CHECK (status IN ('active', 'inactive', 'suspended', 'pending', 'partial', 'disabled', 'disconnected'));

-- Add columns for sync management if they don't exist
DO $$
BEGIN
    -- Add sync_status column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_accounts'
        AND column_name = 'sync_status'
    ) THEN
        ALTER TABLE user_accounts
        ADD COLUMN sync_status VARCHAR(50) DEFAULT 'pending'
        CHECK (sync_status IN ('pending', 'in_progress', 'completed', 'failed'));
    END IF;

    -- Add sync_error_message column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_accounts'
        AND column_name = 'sync_error_message'
    ) THEN
        ALTER TABLE user_accounts
        ADD COLUMN sync_error_message TEXT;
    END IF;

    -- Add sync_retry_count column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_accounts'
        AND column_name = 'sync_retry_count'
    ) THEN
        ALTER TABLE user_accounts
        ADD COLUMN sync_retry_count INTEGER DEFAULT 0;
    END IF;

    -- Add next_sync_at column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_accounts'
        AND column_name = 'next_sync_at'
    ) THEN
        ALTER TABLE user_accounts
        ADD COLUMN next_sync_at TIMESTAMP WITH TIME ZONE;
    END IF;
END $$;

-- Create or update account_sync_history table
CREATE TABLE IF NOT EXISTS account_sync_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_account_id UUID REFERENCES user_accounts(id) ON DELETE CASCADE,
    sync_type VARCHAR(50) NOT NULL CHECK (sync_type IN ('manual', 'scheduled', 'webhook')),
    sync_status VARCHAR(50) NOT NULL CHECK (sync_status IN ('started', 'success', 'failed', 'partial')),
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    accounts_synced INTEGER DEFAULT 0,
    accounts_failed INTEGER DEFAULT 0,
    error_details JSONB,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes for account_sync_history
CREATE INDEX IF NOT EXISTS idx_sync_history_user_account
    ON account_sync_history(user_account_id);

CREATE INDEX IF NOT EXISTS idx_sync_history_status
    ON account_sync_history(sync_status);

CREATE INDEX IF NOT EXISTS idx_sync_history_created
    ON account_sync_history(created_at DESC);

-- Create function to get profile IDs by country code
CREATE OR REPLACE FUNCTION get_profile_ids_by_country(
    p_user_id UUID,
    p_country_code VARCHAR(2)
) RETURNS TABLE (
    account_id UUID,
    account_name VARCHAR(255),
    amazon_account_id VARCHAR(255),
    profile_id BIGINT,
    entity_id TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ua.id,
        ua.account_name,
        ua.amazon_account_id,
        (alt_id->>'profileId')::BIGINT as profile_id,
        alt_id->>'entityId' as entity_id
    FROM
        user_accounts ua,
        jsonb_array_elements(ua.metadata->'alternate_ids') as alt_id
    WHERE
        ua.user_id = p_user_id
        AND alt_id->>'countryCode' = p_country_code
        AND ua.status = 'active';
END;
$$ LANGUAGE plpgsql;

-- Create function to get accounts with errors
CREATE OR REPLACE FUNCTION get_accounts_with_errors(
    p_user_id UUID
) RETURNS TABLE (
    account_id UUID,
    account_name VARCHAR(255),
    amazon_account_id VARCHAR(255),
    status VARCHAR(50),
    error_countries TEXT[],
    error_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ua.id,
        ua.account_name,
        ua.amazon_account_id,
        ua.status,
        ARRAY(SELECT jsonb_object_keys(ua.metadata->'errors')) as error_countries,
        jsonb_array_length(ua.metadata->'errors') as error_count
    FROM
        user_accounts ua
    WHERE
        ua.user_id = p_user_id
        AND jsonb_typeof(ua.metadata->'errors') = 'object'
        AND ua.metadata->'errors' != '{}'::jsonb;
END;
$$ LANGUAGE plpgsql;

-- Add RLS policies if not exists
ALTER TABLE user_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE account_sync_history ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for user_accounts
DO $$
BEGIN
    -- Drop existing policies if they exist
    DROP POLICY IF EXISTS "Users can view their own accounts" ON user_accounts;
    DROP POLICY IF EXISTS "Users can update their own accounts" ON user_accounts;
    DROP POLICY IF EXISTS "Users can insert their own accounts" ON user_accounts;
    DROP POLICY IF EXISTS "Users can delete their own accounts" ON user_accounts;

    -- Create new policies
    CREATE POLICY "Users can view their own accounts"
        ON user_accounts FOR SELECT
        USING (auth.uid()::text = (SELECT clerk_user_id FROM users WHERE id = user_id));

    CREATE POLICY "Users can update their own accounts"
        ON user_accounts FOR UPDATE
        USING (auth.uid()::text = (SELECT clerk_user_id FROM users WHERE id = user_id));

    CREATE POLICY "Users can insert their own accounts"
        ON user_accounts FOR INSERT
        WITH CHECK (auth.uid()::text = (SELECT clerk_user_id FROM users WHERE id = user_id));

    CREATE POLICY "Users can delete their own accounts"
        ON user_accounts FOR DELETE
        USING (auth.uid()::text = (SELECT clerk_user_id FROM users WHERE id = user_id));
END $$;

-- Create RLS policies for account_sync_history
DO $$
BEGIN
    -- Drop existing policies if they exist
    DROP POLICY IF EXISTS "Users can view their sync history" ON account_sync_history;

    -- Create new policy
    CREATE POLICY "Users can view their sync history"
        ON account_sync_history FOR SELECT
        USING (
            user_account_id IN (
                SELECT id FROM user_accounts
                WHERE user_id IN (
                    SELECT id FROM users
                    WHERE clerk_user_id = auth.uid()::text
                )
            )
        );
END $$;

-- Update existing records to set sync_status if null
UPDATE user_accounts
SET sync_status = 'completed'
WHERE sync_status IS NULL AND last_synced_at IS NOT NULL;

UPDATE user_accounts
SET sync_status = 'pending'
WHERE sync_status IS NULL AND last_synced_at IS NULL;

-- Add comment to table for documentation
COMMENT ON TABLE user_accounts IS 'Stores Amazon Advertising account connections with v3.0 API support';
COMMENT ON COLUMN user_accounts.metadata IS 'JSONB field storing alternateIds, countryCodes, errors, and profile mappings from API v3.0';
COMMENT ON COLUMN user_accounts.amazon_account_id IS 'Maps to adsAccountId from Amazon Ads API v3.0';

-- Grant necessary permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON user_accounts TO authenticated;
GRANT SELECT ON account_sync_history TO authenticated;
GRANT EXECUTE ON FUNCTION get_profile_ids_by_country TO authenticated;
GRANT EXECUTE ON FUNCTION get_accounts_with_errors TO authenticated;