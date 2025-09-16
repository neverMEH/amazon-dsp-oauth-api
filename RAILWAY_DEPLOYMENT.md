# Railway Deployment Guide

This guide covers deploying the Amazon DSP OAuth API as two separate Railway services for optimal performance and scalability.

## Architecture Overview

```
┌─────────────────┐         ┌─────────────────┐
│                 │         │                 │
│  Frontend       │ ──API──>│  Backend        │
│  (React/Vite)   │         │  (FastAPI)      │
│                 │         │                 │
└─────────────────┘         └─────────────────┘
       ↓                            ↓
   Railway CDN                  Supabase DB
```

## Prerequisites

1. Railway account with active project
2. GitHub repository connected to Railway
3. Supabase project for database
4. Clerk account for authentication
5. Amazon Advertising API credentials

## Deployment Steps

### Step 1: Create Railway Project

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Create new project
railway init
```

### Step 2: Create Backend Service

1. In Railway Dashboard, click "New Service"
2. Select "GitHub Repo" and choose your repository
3. Name it `backend-api`
4. Set the following configurations:

**Build Configuration:**
- Root Directory: `/`
- Build Command: (use railway.backend.toml)
- Start Command: (use railway.backend.toml)

**Environment Variables:**
Copy all variables from `.env.railway.backend` to Railway's environment variables section.

Critical variables to update:
```
ENVIRONMENT=production
AMAZON_OAUTH_REDIRECT_URI=https://your-backend.railway.app/api/v1/auth/amazon/callback
FRONTEND_URL=https://your-frontend.railway.app
BACKEND_URL=https://your-backend.railway.app
CORS_ORIGINS=["https://your-frontend.railway.app"]
```

### Step 3: Create Frontend Service

1. Click "New Service" again
2. Select same GitHub repo
3. Name it `frontend-app`
4. Set the following configurations:

**Build Configuration:**
- Root Directory: `/`
- Build Command: (use railway.frontend.toml)
- Start Command: (use railway.frontend.toml)

**Environment Variables:**
Copy all variables from `.env.railway.frontend` to Railway's environment variables section.

Critical variable to update:
```
VITE_API_URL=https://your-backend.railway.app
```

### Step 4: Configure Service Settings

#### Backend Service:
- **Health Check Path**: `/api/v1/health`
- **Deploy on Push**: Enable for `main` branch
- **Auto Deploy**: Enable

#### Frontend Service:
- **Health Check Path**: `/`
- **Deploy on Push**: Enable for `main` branch
- **Auto Deploy**: Enable

### Step 5: Set Up Custom Domains (Optional)

#### Backend Domain:
1. Go to Backend service settings
2. Click "Generate Domain" or add custom domain
3. Update `BACKEND_URL` in backend environment variables
4. Update `VITE_API_URL` in frontend environment variables

#### Frontend Domain:
1. Go to Frontend service settings
2. Click "Generate Domain" or add custom domain
3. Update `FRONTEND_URL` in backend environment variables
4. Update `CORS_ORIGINS` in backend environment variables

### Step 6: Deploy

```bash
# Deploy backend
railway up -s backend-api

# Deploy frontend
railway up -s frontend-app
```

Or push to your GitHub repository to trigger automatic deployments.

## Environment Variables Reference

### Backend Service

| Variable | Description | Example |
|----------|-------------|---------|
| `ENVIRONMENT` | Deployment environment | `production` |
| `PORT` | Server port (Railway provides) | `${{PORT}}` |
| `AMAZON_CLIENT_ID` | Amazon OAuth client ID | `amzn1.application-oa2-client.xxx` |
| `AMAZON_CLIENT_SECRET` | Amazon OAuth secret | `xxx` |
| `AMAZON_OAUTH_REDIRECT_URI` | OAuth callback URL | `https://api.yourdomain.app/api/v1/auth/amazon/callback` |
| `FERNET_KEY` | Encryption key for tokens | Generate with provided script |
| `SUPABASE_URL` | Supabase project URL | `https://xxx.supabase.co` |
| `SUPABASE_KEY` | Supabase anon key | `eyJxxx` |
| `CLERK_SECRET_KEY` | Clerk secret key | `sk_live_xxx` |
| `FRONTEND_URL` | Frontend service URL | `https://app.yourdomain.app` |

### Frontend Service

| Variable | Description | Example |
|----------|-------------|---------|
| `NODE_ENV` | Node environment | `production` |
| `PORT` | Server port (Railway provides) | `${{PORT}}` |
| `VITE_API_URL` | Backend API URL | `https://api.yourdomain.app` |
| `VITE_CLERK_PUBLISHABLE_KEY` | Clerk public key | `pk_live_xxx` |

## Post-Deployment Checklist

- [ ] Backend health check passing (`/api/v1/health`)
- [ ] Frontend loads successfully
- [ ] CORS configured correctly (no CORS errors in browser console)
- [ ] Authentication flow works (Clerk integration)
- [ ] Amazon OAuth flow completes successfully
- [ ] Database connections working (check Supabase)
- [ ] DSP seats feature accessible
- [ ] Environment variables properly set for both services
- [ ] Custom domains configured (if applicable)
- [ ] SSL certificates active

## Monitoring & Logs

### View Logs:
```bash
# Backend logs
railway logs -s backend-api

# Frontend logs
railway logs -s frontend-app
```

### Railway Dashboard:
- Monitor deployments
- View metrics (CPU, Memory, Network)
- Check build logs
- Review runtime logs

## Troubleshooting

### CORS Issues
If you see CORS errors:
1. Verify `FRONTEND_URL` in backend environment variables
2. Check `CORS_ORIGINS` includes your frontend URL
3. Restart backend service after changes

### Database Connection Issues
1. Verify `SUPABASE_URL` and `SUPABASE_KEY` are correct
2. Check Supabase connection pooler settings
3. Ensure database migrations have run

### Build Failures
1. Check build logs in Railway dashboard
2. Verify `nixpacks.toml` configurations
3. Ensure all dependencies are in `requirements.txt` and `package.json`

### Authentication Issues
1. Verify Clerk keys in both frontend and backend
2. Check webhook configuration in Clerk dashboard
3. Ensure `AMAZON_OAUTH_REDIRECT_URI` matches Railway URL

## Rollback Strategy

If deployment fails:
1. Go to Railway dashboard
2. Select the problematic service
3. Click on "Deployments"
4. Find last working deployment
5. Click "Rollback to this deployment"

## Performance Optimization

1. **Enable Railway's Edge Network** for frontend service
2. **Set up caching headers** in backend responses
3. **Configure auto-scaling** if needed (Railway Pro)
4. **Monitor resource usage** and adjust service limits

## Security Notes

- Never commit `.env` files to repository
- Rotate `FERNET_KEY` periodically
- Use Railway's secret management for sensitive values
- Enable 2FA on Railway account
- Regularly update dependencies

## Support

- Railway Documentation: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
- Project Issues: https://github.com/your-username/amazon-dsp-oauth-api/issues