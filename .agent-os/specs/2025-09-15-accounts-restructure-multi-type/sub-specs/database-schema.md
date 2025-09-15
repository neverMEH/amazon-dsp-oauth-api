# Database Schema

This is the database schema implementation for the spec detailed in @.agent-os/specs/2025-09-15-accounts-restructure-multi-type/spec.md

> Created: 2025-09-15
> Version: 1.0.0

## Schema Changes

### Modified Tables

#### user_accounts (Enhanced)
```sql
-- Add account_type column to distinguish between account types
ALTER TABLE user_accounts
ADD COLUMN account_type VARCHAR(20) DEFAULT 'advertising'
CHECK (account_type IN ('advertising', 'dsp', 'amc'));

-- Add last_managed_at to track when account was last selected for management
ALTER TABLE user_accounts
ADD COLUMN last_managed_at TIMESTAMP WITH TIME ZONE;

-- Add profile and entity ID columns for easier querying
ALTER TABLE user_accounts
ADD COLUMN profile_id VARCHAR(255),
ADD COLUMN entity_id VARCHAR(255);

-- Add indexes for efficient filtering and sorting
CREATE INDEX idx_user_accounts_type ON user_accounts(account_type, user_id);
CREATE INDEX idx_user_accounts_last_managed ON user_accounts(last_managed_at DESC);
CREATE INDEX idx_user_accounts_profile_entity ON user_accounts(profile_id, entity_id);

-- Update metadata column to support type-specific fields
COMMENT ON COLUMN user_accounts.metadata IS 'JSONB field containing type-specific data:
- advertising: {alternateIds, countryCodes, marketplaces, campaigns_count}
- dsp: {marketplaces, advertiser_type, line_items_count, access_level}
- amc: {data_set_id, instance_id, storage_used, query_credits, associated_accounts}';
```

### New Tables

#### account_relationships
```sql
CREATE TABLE account_relationships (
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
        'dsp_to_amc'           -- DSP feeds into AMC
    ))
);

-- Indexes for efficient queries
CREATE INDEX idx_account_relationships_parent ON account_relationships(parent_account_id);
CREATE INDEX idx_account_relationships_child ON account_relationships(child_account_id);
CREATE INDEX idx_account_relationships_type ON account_relationships(relationship_type);
```

#### amc_instance_accounts (Junction Table)
```sql
-- Many-to-many relationship for AMC instances and their data sources
CREATE TABLE amc_instance_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    amc_account_id UUID NOT NULL REFERENCES user_accounts(id) ON DELETE CASCADE,
    source_account_id UUID NOT NULL REFERENCES user_accounts(id) ON DELETE CASCADE,
    source_type VARCHAR(20) NOT NULL CHECK (source_type IN ('advertising', 'dsp')),
    advertiser_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Prevent duplicates
    UNIQUE(amc_account_id, source_account_id)
);

CREATE INDEX idx_amc_instance_accounts_amc ON amc_instance_accounts(amc_account_id);
CREATE INDEX idx_amc_instance_accounts_source ON amc_instance_accounts(source_account_id);
```

## Database Functions

### get_account_relationships
```sql
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
```

### get_amc_linked_accounts
```sql
CREATE OR REPLACE FUNCTION get_amc_linked_accounts(amc_uuid UUID)
RETURNS TABLE (
    account_id UUID,
    account_name VARCHAR(255),
    account_type VARCHAR(20),
    advertiser_id VARCHAR(255)
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ua.id,
        ua.account_name,
        ua.account_type,
        aia.advertiser_id
    FROM amc_instance_accounts aia
    JOIN user_accounts ua ON ua.id = aia.source_account_id
    WHERE aia.amc_account_id = amc_uuid
    ORDER BY ua.account_type, ua.account_name;
END;
$$ LANGUAGE plpgsql;
```

## Migration Script

```sql
-- Migration: Add multi-account-type support
-- Version: 2025_09_15_accounts_restructure

BEGIN;

-- 1. Add account_type to existing accounts (default to 'advertising')
ALTER TABLE user_accounts
ADD COLUMN IF NOT EXISTS account_type VARCHAR(20) DEFAULT 'advertising';

-- 2. Update existing accounts based on metadata
UPDATE user_accounts
SET account_type = 'advertising'
WHERE metadata->>'account_source' = 'amazon_ads'
   OR metadata->>'alternateIds' IS NOT NULL;

-- 3. Create new tables
CREATE TABLE IF NOT EXISTS account_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_account_id UUID NOT NULL REFERENCES user_accounts(id) ON DELETE CASCADE,
    child_account_id UUID NOT NULL REFERENCES user_accounts(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,

    UNIQUE(parent_account_id, child_account_id, relationship_type),
    CHECK (parent_account_id != child_account_id),
    CHECK (relationship_type IN (
        'sponsored_to_dsp',
        'sponsored_to_amc',
        'dsp_to_amc'
    ))
);

CREATE TABLE IF NOT EXISTS amc_instance_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    amc_account_id UUID NOT NULL REFERENCES user_accounts(id) ON DELETE CASCADE,
    source_account_id UUID NOT NULL REFERENCES user_accounts(id) ON DELETE CASCADE,
    source_type VARCHAR(20) NOT NULL CHECK (source_type IN ('advertising', 'dsp')),
    advertiser_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(amc_account_id, source_account_id)
);

-- 4. Create indexes
CREATE INDEX IF NOT EXISTS idx_user_accounts_type ON user_accounts(account_type, user_id);
CREATE INDEX IF NOT EXISTS idx_account_relationships_parent ON account_relationships(parent_account_id);
CREATE INDEX IF NOT EXISTS idx_account_relationships_child ON account_relationships(child_account_id);
CREATE INDEX IF NOT EXISTS idx_account_relationships_type ON account_relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_amc_instance_accounts_amc ON amc_instance_accounts(amc_account_id);
CREATE INDEX IF NOT EXISTS idx_amc_instance_accounts_source ON amc_instance_accounts(source_account_id);

-- 5. Create helper functions
-- (Function definitions would be included here)

COMMIT;
```

## Rationale

- **account_type column**: Enables efficient filtering of accounts by type without complex JSON queries
- **account_relationships table**: Provides flexible parent-child relationships between different account types
- **amc_instance_accounts**: Specifically tracks which accounts feed data into AMC instances
- **Indexes**: Optimized for common query patterns (filtering by type, finding relationships)
- **Helper functions**: Simplify complex relationship queries in application code
- **JSONB metadata**: Maintains flexibility for type-specific fields without schema changes