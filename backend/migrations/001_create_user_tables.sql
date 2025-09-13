-- Migration: Create user authentication tables
-- Description: Creates users and user_accounts tables for Clerk authentication integration
-- Date: 2025-01-13

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create users table for Clerk-authenticated users
CREATE TABLE IF NOT EXISTS users (
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

-- Create indexes for users table
CREATE INDEX IF NOT EXISTS idx_users_clerk_user_id ON users(clerk_user_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Create user_accounts table for Amazon account connections
CREATE TABLE IF NOT EXISTS user_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_name VARCHAR(255) NOT NULL,
    amazon_account_id VARCHAR(255) NOT NULL,
    marketplace_id VARCHAR(50),
    account_type VARCHAR(50) DEFAULT 'advertising',
    is_default BOOLEAN DEFAULT FALSE,
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended', 'pending')),
    connected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_synced_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    UNIQUE(user_id, amazon_account_id)
);

-- Create indexes for user_accounts table
CREATE INDEX IF NOT EXISTS idx_user_accounts_user_id ON user_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_user_accounts_status ON user_accounts(status);
CREATE INDEX IF NOT EXISTS idx_user_accounts_amazon_id ON user_accounts(amazon_account_id);

-- Add user relationship to oauth_tokens table (if it exists)
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'oauth_tokens'
    ) THEN
        -- Add user_id column if it doesn't exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'oauth_tokens' AND column_name = 'user_id'
        ) THEN
            ALTER TABLE oauth_tokens 
            ADD COLUMN user_id UUID REFERENCES users(id) ON DELETE CASCADE;
            
            CREATE INDEX idx_oauth_tokens_user_id ON oauth_tokens(user_id);
        END IF;
        
        -- Add user_account_id column if it doesn't exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'oauth_tokens' AND column_name = 'user_account_id'
        ) THEN
            ALTER TABLE oauth_tokens 
            ADD COLUMN user_account_id UUID REFERENCES user_accounts(id) ON DELETE CASCADE;
            
            CREATE INDEX idx_oauth_tokens_user_account_id ON oauth_tokens(user_account_id);
        END IF;
    END IF;
END $$;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for users table
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create function to ensure only one default account per user
CREATE OR REPLACE FUNCTION ensure_single_default_account()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_default = TRUE THEN
        -- Reset all other accounts for this user to non-default
        UPDATE user_accounts 
        SET is_default = FALSE 
        WHERE user_id = NEW.user_id 
        AND id != NEW.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to ensure only one default account
DROP TRIGGER IF EXISTS ensure_single_default ON user_accounts;
CREATE TRIGGER ensure_single_default
    BEFORE INSERT OR UPDATE ON user_accounts
    FOR EACH ROW
    WHEN (NEW.is_default = TRUE)
    EXECUTE FUNCTION ensure_single_default_account();

-- Enable Row Level Security (RLS) on tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_accounts ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for users table
CREATE POLICY users_select_own ON users
    FOR SELECT 
    USING (clerk_user_id = current_setting('app.current_user_id', true));

CREATE POLICY users_update_own ON users
    FOR UPDATE 
    USING (clerk_user_id = current_setting('app.current_user_id', true));

CREATE POLICY users_insert_own ON users
    FOR INSERT 
    WITH CHECK (clerk_user_id = current_setting('app.current_user_id', true));

-- Create RLS policies for user_accounts table
CREATE POLICY user_accounts_all_own ON user_accounts
    FOR ALL 
    USING (user_id IN (
        SELECT id FROM users 
        WHERE clerk_user_id = current_setting('app.current_user_id', true)
    ));

-- Grant permissions to application role (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON users TO app_user;
        GRANT SELECT, INSERT, UPDATE, DELETE ON user_accounts TO app_user;
        GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO app_user;
    END IF;
END $$;

-- Add comment to tables
COMMENT ON TABLE users IS 'Stores user information synchronized from Clerk authentication';
COMMENT ON TABLE user_accounts IS 'Stores Amazon account connections for each user';

-- Add column comments
COMMENT ON COLUMN users.clerk_user_id IS 'Unique identifier from Clerk authentication service';
COMMENT ON COLUMN users.email IS 'User email address from Clerk';
COMMENT ON COLUMN user_accounts.amazon_account_id IS 'Amazon Advertising account identifier';
COMMENT ON COLUMN user_accounts.is_default IS 'Whether this is the users default account for dashboard display';
COMMENT ON COLUMN user_accounts.metadata IS 'Additional account data including advertiser IDs and profile information';