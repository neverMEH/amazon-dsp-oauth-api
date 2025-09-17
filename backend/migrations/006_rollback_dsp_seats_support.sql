-- Rollback Migration: Remove DSP Seats Support
-- Date: 2025-09-17
-- Description: Rolls back DSP seats tracking and synchronization logging tables

-- 1. Drop indexes
DROP INDEX IF EXISTS idx_user_accounts_seats_metadata;
DROP INDEX IF EXISTS idx_dsp_seats_sync_log_advertiser_created;
DROP INDEX IF EXISTS idx_dsp_seats_sync_log_created_at;
DROP INDEX IF EXISTS idx_dsp_seats_sync_log_status;
DROP INDEX IF EXISTS idx_dsp_seats_sync_log_user_account;
DROP INDEX IF EXISTS idx_dsp_seats_sync_log_advertiser;

-- 2. Drop dsp_seats_sync_log table
DROP TABLE IF EXISTS dsp_seats_sync_log;

-- 3. Remove seats_metadata column from user_accounts
ALTER TABLE user_accounts
DROP COLUMN IF EXISTS seats_metadata;