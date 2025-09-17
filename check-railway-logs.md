# Railway Logs Debugging Guide

## Accessing Railway Logs

### Via Railway CLI
```bash
# Install Railway CLI if not already installed
npm install -g @railway/cli

# Login to Railway
railway login

# View deployment logs
railway logs

# View build logs
railway logs --build

# Follow logs in real-time
railway logs -f

# View last 100 lines
railway logs -n 100
```

### Via Railway Dashboard
1. Go to https://railway.app/dashboard
2. Select your project
3. Click on the service
4. Navigate to "Deployments" tab
5. Click on specific deployment to see logs

## Common Issues and Solutions

### 1. Node.js Package Errors
**Symptom:**
```
error: undefined variable 'nodejs-20_x'
```

**Solution:** ✅ Already fixed - using `nodejs_20`

### 2. Build Memory Issues
**Symptom:**
```
JavaScript heap out of memory
```

**Solution:**
Add to nixpacks.toml:
```toml
[phases.build]
cmds = [
    "export NODE_OPTIONS='--max-old-space-size=4096'",
    "cd frontend && npm install && npm run build"
]
```

### 3. Port Binding Issues
**Symptom:**
```
Error: listen EADDRINUSE: address already in use
```

**Solution:**
Ensure using Railway's PORT variable:
```python
# backend/app/main.py
port = int(os.getenv("PORT", 8000))
```

### 4. Database Connection Issues
**Symptom:**
```
Cannot connect to Supabase
```

**Solution:**
Check environment variables:
- SUPABASE_URL
- SUPABASE_KEY

### 5. CORS Errors
**Symptom:**
```
Access to fetch at 'api.railway.app' from origin 'app.railway.app' has been blocked by CORS
```

**Solution:**
Update CORS_ORIGINS in backend environment variables

## Debugging Commands

### Check Current Deployment Status
```bash
railway status
```

### View Environment Variables
```bash
railway variables
```

### Restart Service
```bash
railway restart
```

### Rollback to Previous Deployment
```bash
railway rollback
```

## Log Patterns to Watch For

### Successful Build
```
✓ Built in X seconds
✓ Deployed successfully
```

### Successful Startup
```
INFO: Uvicorn running on http://0.0.0.0:8000
INFO: Application startup complete
```

### Database Connected
```
INFO: Supabase client initialized
```

### Token Refresh Scheduler Started
```
INFO: Token refresh scheduler started
```

## Health Check Verification

After deployment, verify:
```bash
# Check backend health
curl https://your-app.railway.app/api/v1/health

# Expected response:
{
  "status": "healthy",
  "version": "1.0.1",
  "timestamp": "...",
  "services": {
    "database": "connected",
    "token_refresh": "running"
  }
}
```

## If Build Still Fails

1. **Clear Railway Cache:**
   - In Railway dashboard → Settings → Clear build cache

2. **Check nixpacks.toml:**
   ```toml
   [phases.setup]
   nixPkgs = ["python311", "python311Packages.pip", "gcc", "nodejs_20"]
   ```

3. **Verify package.json engines:**
   ```json
   "engines": {
     "node": ">=18.0.0"
   }
   ```

4. **Check for missing dependencies:**
   ```bash
   # Frontend
   cd frontend && npm ls

   # Backend
   cd backend && pip list
   ```

## Environment Variable Checklist

Essential variables that must be set:
- [ ] PORT (Railway provides automatically)
- [ ] ENVIRONMENT=production
- [ ] AMAZON_CLIENT_ID
- [ ] AMAZON_CLIENT_SECRET
- [ ] AMAZON_OAUTH_REDIRECT_URI
- [ ] FERNET_KEY
- [ ] SUPABASE_URL
- [ ] SUPABASE_KEY
- [ ] CLERK_SECRET_KEY
- [ ] CLERK_PUBLISHABLE_KEY
- [ ] CLERK_WEBHOOK_SECRET
- [ ] FRONTEND_URL
- [ ] BACKEND_URL

## Contact Support

If issues persist:
1. Railway Discord: https://discord.gg/railway
2. GitHub Issues: https://github.com/neverMEH/amazon-dsp-oauth-api/issues
3. Railway Support: support@railway.app