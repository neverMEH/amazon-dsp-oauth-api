# 🚀 Quick Start Guide

## ✅ Prerequisites Completed
- ✅ Supabase database configured
- ✅ Environment variables set (.env file)
- ✅ Encryption keys generated

## 📦 Installation & Running

### Option 1: Using PowerShell (Recommended)

1. **Open PowerShell as Administrator**

2. **Allow script execution (if needed):**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

3. **Setup the backend:**
```powershell
.\setup_backend.ps1
```

4. **Run the backend:**
```powershell
.\run_backend.ps1
```

### Option 2: Using Command Prompt

1. **Setup the backend:**
```cmd
setup_backend.bat
```

2. **Run the backend:**
```cmd
run_backend.bat
```

### Option 3: Manual Setup

1. **Open a terminal in the project directory**

2. **Create virtual environment:**
```bash
cd backend
python -m venv venv
```

3. **Activate virtual environment:**
- Windows: `venv\Scripts\activate`
- PowerShell: `.\venv\Scripts\Activate.ps1`

4. **Install dependencies:**
```bash
pip install -r requirements.txt
```

5. **Run the server:**
```bash
uvicorn app.main:app --reload --port 8000
```

## 🔗 Access Points

Once running, you can access:

- **API Base**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health

## 🧪 Test the OAuth Flow

1. **Open the API docs**: http://localhost:8000/docs

2. **Start OAuth flow**:
   - Click on `GET /api/v1/auth/amazon/login`
   - Click "Try it out"
   - Click "Execute"
   - Copy the `auth_url` from the response

3. **Authorize with Amazon**:
   - Open the `auth_url` in your browser
   - Log in to Amazon with your developer account
   - Grant permissions for DSP Campaign Insights

4. **Check authentication status**:
   - Use `GET /api/v1/auth/status` to verify tokens are stored

## 🔑 Important Credentials

Your environment is configured with:
- **Admin Key**: `UwbStgW0nVX6-KO5e2lwrbxQzj3XCayInOg2-88bCUQ`
- **Fernet Key**: Already set (for encryption)
- **Supabase**: Connected to `pxnsjdlfgxrthgibmfzm.supabase.co`

## 📝 Manual Token Refresh

To manually refresh tokens (requires admin key):

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "X-Admin-Key: UwbStgW0nVX6-KO5e2lwrbxQzj3XCayInOg2-88bCUQ"
```

## 🐛 Troubleshooting

### Port 8000 already in use
- Change the port: `uvicorn app.main:app --reload --port 8001`

### Module not found errors
- Make sure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

### Database connection errors
- Verify Supabase URL and key in `.env`
- Check if tables were created in Supabase

### OAuth redirect errors
- Ensure redirect URI in Amazon Developer Console matches:
  `http://localhost:8000/api/v1/auth/amazon/callback`

## 📊 Next Steps

Once the backend is running successfully:
1. Complete the OAuth flow to get initial tokens
2. Verify automatic token refresh is working
3. Check audit logs at `/api/v1/auth/audit`
4. Proceed to frontend implementation (Task 4)