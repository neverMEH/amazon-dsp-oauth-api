-- Migration: Add Account Type Support for Multi-Type Account Management
-- Date: 2025-09-15
-- Description: Adds support for distinguishing between Sponsored Ads, DSP, and AMC account types

-- 1. Add new columns to user_accounts table
ALTER TABLE user_accounts
ADD COLUMN IF NOT EXISTS account_type VARCHAR(20) DEFAULT 'advertising',
ADD COLUMN IF NOT EXISTS profile_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS entity_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS last_managed_at TIMESTAMP WITH TIME ZONE;

-- 2. Add check constraint for account_type values
ALTER TABLE user_accounts
DROP CONSTRAINT IF EXISTS user_accounts_account_type_check;

ALTER TABLE user_accounts
ADD CONSTRAINT user_accounts_account_type_check
CHECK (account_type IN ('advertising', 'dsp', 'amc'));

-- 3. Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_user_accounts_account_type
ON user_accounts(account_type);

CREATE INDEX IF NOT EXISTS idx_user_accounts_profile_entity
ON user_accounts(profile_id, entity_id);

CREATE INDEX IF NOT EXISTS idx_user_accounts_last_managed
ON user_accounts(last_managed_at DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_user_accounts_type_user
ON user_accounts(account_type, user_id);

-- 4. Create account_relationships table for tracking AMC associations
CREATE TABLE IF NOT EXISTS account_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_account_id UUID NOT NULL REFERENCES user_accounts(id) ON DELETE CASCADE,
    child_account_id UUID NOT NULL REFERENCES user_accounts(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,

    -- Prevent duplicate relationships
    UNIQUE(parent_account_id, child_account_id, relationship_type),

    -- Prevent self-relationships
    CHECK (parent_account_id != child_account_id),

    -- Valid relationship types
    CHECK (relationship_type IN (
        'sponsored_to_dsp',      -- Sponsored Ads account owns DSP account
        'sponsored_to_amc',      -- Sponsored Ads feeds into AMC
        'dsp_to_amc'            -- DSP feeds into AMC
    ))
);

-- 5. Create indexes for account_relationships table
CREATE INDEX IF NOT EXISTS idx_account_relationships_parent
ON account_relationships(parent_account_id);

CREATE INDEX IF NOT EXISTS idx_account_relationships_child
ON account_relationships(child_account_id);

CREATE INDEX IF NOT EXISTS idx_account_relationships_type
ON account_relationships(relationship_type);

-- 6. Create junction table for AMC instance accounts (many-to-many)
CREATE TABLE IF NOT EXISTS amc_instance_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    amc_account_id UUID NOT NULL REFERENCES user_accounts(id) ON DELETE CASCADE,
    source_account_id UUID NOT NULL REFERENCES user_accounts(id) ON DELETE CASCADE,
    source_type VARCHAR(20) NOT NULL CHECK (source_type IN ('advertising', 'dsp')),
    advertiser_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Prevent duplicates
    UNIQUE(amc_account_id, source_account_id)
);

-- 7. Create indexes for amc_instance_accounts table
CREATE INDEX IF NOT EXISTS idx_amc_instance_accounts_amc
ON amc_instance_accounts(amc_account_id);

CREATE INDEX IF NOT EXISTS idx_amc_instance_accounts_source
ON amc_instance_accounts(source_account_id);

-- 8. Update existing data - set default account_type for existing records
UPDATE user_accounts
SET account_type = 'advertising'
WHERE account_type IS NULL
AND (
    metadata->>'alternateIds' IS NOT NULL
    OR metadata->>'adsAccountId' IS NOT NULL
    OR amazon_account_id LIKE 'ENTITY%'
);

-- 9. Extract profile_id and entity_id from existing metadata if available
UPDATE user_accounts
SET profile_id = COALESCE(
    metadata->>'profileId',
    metadata->'alternateIds'->0->>'profileId'
)
WHERE profile_id IS NULL
AND metadata IS NOT NULL;

UPDATE user_accounts
SET entity_id = COALESCE(
    metadata->>'entityId',
    amazon_account_id
)
WHERE entity_id IS NULL;

