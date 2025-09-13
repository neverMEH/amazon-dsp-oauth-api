# Database Schema

This is the database schema implementation for the spec detailed in @.agent-os/specs/2025-09-12-oauth-foundation-infrastructure/spec.md

## Schema Overview

Single-user authentication system with encrypted token storage and comprehensive audit logging for Amazon DSP API OAuth integration.

## Tables

### oauth_tokens
Primary table for storing encrypted OAuth tokens with automatic refresh tracking.

```sql
CREATE TABLE oauth_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    access_token TEXT NOT NULL,           -- Fernet-encrypted access token
    refresh_token TEXT NOT NULL,          -- Fernet-encrypted refresh token
    token_type VARCHAR(50) DEFAULT 'Bearer',
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    scope TEXT NOT NULL,                  -- DSP API scope
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_refresh_at TIMESTAMP WITH TIME ZONE,
    refresh_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true
);

-- Index for active token lookups
CREATE INDEX idx_oauth_tokens_active ON oauth_tokens(is_active) WHERE is_active = true;

-- Index for expiration monitoring
CREATE INDEX idx_oauth_tokens_expires ON oauth_tokens(expires_at) WHERE is_active = true;
```

### oauth_states
CSRF protection for OAuth flow state management.

```sql
CREATE TABLE oauth_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    state_token VARCHAR(255) UNIQUE NOT NULL,
    redirect_uri TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() + INTERVAL '10 minutes',
    used BOOLEAN DEFAULT false
);

-- Index for state token lookup
CREATE INDEX idx_oauth_states_token ON oauth_states(state_token) WHERE used = false;

-- Automatic cleanup of expired states
CREATE INDEX idx_oauth_states_expires ON oauth_states(expires_at);
```

### auth_audit_log
Comprehensive audit trail for all authentication events.

```sql
CREATE TABLE auth_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,      -- 'login', 'refresh', 'error', 'revoke'
    event_status VARCHAR(20) NOT NULL,    -- 'success', 'failure', 'pending'
    token_id UUID REFERENCES oauth_tokens(id) ON DELETE SET NULL,
    error_message TEXT,
    error_code VARCHAR(50),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB                        -- Additional event-specific data
);

-- Index for querying by event type
CREATE INDEX idx_auth_audit_event_type ON auth_audit_log(event_type, created_at DESC);

-- Index for error analysis
CREATE INDEX idx_auth_audit_errors ON auth_audit_log(event_status, created_at DESC) 
WHERE event_status = 'failure';

-- Index for token history
CREATE INDEX idx_auth_audit_token ON auth_audit_log(token_id) WHERE token_id IS NOT NULL;
```

### application_config
Key-value store for application configuration and settings.

```sql
CREATE TABLE application_config (
    key VARCHAR(255) PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    is_encrypted BOOLEAN DEFAULT false,   -- Flag for encrypted values
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default configuration
INSERT INTO application_config (key, value, description, is_encrypted) VALUES
    ('oauth_token_refresh_interval', '60', 'Token refresh check interval in seconds', false),
    ('oauth_token_refresh_buffer', '300', 'Seconds before expiry to trigger refresh', false),
    ('oauth_max_refresh_retries', '5', 'Maximum refresh retry attempts', false),
    ('oauth_retry_backoff_base', '2', 'Exponential backoff base for retries', false);
```

## Database Functions

### Update Timestamp Trigger
Automatically update the `updated_at` timestamp on record modification.

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to oauth_tokens table
CREATE TRIGGER update_oauth_tokens_updated_at
    BEFORE UPDATE ON oauth_tokens
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply to application_config table
CREATE TRIGGER update_application_config_updated_at
    BEFORE UPDATE ON application_config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### Cleanup Expired States
Automatic cleanup of expired OAuth state tokens.

```sql
CREATE OR REPLACE FUNCTION cleanup_expired_states()
RETURNS void AS $$
BEGIN
    DELETE FROM oauth_states 
    WHERE expires_at < NOW() OR used = true;
END;
$$ LANGUAGE plpgsql;

-- Schedule cleanup (requires pg_cron extension or external scheduler)
-- Alternatively, call this function from the application periodically
```

