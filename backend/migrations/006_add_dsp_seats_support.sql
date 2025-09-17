-- Migration: Add DSP Seats Support
-- Date: 2025-09-17
-- Description: Adds database support for DSP seats tracking and synchronization logging

-- 1. Add seats_metadata column to user_accounts table for storing DSP seat information
ALTER TABLE user_accounts
ADD COLUMN IF NOT EXISTS seats_metadata JSONB;

-- 2. Create dsp_seats_sync_log table for tracking DSP seat synchronization history
CREATE TABLE IF NOT EXISTS dsp_seats_sync_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_account_id UUID REFERENCES user_accounts(id) ON DELETE CASCADE,
    advertiser_id VARCHAR(255) NOT NULL,
    sync_status VARCHAR(50) NOT NULL,
    seats_retrieved INTEGER DEFAULT 0,
    exchanges_count INTEGER DEFAULT 0,
    error_message TEXT,
    request_metadata JSONB,
    response_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Valid sync status values
    CHECK (sync_status IN ('pending', 'in_progress', 'success', 'failed', 'partial'))
);

-- 3. Create indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_dsp_seats_sync_log_advertiser
ON dsp_seats_sync_log(advertiser_id);

CREATE INDEX IF NOT EXISTS idx_dsp_seats_sync_log_user_account
ON dsp_seats_sync_log(user_account_id);

CREATE INDEX IF NOT EXISTS idx_dsp_seats_sync_log_status
ON dsp_seats_sync_log(sync_status);

CREATE INDEX IF NOT EXISTS idx_dsp_seats_sync_log_created_at
ON dsp_seats_sync_log(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_dsp_seats_sync_log_advertiser_created
ON dsp_seats_sync_log(advertiser_id, created_at DESC);

-- 4. Create index for seats_metadata JSONB column to enable efficient queries
CREATE INDEX IF NOT EXISTS idx_user_accounts_seats_metadata
ON user_accounts USING GIN (seats_metadata);

-- 5. Add comment for documentation
COMMENT ON TABLE dsp_seats_sync_log IS 'Tracks synchronization history for DSP advertiser seats data';
COMMENT ON COLUMN user_accounts.seats_metadata IS 'JSONB field containing DSP seat information including exchanges, last sync timestamp, and total seats count';
COMMENT ON COLUMN dsp_seats_sync_log.sync_status IS 'Status of the synchronization attempt: pending, in_progress, success, failed, or partial';
COMMENT ON COLUMN dsp_seats_sync_log.request_metadata IS 'Contains request parameters like max_results, next_token, exchange_ids, profile_id';
COMMENT ON COLUMN dsp_seats_sync_log.response_metadata IS 'Contains response metadata like has_next_token, advertiser_seats_count';