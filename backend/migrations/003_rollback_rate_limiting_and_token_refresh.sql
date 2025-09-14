-- Rollback Migration: Remove rate limiting tracking and token refresh enhancements
-- Date: 2025-09-14

-- 1. Drop RLS policies
DROP POLICY IF EXISTS rate_limit_tracking_policy ON rate_limit_tracking;
DROP POLICY IF EXISTS account_sync_history_policy ON account_sync_history;

-- 2. Drop new tables
DROP TABLE IF EXISTS rate_limit_tracking CASCADE;
DROP TABLE IF EXISTS account_sync_history CASCADE;

-- 3. Remove check constraints from user_accounts
ALTER TABLE user_accounts DROP CONSTRAINT IF EXISTS chk_sync_status_values;

-- 4. Remove indexes from user_accounts
DROP INDEX IF EXISTS idx_user_accounts_metadata;
DROP INDEX IF EXISTS idx_user_accounts_user_amazon;

-- 5. Remove columns from user_accounts
ALTER TABLE user_accounts
DROP COLUMN IF EXISTS sync_status,
DROP COLUMN IF EXISTS sync_error_message,
DROP COLUMN IF EXISTS sync_retry_count,
DROP COLUMN IF EXISTS next_sync_at;

-- 6. Remove index from oauth_tokens
DROP INDEX IF EXISTS idx_oauth_tokens_expires_at;

-- 7. Remove columns from oauth_tokens
ALTER TABLE oauth_tokens
DROP COLUMN IF EXISTS refresh_failure_count,
DROP COLUMN IF EXISTS last_refresh_error,
DROP COLUMN IF EXISTS proactive_refresh_enabled;