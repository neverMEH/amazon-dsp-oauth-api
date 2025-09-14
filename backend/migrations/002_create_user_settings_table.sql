-- Migration: Create user_settings table
-- Description: Store user preferences and settings for the application
-- Created: 2025-09-13

-- Create user_settings table
CREATE TABLE IF NOT EXISTS user_settings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT user_settings_user_id_unique UNIQUE (user_id)
);

-- Create index for user_id lookups
CREATE INDEX IF NOT EXISTS idx_user_settings_user_id ON user_settings(user_id);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_user_settings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER user_settings_updated_at_trigger
    BEFORE UPDATE ON user_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_user_settings_updated_at();

-- Enable Row Level Security
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for user_settings
-- Users can only view their own settings
CREATE POLICY user_settings_select_policy ON user_settings
    FOR SELECT
    USING (auth.uid()::text = (SELECT clerk_user_id FROM users WHERE id = user_settings.user_id));

-- Users can only insert their own settings
CREATE POLICY user_settings_insert_policy ON user_settings
    FOR INSERT
    WITH CHECK (auth.uid()::text = (SELECT clerk_user_id FROM users WHERE id = user_settings.user_id));

-- Users can only update their own settings
CREATE POLICY user_settings_update_policy ON user_settings
    FOR UPDATE
    USING (auth.uid()::text = (SELECT clerk_user_id FROM users WHERE id = user_settings.user_id))
    WITH CHECK (auth.uid()::text = (SELECT clerk_user_id FROM users WHERE id = user_settings.user_id));

-- Users can only delete their own settings
CREATE POLICY user_settings_delete_policy ON user_settings
    FOR DELETE
    USING (auth.uid()::text = (SELECT clerk_user_id FROM users WHERE id = user_settings.user_id));

-- Grant permissions
GRANT ALL ON user_settings TO authenticated;
GRANT USAGE ON SEQUENCE user_settings_id_seq TO authenticated;

-- Comments
COMMENT ON TABLE user_settings IS 'User preferences and application settings';
COMMENT ON COLUMN user_settings.user_id IS 'Reference to the user';
COMMENT ON COLUMN user_settings.preferences IS 'JSON object containing user preferences';
COMMENT ON COLUMN user_settings.created_at IS 'Timestamp when settings were first created';
COMMENT ON COLUMN user_settings.updated_at IS 'Timestamp when settings were last updated';