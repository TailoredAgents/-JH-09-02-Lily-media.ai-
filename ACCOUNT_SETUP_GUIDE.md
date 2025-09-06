# Account Setup & Login Guide for AI Social Media Agent

## Overview
The platform uses an **open SaaS authentication system**. New users can sign up directly through the registration form with email verification (when enabled).

## Two Types of Accounts

### 1. Admin Account (Backend Management)
- **Purpose**: System administration, user management, registration key generation
- **Login URL**: `/admin/login` on your backend
- **Setup Required**: Set environment variables before running admin creation scripts:
  - `ADMIN_USERNAME` (default: superadmin)
  - `ADMIN_EMAIL` (required)
  - `ADMIN_PASSWORD` (required - use a strong password)

### 2. Regular User Account (Platform Users)
- **Purpose**: Using the social media automation features
- **Login URL**: `/login` on your frontend
- **Registration**: Open registration with email and password

## Initial Setup Process

### Step 1: Create Admin Account (One-time setup)

#### Option A: Using Render Shell (Recommended)
1. Go to your Render dashboard
2. Navigate to your backend web service
3. Click on "Shell" tab
4. Set environment variables and run:
```bash
export ADMIN_EMAIL="your-admin@company.com"
export ADMIN_PASSWORD="your-secure-admin-password"
python create_admin_simple.py
```

#### Option B: Local Setup (if you have database access)
```bash
# Set your production database URL and admin credentials
export DATABASE_URL="your-database-url-here"
export ADMIN_EMAIL="your-admin@company.com"
export ADMIN_PASSWORD="your-secure-admin-password"

# Run the admin creation script
python create_admin_simple.py
```

### Step 2: Access Admin Panel
1. Navigate to: `https://your-backend-url.onrender.com/admin/login`
2. Login with the superadmin credentials

### Step 3: Create Regular User Account
Users can register directly without registration keys:

1. Navigate to: `https://your-frontend-url.onrender.com/register`
2. Fill in the registration form:
   - Email
   - Username
   - Password
   - Full Name

### Step 4: Login as Regular User
1. Navigate to: `https://your-frontend-url.onrender.com/login`
2. Enter email and password
3. Complete 2FA if enabled

## API Endpoints

### Authentication Endpoints
- **Register**: `POST /api/auth/register`
  ```json
  {
    "email": "user@example.com",
    "username": "username", 
    "password": "password",
    "full_name": "Full Name"
  }
  ```

- **Login**: `POST /api/auth/login`
  ```json
  {
    "email": "user@example.com",
    "password": "password",
    "totp_code": "123456"  // Optional, if 2FA enabled
  }
  ```

### Admin Endpoints
- **Admin Login**: `POST /api/admin/auth/login`
  ```json
  {
    "username": "superadmin",
    "password": "Admin053103"
  }
  ```

- **List Users**: `GET /api/admin/users` (requires admin auth)

## Security Features

### Open Registration System
- **Purpose**: Allows anyone to create accounts
- **Features**:
  - Direct email/password registration
  - Optional email verification (configurable)
  - JWT-based authentication
  - Secure password hashing with bcrypt

### Two-Factor Authentication (2FA)
- Optional but recommended
- TOTP-based (Time-based One-Time Password)
- Backup codes available
- Can be enabled after account creation

### Password Requirements
- Minimum 8 characters
- Should contain uppercase, lowercase, numbers, and special characters
- Hashed using bcrypt

## Troubleshooting

### Can't Create Admin Account
1. Check database connection: Ensure `DATABASE_URL` is set correctly
2. Check if admin already exists: Query `admin_users` table
3. Check logs for specific errors

### Email Verification Issues
1. Check if email verification is enabled in settings
2. Verify email service configuration
3. Check spam folder for verification emails
4. Ensure email address is valid

### Can't Login
1. Verify credentials are correct
2. Check if account is active
3. Check if 2FA is required
4. Check CORS settings if frontend/backend on different domains

### Database Access
To check users directly in the database:
```sql
-- Check admin users
SELECT * FROM admin_users;

-- Check regular users
SELECT id, email, username, is_active, created_at FROM users;

-- Check user verification status
SELECT id, email, username, is_verified, is_active, created_at FROM users;
```

## Environment Variables Required
```bash
# Backend (.env)
DATABASE_URL=postgresql://...
SECRET_KEY=your-secret-key
OPENAI_API_KEY=your-openai-key  # For AI features

# Frontend (.env)
VITE_API_BASE_URL=https://your-backend-url.onrender.com
```

## Quick Start Commands

### 1. Create Admin (run once in Render shell)
```bash
python create_admin_simple.py
```

### 2. Register New User (Direct Registration)
```bash
curl -X POST https://your-backend.onrender.com/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "username": "newuser",
    "password": "SecurePassword123!",
    "full_name": "New User"
  }'
```

### 3. Login as User
```bash
curl -X POST https://your-backend.onrender.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "SecurePassword123!"
  }'
```

## Notes  
- The admin account is separate from regular user accounts
- Admin accounts can only manage the system, not use social media features
- Regular users can register directly and have full access to platform features
- Always use HTTPS in production
- Email verification can be enabled/disabled via environment variables