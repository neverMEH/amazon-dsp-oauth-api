# Database Schema

This is the database schema implementation for the spec detailed in @.agent-os/specs/2025-09-16-dsp-advertiser-seats/spec.md

> Created: 2025-09-16
> Version: 1.0.0

## Schema Changes

### 1. Add seats_metadata Column to user_accounts Table

**Migration SQL:**
```sql
-- Add seats_metadata column for storing DSP seat information
ALTER TABLE user_accounts
ADD COLUMN IF NOT EXISTS seats_metadata JSONB DEFAULT '{}';

-- Create index for efficient JSONB queries
CREATE INDEX IF NOT EXISTS idx_user_accounts_seats_metadata
ON user_accounts USING gin(seats_metadata);

-- Update existing DSP accounts with default seats structure
UPDATE user_accounts
SET seats_metadata = jsonb_build_object(
    'exchanges', '[]'::jsonb,
    'last_seats_sync', NULL,
    'total_seats', 0,
    'sync_status', 'pending'
)
WHERE account_type = 'dsp'
AND (seats_metadata IS NULL OR seats_metadata = '{}');
```

### 2. Create dsp_seats_sync_log Table

**Table Creation SQL:**
```sql
-- Create table for tracking DSP seats synchronization history
CREATE TABLE IF NOT EXISTS dsp_seats_sync_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_account_id UUID NOT NULL REFERENCES user_accounts(id) ON DELETE CASCADE,
    advertiser_id VARCHAR(255) NOT NULL,
    sync_status VARCHAR(50) NOT NULL CHECK (sync_status IN ('success', 'failed', 'partial')),
    seats_retrieved INTEGER DEFAULT 0,
    exchanges_count INTEGER DEFAULT 0,
    error_message TEXT,
    request_metadata JSONB DEFAULT '{}',
    response_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Indexes for performance
    INDEX idx_dsp_seats_sync_user_account (user_account_id),
    INDEX idx_dsp_seats_sync_advertiser (advertiser_id),
    INDEX idx_dsp_seats_sync_created (created_at DESC)
);
```

### 3. Update metadata Structure in user_accounts

**JSONB Structure for seats_metadata:**
```json
{
    "exchanges": [
        {
            "exchange_id": "string",
            "exchange_name": "string",
            "deal_creation_id": "string|null",
            "spend_tracking_id": "string|null",
            "added_at": "ISO 8601 timestamp"
        }
    ],
    "last_seats_sync": "ISO 8601 timestamp",
    "total_seats": "integer",
    "sync_status": "success|failed|pending",
    "next_token": "string|null",
    "has_more_pages": "boolean"
}
```

## Migration Rationale

### Why JSONB for seats_metadata?
- **Flexibility**: Seat structures may vary between exchanges and evolve over time
- **Performance**: GIN indexes provide efficient queries on JSONB data
- **Simplicity**: Avoids complex relational structures for exchange-specific data
- **Compatibility**: Aligns with existing metadata column pattern in user_accounts

### Why separate sync_log table?
- **Audit Trail**: Maintains history of all synchronization attempts
- **Debugging**: Helps troubleshoot sync failures and performance issues
- **Analytics**: Enables analysis of sync patterns and success rates
- **Compliance**: Provides audit log for data access and updates

## Data Integrity Rules

### Constraints
- `advertiser_id` must match pattern `^[0-9]+$` (numeric string)
- `sync_status` limited to enum values: 'success', 'failed', 'partial', 'pending'
- `user_account_id` must reference valid DSP account (account_type = 'dsp')

### Triggers
```sql
-- Trigger to update last_synced_at when seats_metadata changes
CREATE OR REPLACE FUNCTION update_seats_sync_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.seats_metadata IS DISTINCT FROM NEW.seats_metadata THEN
        NEW.last_synced_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_seats_sync
BEFORE UPDATE ON user_accounts
FOR EACH ROW
WHEN (NEW.account_type = 'dsp')
EXECUTE FUNCTION update_seats_sync_timestamp();
```

## Performance Considerations

### Indexes
- **GIN Index on seats_metadata**: Enables efficient queries like "find all accounts with seats on exchange X"
- **B-tree Indexes on sync_log**: Optimizes queries for recent syncs and by advertiser

### Query Optimization Examples
```sql
-- Find accounts with seats on specific exchange
SELECT * FROM user_accounts
WHERE account_type = 'dsp'
AND seats_metadata @> '{"exchanges": [{"exchange_name": "Google Ad Manager"}]}';

-- Get recent sync history for an advertiser
SELECT * FROM dsp_seats_sync_log
WHERE advertiser_id = $1
ORDER BY created_at DESC
LIMIT 10;
```

## Rollback Plan

```sql
-- Rollback migration if needed
ALTER TABLE user_accounts DROP COLUMN IF EXISTS seats_metadata;
DROP TABLE IF EXISTS dsp_seats_sync_log;
DROP TRIGGER IF EXISTS trigger_update_seats_sync ON user_accounts;
DROP FUNCTION IF EXISTS update_seats_sync_timestamp();
```