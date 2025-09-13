# Database Schema

This is the database schema implementation for the spec detailed in @.agent-os/specs/2025-09-13-clerk-auth-amazon-sync/spec.md

## Schema Changes

### New Tables

#### users
Stores authenticated user information synced from Clerk
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clerk_user_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    profile_image_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_users_clerk_user_id ON users(clerk_user_id);
CREATE INDEX idx_users_email ON users(email);
```

#### user_accounts
Links users to their Amazon Advertising accounts
```sql
CREATE TABLE user_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_name VARCHAR(255) NOT NULL,
    amazon_account_id VARCHAR(255) NOT NULL,
    marketplace_id VARCHAR(50),
    account_type VARCHAR(50) DEFAULT 'advertising',
    is_default BOOLEAN DEFAULT FALSE,
    status VARCHAR(50) DEFAULT 'active',
    connected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_synced_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    UNIQUE(user_id, amazon_account_id)
);

CREATE INDEX idx_user_accounts_user_id ON user_accounts(user_id);
CREATE INDEX idx_user_accounts_status ON user_accounts(status);
```

### Table Modifications

#### oauth_tokens (modification)
Add user relationship to existing oauth_tokens table
```sql
ALTER TABLE oauth_tokens 
ADD COLUMN user_id UUID REFERENCES users(id) ON DELETE CASCADE,
ADD COLUMN user_account_id UUID REFERENCES user_accounts(id) ON DELETE CASCADE;

CREATE INDEX idx_oauth_tokens_user_id ON oauth_tokens(user_id);
CREATE INDEX idx_oauth_tokens_user_account_id ON oauth_tokens(user_account_id);
```

## Row Level Security (RLS) Policies

### Enable RLS on tables
```sql
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE oauth_tokens ENABLE ROW LEVEL SECURITY;
```

### Users table policies
```sql
-- Users can only view their own profile
CREATE POLICY users_select_own ON users
    FOR SELECT USING (clerk_user_id = current_setting('app.current_user_id'));

-- Users can only update their own profile
CREATE POLICY users_update_own ON users
    FOR UPDATE USING (clerk_user_id = current_setting('app.current_user_id'));
```

### User accounts policies
```sql
-- Users can only view their own accounts
CREATE POLICY user_accounts_select_own ON user_accounts
    FOR SELECT USING (user_id IN (
        SELECT id FROM users WHERE clerk_user_id = current_setting('app.current_user_id')
    ));

-- Users can only manage their own accounts
CREATE POLICY user_accounts_all_own ON user_accounts
    FOR ALL USING (user_id IN (
        SELECT id FROM users WHERE clerk_user_id = current_setting('app.current_user_id')
    ));
```

### OAuth tokens policies
```sql
-- Users can only access their own tokens
CREATE POLICY oauth_tokens_all_own ON oauth_tokens
    FOR ALL USING (user_id IN (
        SELECT id FROM users WHERE clerk_user_id = current_setting('app.current_user_id')
    ));
```

## Database Functions

### Set default account function
```sql
CREATE OR REPLACE FUNCTION set_default_account(p_user_id UUID, p_account_id UUID)
RETURNS VOID AS $$
BEGIN
    -- Reset all accounts to non-default
    UPDATE user_accounts 
    SET is_default = FALSE 
    WHERE user_id = p_user_id;
    
    -- Set selected account as default
    UPDATE user_accounts 
    SET is_default = TRUE 
    WHERE user_id = p_user_id AND id = p_account_id;
END;
$$ LANGUAGE plpgsql;
```

### Update timestamp trigger
```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

## Migration Notes

1. **Data Migration**: Existing oauth_tokens records will need to be associated with user accounts after migration
2. **Backward Compatibility**: The system should handle tokens without user associations during transition period
3. **Indexes**: All foreign key columns have indexes for query performance
4. **Constraints**: Unique constraints prevent duplicate account connections per user
5. **Cascading Deletes**: User deletion cascades to remove all associated accounts and tokens