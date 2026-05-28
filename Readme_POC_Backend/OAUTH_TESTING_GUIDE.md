# OAuth Swagger UI Testing Guide

## ⚠️ Why OAuth Endpoints Show "Failed to fetch" in Swagger UI

**This is EXPECTED behavior**, not an error!

### The Problem
- `/auth/login` returns a **redirect response** (HTTP 307) to Google's OAuth server
- Swagger UI's "Try it out" feature **cannot follow redirects** to external domains
- This triggers the "Failed to fetch" error you see

### The Solution
**OAuth endpoints MUST be tested in a real browser, not Swagger UI.**

## ✅ How to Properly Test OAuth Endpoints

### Method 1: Direct Browser Testing (Recommended)
1. Make sure your server is running:
   ```bash
   uvicorn app.main:app --reload
   ```

2. Open your browser to:
   ```
   http://localhost:8000/auth/login
   ```

3. You'll be redirected to Google sign-in
4. Complete the OAuth flow
5. You'll be redirected back with a JWT cookie set

### Method 2: Test the Health Check (Swagger UI works!)
In Swagger UI, test this endpoint instead:
- **GET /auth/health** ✅ This works in Swagger!

This verifies your auth service is running properly.

## 📝 Which Endpoints Work in Swagger UI?

| Endpoint | Swagger UI? | Why? |
|----------|-------------|------|
| `/auth/health` | ✅ Yes | Returns JSON, no redirect |
| `/auth/login` | ❌ No | Redirects to Google |
| `/auth/callback` | ❌ No | Called by Google, not you |
| `/auth/me` | ✅ Yes* | *Requires JWT cookie from browser |
| `/auth/logout` | ✅ Yes* | *Requires JWT cookie from browser |
| `/sync` | ✅ Yes* | *Requires JWT cookie from browser |
| `/projects` | ✅ Yes* | *Requires JWT cookie from browser |
| `/generate-readme` | ✅ Yes* | *Requires JWT cookie from browser |

## 🔧 Complete Testing Workflow

### Step 1: Start Server
```bash
uvicorn app.main:app --reload
```

### Step 2: Test Auth Health (Swagger UI)
Go to Swagger UI: `http://localhost:8000/docs`
- Try **GET /auth/health** ✅ Should return `{"status": "healthy"}`

### Step 3: Login (Browser)
Open browser to: `http://localhost:8000/auth/login`
- Sign in with Google
- Grant permissions
- You'll get a JWT cookie

### Step 4: Test Protected Endpoints (Swagger UI)
Now that you have the JWT cookie:
- Try **GET /auth/me** ✅ Should show your user info
- Try **POST /sync** ✅ Should sync emails
- Try **GET /projects** ✅ Should list projects

## 🎯 Summary

**The "Failed to fetch" error is NOT a bug!**
- OAuth login endpoints naturally redirect to Google
- Swagger UI can't handle external redirects
- Use your browser for OAuth testing
- Use Swagger UI for testing regular API endpoints

Your implementation is **working correctly**! 🎉
