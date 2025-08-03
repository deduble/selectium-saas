# Google Console OAuth Configuration Guide

This guide provides step-by-step instructions to fix the `redirect_uri_mismatch` error by properly configuring Google Console for Selextract Cloud.

## CRITICAL: Correct Redirect URI

**The correct redirect URI is:** `http://localhost:8000/api/auth/google/callback`

## Step-by-Step Google Console Configuration

### Step 1: Access Google Cloud Console
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Sign in with your Google account
3. Select your project or create a new one

### Step 2: Enable Google+ API
1. Navigate to **APIs & Services** → **Library**
2. Search for "Google+ API" or "People API"
3. Click **Enable** if not already enabled

### Step 3: Configure OAuth Consent Screen
1. Navigate to **APIs & Services** → **OAuth consent screen**
2. Choose **External** user type (for development)
3. Fill in required fields:
   - **App name:** Selextract Cloud
   - **User support email:** your-email@domain.com
   - **Developer contact information:** your-email@domain.com
4. Add scopes:
   - `openid`
   - `email`
   - `profile`
5. Save and continue

### Step 4: Create OAuth Credentials
1. Navigate to **APIs & Services** → **Credentials**
2. Click **+ CREATE CREDENTIALS** → **OAuth 2.0 Client IDs**
3. Choose **Web application** as application type
4. Set **Name:** Selextract Cloud Local Development

### Step 5: Configure Authorized Redirect URIs
**THIS IS THE CRITICAL STEP:**

In the **Authorized redirect URIs** section, add EXACTLY:
```
http://localhost:8000/api/auth/google/callback
```

**Important Notes:**
- Use `http://` (not `https://`) for local development
- Use port `8000` (the API server port, not frontend port 3000)
- Include the full path `/api/auth/google/callback`
- Do NOT use trailing slashes
- Do NOT add the frontend URL (`http://localhost:3000/auth/success`)

### Step 6: Save and Copy Credentials
1. Click **SAVE**
2. Copy the **Client ID** and **Client Secret**
3. Update your `.env` file:
   ```bash
   GOOGLE_CLIENT_ID=your_client_id_here
   GOOGLE_CLIENT_SECRET=your_client_secret_here
   GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback
   ```

## Verification Steps

### Step 1: Check Environment Variables
Ensure your `.env` file contains:
```bash
# OAuth
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback
GOOGLE_CLIENT_ID=your_actual_client_id
GOOGLE_CLIENT_SECRET=your_actual_client_secret

# Application URLs
API_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your_actual_client_id
```

### Step 2: Test the OAuth Flow
1. Start your services:
   ```bash
   docker-compose up
   ```

2. Visit the debug page:
   ```
   http://localhost:3000/debug/oauth
   ```

3. Verify the environment variables and OAuth URLs are correct

4. Test login:
   ```
   http://localhost:3000/login
   ```

### Step 3: Monitor OAuth Flow
The OAuth flow should work as follows:
1. User clicks "Continue with Google" on `/login`
2. Frontend calls `/api/auth/google` to get authorization URL
3. User is redirected to Google OAuth
4. Google redirects to `http://localhost:8000/api/auth/google/callback`
5. Backend processes the callback and redirects to `http://localhost:3000/auth/success?token=...`
6. Frontend extracts the token and logs in the user

## Common Issues and Solutions

### Issue 1: Still getting redirect_uri_mismatch
**Solution:** Double-check the Google Console configuration:
- Ensure the redirect URI is exactly: `http://localhost:8000/api/auth/google/callback`
- Check for typos, extra spaces, or trailing slashes
- Wait a few minutes for Google changes to propagate

### Issue 2: Environment variables not loading
**Solution:**
1. Restart Docker containers completely:
   ```bash
   docker-compose down
   docker-compose up --build
   ```
2. Check that `.env` file is in the project root
3. Verify environment variables are correctly formatted (no quotes around values)

### Issue 3: CORS errors
**Solution:** Ensure your CORS configuration allows the frontend origin:
```bash
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
```

### Issue 4: "Invalid state parameter" error
**Solution:** This indicates session storage issues:
1. Clear browser cookies and cache
2. Restart the application
3. In production, implement Redis for session storage

## Production Configuration

For production deployment, update the redirect URI to your production domain:
```
https://yourdomain.com/api/auth/google/callback
```

And update environment variables accordingly:
```bash
GOOGLE_REDIRECT_URI=https://yourdomain.com/api/auth/google/callback
API_URL=https://yourdomain.com
FRONTEND_URL=https://yourdomain.com
```

## Security Notes

1. **Client Secret Security:** Keep your Google Client Secret secure and never expose it in frontend code
2. **HTTPS in Production:** Always use HTTPS in production environments
3. **Domain Verification:** Verify your production domain in Google Console
4. **Scope Limitation:** Only request necessary OAuth scopes (openid, email, profile)

## Troubleshooting Commands

### Check environment variables in containers:
```bash
# API container
docker-compose exec api env | grep GOOGLE

# Frontend container  
docker-compose exec frontend env | grep NEXT_PUBLIC
```

### View logs for OAuth flow:
```bash
# API logs
docker-compose logs -f api

# Frontend logs
docker-compose logs -f frontend
```

### Test API endpoint directly:
```bash
curl -X GET "http://localhost:8000/api/auth/google" \
  -H "Accept: application/json"
```

This should return a JSON response with `auth_url` and `state` fields.

---

**Need Help?** 
If you're still experiencing issues after following this guide, check the debug page at `http://localhost:3000/debug/oauth` to see the exact configuration being used.