-- 10. Create helper functions for account relationships
CREATE OR REPLACE FUNCTION get_account_relationships(account_uuid UUID)
RETURNS TABLE (
    related_account_id UUID,
    account_name VARCHAR(255),
    account_type VARCHAR(20),
    relationship_type VARCHAR(50),
    direction VARCHAR(10)
) AS $$
BEGIN
    RETURN QUERY
    -- Get child accounts
    SELECT
        ua.id,
        ua.account_name,
        ua.account_type,
        ar.relationship_type,
        'child'::VARCHAR(10) as direction
    FROM account_relationships ar
    JOIN user_accounts ua ON ua.id = ar.child_account_id
    WHERE ar.parent_account_id = account_uuid

    UNION ALL

    -- Get parent accounts
    SELECT
        ua.id,
        ua.account_name,
        ua.account_type,
        ar.relationship_type,
        'parent'::VARCHAR(10) as direction
    FROM account_relationships ar
    JOIN user_accounts ua ON ua.id = ar.parent_account_id
    WHERE ar.child_account_id = account_uuid;
END;
$$ LANGUAGE plpgsql;

-- 11. Create function to get AMC linked accounts
CREATE OR REPLACE FUNCTION get_amc_linked_accounts(amc_uuid UUID)
RETURNS TABLE (
    account_id UUID,
    account_name VARCHAR(255),
    account_type VARCHAR(20),
    profile_id VARCHAR(255),
    entity_id VARCHAR(255),
    advertiser_id VARCHAR(255)
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ua.id,
        ua.account_name,
        ua.account_type,
        ua.profile_id,
        ua.entity_id,
        aia.advertiser_id
    FROM amc_instance_accounts aia
    JOIN user_accounts ua ON ua.id = aia.source_account_id
    WHERE aia.amc_account_id = amc_uuid
    ORDER BY ua.account_type, ua.account_name;
END;
$$ LANGUAGE plpgsql;

-- 12. Update metadata structure documentation
COMMENT ON COLUMN user_accounts.account_type IS 'Type of Amazon account: advertising (Sponsored Ads), dsp, or amc';
COMMENT ON COLUMN user_accounts.profile_id IS 'Amazon profile ID for the account';
COMMENT ON COLUMN user_accounts.entity_id IS 'Amazon entity ID for the account';
COMMENT ON COLUMN user_accounts.last_managed_at IS 'Timestamp when account was last selected for management';

COMMENT ON TABLE account_relationships IS 'Tracks parent-child relationships between different account types';
COMMENT ON TABLE amc_instance_accounts IS 'Maps AMC instances to their data source accounts (Sponsored Ads and DSP)';

-- 13. Create RLS policies for new tables
ALTER TABLE account_relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE amc_instance_accounts ENABLE ROW LEVEL SECURITY;

-- Policy for account_relationships
CREATE POLICY account_relationships_user_access ON account_relationships
    FOR ALL USING (
        parent_account_id IN (
            SELECT id FROM user_accounts WHERE user_id = auth.uid()
        )
        OR child_account_id IN (
            SELECT id FROM user_accounts WHERE user_id = auth.uid()
        )
    );

-- Policy for amc_instance_accounts
CREATE POLICY amc_instance_accounts_user_access ON amc_instance_accounts
    FOR ALL USING (
        amc_account_id IN (
            SELECT id FROM user_accounts WHERE user_id = auth.uid()
        )
        OR source_account_id IN (
            SELECT id FROM user_accounts WHERE user_id = auth.uid()
        )
    );

-- 14. Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON account_relationships TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON amc_instance_accounts TO authenticated;

-- 15. Create trigger to update last_managed_at timestamp
CREATE OR REPLACE FUNCTION update_last_managed_at()
RETURNS TRIGGER AS $$
BEGIN
    -- Only update if explicitly triggered by management action
    IF NEW.metadata ? 'manage_action' THEN
        NEW.last_managed_at = CURRENT_TIMESTAMP;
        -- Remove the trigger flag from metadata
        NEW.metadata = NEW.metadata - 'manage_action';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_last_managed ON user_accounts;
CREATE TRIGGER trigger_update_last_managed
    BEFORE UPDATE ON user_accounts
    FOR EACH ROW
    EXECUTE FUNCTION update_last_managed_at();

-- 16. Success message
DO $$
BEGIN
    RAISE NOTICE 'Account type support migration completed successfully';
    RAISE NOTICE 'Added columns: account_type, profile_id, entity_id, last_managed_at';
    RAISE NOTICE 'Created tables: account_relationships, amc_instance_accounts';
    RAISE NOTICE 'Created helper functions for relationship queries';
END $$;