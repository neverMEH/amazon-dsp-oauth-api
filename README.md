# Amazon DSP OAuth API

OAuth 2.0 authentication service for Amazon DSP Campaign Insights API with automatic token refresh and Next.js testing dashboard.

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/deploy)

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Supabase account
- Amazon Developer account with DSP API access

### Backend Setup

1. **Install dependencies:**
```bash
cd backend
pip install -r requirements.txt
```

2. **Configure environment variables:**
```bash
# Copy the example file
cp .env.example .env

# Generate encryption keys
python generate_keys.py

# Update .env with:
# - Your Supabase URL and key
# - Generated FERNET_KEY and ADMIN_KEY
# - Amazon OAuth credentials (already included)
```

3. **Set up Supabase database:**

Run this SQL in your Supabase SQL editor:

```sql
-- Create tables
CREATE TABLE oauth_tokens (
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

CREATE TABLE oauth_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    state_token VARCHAR(255) UNIQUE NOT NULL,
    redirect_uri TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() + INTERVAL '10 minutes',
    used BOOLEAN DEFAULT false
);

CREATE TABLE auth_audit_log (
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

CREATE TABLE application_config (
    key VARCHAR(255) PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    is_encrypted BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_oauth_tokens_active ON oauth_tokens(is_active) WHERE is_active = true;
CREATE INDEX idx_oauth_tokens_expires ON oauth_tokens(expires_at) WHERE is_active = true;
CREATE INDEX idx_oauth_states_token ON oauth_states(state_token) WHERE used = false;
CREATE INDEX idx_oauth_states_expires ON oauth_states(expires_at);
CREATE INDEX idx_auth_audit_event_type ON auth_audit_log(event_type, created_at DESC);
CREATE INDEX idx_auth_audit_errors ON auth_audit_log(event_status, created_at DESC) WHERE event_status = 'failure';
CREATE INDEX idx_auth_audit_token ON auth_audit_log(token_id) WHERE token_id IS NOT NULL;

-- Insert default configuration
INSERT INTO application_config (key, value, description, is_encrypted) VALUES
    ('oauth_token_refresh_interval', '60', 'Token refresh check interval in seconds', false),
    ('oauth_token_refresh_buffer', '300', 'Seconds before expiry to trigger refresh', false),
    ('oauth_max_refresh_retries', '5', 'Maximum refresh retry attempts', false),
    ('oauth_retry_backoff_base', '2', 'Exponential backoff base for retries', false);

-- Enable RLS
ALTER TABLE oauth_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth_audit_log ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY service_role_all ON oauth_tokens FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY service_role_audit ON auth_audit_log FOR ALL USING (true) WITH CHECK (true);
```

4. **Run the backend:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

The API will be available at http://localhost:8000
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

### Frontend Setup (Coming Next)

The Next.js dashboard with shadcn/ui components will be implemented in Task 4.

## 📝 API Endpoints

### Authentication
- `GET /api/v1/auth/amazon/login` - Initiate OAuth flow
- `GET /api/v1/auth/amazon/callback` - Handle OAuth callback
- `GET /api/v1/auth/status` - Check authentication status
- `POST /api/v1/auth/refresh` - Manual token refresh (requires admin key)
- `DELETE /api/v1/auth/revoke` - Revoke tokens (requires admin key)
- `GET /api/v1/auth/audit` - View audit logs

### Health
- `GET /api/v1/health` - Service health check

## 🔐 Security Features

- **Fernet encryption** for token storage
- **CSRF protection** with state tokens
- **Automatic token refresh** before expiration
- **Comprehensive audit logging**
- **Environment-based configuration**

## 🧪 Testing

Run the test suite:
```bash
cd backend
pytest tests/ -v
```

## 📊 Project Status

### ✅ Completed (Task 1)
- FastAPI backend structure
- OAuth 2.0 implementation
- Token encryption service
- Supabase integration
- Error handling and logging
- Background refresh service
- Comprehensive test suite

### 🚧 Next Steps
- Task 2: Database migration setup
- Task 3: Enhanced refresh service
- Task 4: Next.js frontend dashboard
- Task 5: Railway deployment

## 🤝 Contributing

This is a private project for Amazon DSP API integration.

## 📄 License

Proprietary - All rights reserved