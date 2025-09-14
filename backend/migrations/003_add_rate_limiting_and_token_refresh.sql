-- Migration: Add rate limiting tracking and token refresh enhancements
-- Date: 2025-09-14
-- Description: Adds rate limit tracking, account sync history, and token refresh management

-- 1. Enhancements to oauth_tokens table
ALTER TABLE oauth_tokens
ADD COLUMN IF NOT EXISTS refresh_failure_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_refresh_error TEXT,
ADD COLUMN IF NOT EXISTS proactive_refresh_enabled BOOLEAN DEFAULT TRUE;

-- Add index for efficient token refresh queries
CREATE INDEX IF NOT EXISTS idx_oauth_tokens_expires_at
ON oauth_tokens(expires_at)
WHERE proactive_refresh_enabled = TRUE;

-- 2. Enhancements to user_accounts table
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

-- 3. Create account_sync_history table
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

-- 4. Create rate_limit_tracking table
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

-- 5. Initialize data for existing records
UPDATE user_accounts
SET sync_status = CASE
    WHEN status = 'active' THEN 'completed'
    WHEN status = 'pending' THEN 'pending'
    ELSE 'failed'
END
WHERE sync_status IS NULL;

UPDATE user_accounts
SET next_sync_at = NOW() + INTERVAL '1 hour'
WHERE next_sync_at IS NULL;

-- 6. Add check constraints for data integrity
ALTER TABLE account_sync_history
ADD CONSTRAINT chk_sync_status CHECK (sync_status IN ('started', 'success', 'failed'));

ALTER TABLE account_sync_history
ADD CONSTRAINT chk_sync_type CHECK (sync_type IN ('manual', 'scheduled', 'webhook'));

ALTER TABLE user_accounts
ADD CONSTRAINT chk_sync_status_values CHECK (sync_status IN ('pending', 'in_progress', 'completed', 'failed'));

-- 7. Add RLS policies (if using Supabase)
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

ALTER TABLE rate_limit_tracking ENABLE ROW LEVEL SECURITY;

CREATE POLICY rate_limit_tracking_policy ON rate_limit_tracking
FOR ALL
TO authenticated
USING (user_id = auth.uid());