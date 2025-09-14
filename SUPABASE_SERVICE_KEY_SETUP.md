# Supabase Service Role Key Setup

## Problem
The application needs to create users in the database after Clerk authentication, but Supabase Row Level Security (RLS) policies block the anon key from creating users. This results in error 42501: "new row violates row-level security policy for table 'users'".

## Solution
Use a Supabase service role key for backend operations that need to bypass RLS.

## How to Get Your Service Role Key

1. Go to your [Supabase Dashboard](https://app.supabase.com)
2. Select your project
3. Go to Settings → API
4. Find the "Service Role" key under "Project API keys"
   - ⚠️ **IMPORTANT**: This key has full admin access - keep it secret!
   - Never expose this key in client-side code
   - Only use it in backend/server environments

## Setup Instructions

1. Copy your service role key from Supabase dashboard

2. Add it to your `.env` file:
```env
# Existing Supabase configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJhbGc...  # This is your anon key (keep this)

# Add this new line
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...  # Your service role key goes here
```

3. Restart your backend server

## Verification

Run the test script to verify the setup:
```bash
cd backend
python3 test_supabase_fix.py
```

You should see:
```
✓ Service client initialized (using service role key)
```

## Security Notes

- **Service role key bypasses ALL Row Level Security**
- Only use it for trusted backend operations
- Never expose it to the client or in public repositories
- Store it securely in environment variables
- Use it only when necessary (user creation, admin operations)

## Code Implementation

The code automatically uses the service role key when available:
- `UserService` uses service role by default for user operations
- Falls back to anon key if service role key is not configured
- Other operations continue using the anon key for proper RLS enforcement