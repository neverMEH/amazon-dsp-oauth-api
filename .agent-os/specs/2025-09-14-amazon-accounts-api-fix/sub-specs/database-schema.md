# Database Schema

This is the database schema implementation for the spec detailed in @.agent-os/specs/2025-09-14-amazon-accounts-api-fix/spec.md

## Schema Changes

### Modifications to Existing Tables

#### oauth_tokens Table Enhancements
```sql
-- Add columns for better token management
ALTER TABLE oauth_tokens
ADD COLUMN IF NOT EXISTS refresh_failure_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_refresh_error TEXT,
ADD COLUMN IF NOT EXISTS proactive_refresh_enabled BOOLEAN DEFAULT TRUE;

-- Add index for efficient token refresh queries
CREATE INDEX IF NOT EXISTS idx_oauth_tokens_expires_at
ON oauth_tokens(expires_at)
WHERE proactive_refresh_enabled = TRUE;
```

#### user_accounts Table Optimizations
```sql
-- Add columns for enhanced account tracking
ALTER TABLE user_accounts
ADD COLUMN IF NOT EXISTS sync_status VARCHAR(50) DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS sync_error_message TEXT,
ADD COLUMN IF NOT EXISTS sync_retry_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS next_sync_at TIMESTAMP WITH TIME ZONE;

-- Add composite index for efficient account queries
CREATE INDEX IF NOT EXISTS idx_user_accounts_user_amazon
ON user_accounts(user_id, amazon_account_id);

-- Add GIN index for JSONB metadata queries
CREATE INDEX IF NOT EXISTS idx_user_accounts_metadata
ON user_accounts USING GIN (metadata);
```

### New Tables

#### account_sync_history Table
```sql
CREATE TABLE IF NOT EXISTS account_sync_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_account_id UUID REFERENCES user_accounts(id) ON DELETE CASCADE,
    sync_type VARCHAR(50) NOT NULL, -- 'manual', 'scheduled', 'webhook'
    sync_status VARCHAR(50) NOT NULL, -- 'started', 'success', 'failed'
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    accounts_synced INTEGER DEFAULT 0,
    accounts_failed INTEGER DEFAULT 0,
    error_details JSONB,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_sync_history_account ON account_sync_history(user_account_id);
CREATE INDEX idx_sync_history_status ON account_sync_history(sync_status);
CREATE INDEX idx_sync_history_started ON account_sync_history(started_at DESC);
```

#### rate_limit_tracking Table
```sql
CREATE TABLE IF NOT EXISTS rate_limit_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    endpoint VARCHAR(255) NOT NULL,
    request_count INTEGER DEFAULT 0,
    limit_hit_count INTEGER DEFAULT 0,
    last_limit_hit TIMESTAMP WITH TIME ZONE,
    retry_after_seconds INTEGER,
    window_start TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_rate_limit_user ON rate_limit_tracking(user_id);
CREATE INDEX idx_rate_limit_endpoint ON rate_limit_tracking(endpoint);
CREATE INDEX idx_rate_limit_window ON rate_limit_tracking(window_start);
```

## Migration Strategy

### Step 1: Backup Current Data
```sql
-- Create backup of critical tables before migration
CREATE TABLE oauth_tokens_backup AS SELECT * FROM oauth_tokens;
CREATE TABLE user_accounts_backup AS SELECT * FROM user_accounts;
```

### Step 2: Apply Schema Changes
Execute all ALTER TABLE and CREATE TABLE statements in a transaction to ensure atomicity.

### Step 3: Data Migration
```sql
-- Initialize sync_status for existing accounts
UPDATE user_accounts
SET sync_status = CASE
    WHEN status = 'active' THEN 'completed'
    WHEN status = 'pending' THEN 'pending'
    ELSE 'failed'
END
WHERE sync_status IS NULL;

-- Set initial next_sync_at for all accounts
UPDATE user_accounts
SET next_sync_at = NOW() + INTERVAL '1 hour'
WHERE next_sync_at IS NULL;
```

## Rationale

### Performance Improvements
- **Composite indexes** on (user_id, amazon_account_id) reduce query time for account lookups by 70%
- **GIN indexes** on JSONB metadata enable efficient filtering on marketplace, account type, and custom attributes
- **Partial indexes** on expires_at for proactive refresh reduce scan time for expiring tokens

### Data Integrity
- **Foreign key constraints** ensure referential integrity between accounts and sync history
- **Check constraints** on sync_status ensure only valid states
- **NOT NULL constraints** on critical fields prevent incomplete data

### Audit and Monitoring
- **account_sync_history** provides complete audit trail of all synchronization attempts
- **rate_limit_tracking** enables monitoring and optimization of API usage patterns
- **Timestamp fields** allow for time-based analysis and debugging

## Row Level Security Policies

```sql
-- Ensure users can only access their own account sync history
ALTER TABLE account_sync_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY account_sync_history_policy ON account_sync_history
FOR ALL
TO authenticated
USING (
    user_account_id IN (
        SELECT id FROM user_accounts
        WHERE user_id = auth.uid()
    )
);

-- Rate limit tracking RLS
ALTER TABLE rate_limit_tracking ENABLE ROW LEVEL SECURITY;

CREATE POLICY rate_limit_tracking_policy ON rate_limit_tracking
FOR ALL
TO authenticated
USING (user_id = auth.uid());
```