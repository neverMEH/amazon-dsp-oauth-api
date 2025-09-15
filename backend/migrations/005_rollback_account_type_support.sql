-- Rollback Migration: Remove Account Type Support
-- Date: 2025-09-15
-- Description: Rollback changes from 005_add_account_type_support.sql

-- 1. Drop triggers
DROP TRIGGER IF EXISTS trigger_update_last_managed ON user_accounts;
DROP FUNCTION IF EXISTS update_last_managed_at();

-- 2. Drop RLS policies
DROP POLICY IF EXISTS account_relationships_user_access ON account_relationships;
DROP POLICY IF EXISTS amc_instance_accounts_user_access ON amc_instance_accounts;

-- 3. Drop helper functions
DROP FUNCTION IF EXISTS get_account_relationships(UUID);
DROP FUNCTION IF EXISTS get_amc_linked_accounts(UUID);

-- 4. Drop indexes from new tables
DROP INDEX IF EXISTS idx_account_relationships_parent;
DROP INDEX IF EXISTS idx_account_relationships_child;
DROP INDEX IF EXISTS idx_account_relationships_type;
DROP INDEX IF EXISTS idx_amc_instance_accounts_amc;
DROP INDEX IF EXISTS idx_amc_instance_accounts_source;

-- 5. Drop new tables
DROP TABLE IF EXISTS amc_instance_accounts;
DROP TABLE IF EXISTS account_relationships;

-- 6. Drop indexes from user_accounts
DROP INDEX IF EXISTS idx_user_accounts_account_type;
DROP INDEX IF EXISTS idx_user_accounts_profile_entity;
DROP INDEX IF EXISTS idx_user_accounts_last_managed;
DROP INDEX IF EXISTS idx_user_accounts_type_user;

-- 7. Drop constraints
ALTER TABLE user_accounts
DROP CONSTRAINT IF EXISTS user_accounts_account_type_check;

-- 8. Drop columns from user_accounts
ALTER TABLE user_accounts
DROP COLUMN IF EXISTS account_type,
DROP COLUMN IF EXISTS profile_id,
DROP COLUMN IF EXISTS entity_id,
DROP COLUMN IF EXISTS last_managed_at;

-- 9. Success message
DO $$
BEGIN
    RAISE NOTICE 'Account type support rollback completed successfully';
    RAISE NOTICE 'Removed columns: account_type, profile_id, entity_id, last_managed_at';
    RAISE NOTICE 'Dropped tables: account_relationships, amc_instance_accounts';
    RAISE NOTICE 'Removed helper functions and triggers';
END $$;