-- Rollback Migration: Remove user authentication tables
-- Description: Rolls back the user authentication tables and related changes
-- Date: 2025-01-13

-- Drop triggers
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
DROP TRIGGER IF EXISTS ensure_single_default ON user_accounts;

-- Drop functions
DROP FUNCTION IF EXISTS update_updated_at_column();
DROP FUNCTION IF EXISTS ensure_single_default_account();

-- Drop RLS policies
DROP POLICY IF EXISTS users_select_own ON users;
DROP POLICY IF EXISTS users_update_own ON users;
DROP POLICY IF EXISTS users_insert_own ON users;
DROP POLICY IF EXISTS user_accounts_all_own ON user_accounts;

-- Remove columns from oauth_tokens if they exist
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'oauth_tokens'
    ) THEN
        ALTER TABLE oauth_tokens 
        DROP COLUMN IF EXISTS user_id,
        DROP COLUMN IF EXISTS user_account_id;
    END IF;
END $$;

-- Drop indexes
DROP INDEX IF EXISTS idx_oauth_tokens_user_id;
DROP INDEX IF EXISTS idx_oauth_tokens_user_account_id;
DROP INDEX IF EXISTS idx_user_accounts_user_id;
DROP INDEX IF EXISTS idx_user_accounts_status;
DROP INDEX IF EXISTS idx_user_accounts_amazon_id;
DROP INDEX IF EXISTS idx_users_clerk_user_id;
DROP INDEX IF EXISTS idx_users_email;

-- Drop tables (order matters due to foreign keys)
DROP TABLE IF EXISTS user_accounts;
DROP TABLE IF EXISTS users;

-- Revoke permissions if app_user role exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
        REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM app_user;
        REVOKE USAGE ON ALL SEQUENCES IN SCHEMA public FROM app_user;
    END IF;
END $$;