## Row Level Security (RLS)

Enable RLS for multi-tenant future compatibility (currently single-user).

```sql
-- Enable RLS on sensitive tables
ALTER TABLE oauth_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth_audit_log ENABLE ROW LEVEL SECURITY;

-- Create policy for service role (full access)
CREATE POLICY service_role_all ON oauth_tokens
    FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY service_role_audit ON auth_audit_log
    FOR ALL
    USING (true)
    WITH CHECK (true);
```

## Migration Script

Complete migration for initial schema setup.

```sql
-- Migration: 001_initial_oauth_schema.sql
BEGIN;

-- Create tables
CREATE TABLE IF NOT EXISTS oauth_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    token_type VARCHAR(50) DEFAULT 'Bearer',
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    scope TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_refresh_at TIMESTAMP WITH TIME ZONE,
    refresh_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS oauth_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    state_token VARCHAR(255) UNIQUE NOT NULL,
    redirect_uri TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() + INTERVAL '10 minutes',
    used BOOLEAN DEFAULT false
);

CREATE TABLE IF NOT EXISTS auth_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,
    event_status VARCHAR(20) NOT NULL,
    token_id UUID REFERENCES oauth_tokens(id) ON DELETE SET NULL,
    error_message TEXT,
    error_code VARCHAR(50),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS application_config (
    key VARCHAR(255) PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    is_encrypted BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_oauth_tokens_active ON oauth_tokens(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_oauth_tokens_expires ON oauth_tokens(expires_at) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_oauth_states_token ON oauth_states(state_token) WHERE used = false;
CREATE INDEX IF NOT EXISTS idx_oauth_states_expires ON oauth_states(expires_at);
CREATE INDEX IF NOT EXISTS idx_auth_audit_event_type ON auth_audit_log(event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_auth_audit_errors ON auth_audit_log(event_status, created_at DESC) WHERE event_status = 'failure';
CREATE INDEX IF NOT EXISTS idx_auth_audit_token ON auth_audit_log(token_id) WHERE token_id IS NOT NULL;

-- Create functions and triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_oauth_tokens_updated_at
    BEFORE UPDATE ON oauth_tokens
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_application_config_updated_at
    BEFORE UPDATE ON application_config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default configuration
INSERT INTO application_config (key, value, description, is_encrypted) VALUES
    ('oauth_token_refresh_interval', '60', 'Token refresh check interval in seconds', false),
    ('oauth_token_refresh_buffer', '300', 'Seconds before expiry to trigger refresh', false),
    ('oauth_max_refresh_retries', '5', 'Maximum refresh retry attempts', false),
    ('oauth_retry_backoff_base', '2', 'Exponential backoff base for retries', false)
ON CONFLICT (key) DO NOTHING;

-- Enable RLS
ALTER TABLE oauth_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth_audit_log ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY service_role_all ON oauth_tokens
    FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY service_role_audit ON auth_audit_log
    FOR ALL
    USING (true)
    WITH CHECK (true);

COMMIT;
```

## Rationale

### Design Decisions
- **Single Active Token**: Since this is a single-user system, we maintain one active token set at a time
- **Encrypted Storage**: All tokens are Fernet-encrypted before storage for security
- **Audit Logging**: Comprehensive logging helps debug OAuth issues and track refresh patterns
- **State Management**: CSRF protection through state tokens with automatic expiration
- **Configuration Table**: Allows runtime adjustment of refresh parameters without code changes

### Performance Considerations
- **Indexes**: Strategic indexes on active tokens and expiration times for fast lookups
- **Cleanup**: Automatic cleanup of expired state tokens to prevent table bloat
- **UUID Primary Keys**: Better for distributed systems and prevents ID enumeration

### Data Integrity Rules
- **Token Uniqueness**: Each token set is unique with UUID primary keys
- **Referential Integrity**: Audit logs reference tokens with ON DELETE SET NULL
- **Timestamp Consistency**: Automatic updated_at triggers ensure accurate timestamps
- **State Token Security**: Short expiration (10 minutes) and single-use flags