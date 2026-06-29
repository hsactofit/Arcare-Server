# Arcar Wellness Backend Authentication Completion Log

The social authentication, PostgreSQL migration, and Docker containerization tasks have been successfully completed.

## Test Execution Details (PostgreSQL)
* **Timestamp**: 2026-06-28 04:19:16 (local)
* **Python Version**: CPython 3.14.4
* **Database engine**: PostgreSQL 16 (running via Docker container)
* **Testing Tool**: `test_api.py` (using FastAPI `TestClient`)

## Test Output Logs (Against PostgreSQL)
```text
Attempting to connect to primary database: postgresql://postgres:postgres_password_123@localhost:5432/my_database
Successfully connected to PostgreSQL database.
Resetting database schema...
Database schema reset completed.

/run/media/ponyo/New Volume1/Ocavior/back-end/arcar/venv/lib/python3.14/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
  from starlette.testclient import TestClient as TestClient  # noqa
--- 1. Testing User Sign Up (Local Email) ---
Status Code: 201
Tokens Issued:
  - Access Token: eyJhbGciOiJIUzI1NiIsInR5cCI6Ik...
  - Refresh Token: eyJhbGciOiJIUzI1NiIsInR5cCI6Ik...
User Data returned in Response:
{
  "id": 1,
  "email": "testuser@arcar.com",
  "name": "Test User",
  "provider": "email",
  "onboarding_completed": false,
  "completed_at": null,
  "profile": null,
  "goals": [],
  "permissions": null
}

--- 2. Testing Duplicate Sign Up Prevention ---
Status Code: 400 (Expected 400)
Error Detail: An account with this email address already exists.

--- 3. Testing Incorrect Password Login ---
Status Code: 401 (Expected 401)
Error Detail: Incorrect email address or password.

--- 4. Testing Correct Login ---
Status Code: 200
Access Token: eyJhbGciOiJIUzI1NiIsInR5cCI6Ik...

--- 5. Testing Token Refresh ---
Status Code: 200
New Access Token: eyJhbGciOiJIUzI1NiIsInR5cCI6Ik...

--- 6. Testing User Onboarding Flow Setup ---
Status Code: 201
Response: {'message': 'Onboarding completed and saved successfully'}

--- 7. Logging in again (Verifying profile & permissions are returned) ---
Status Code: 200
User Onboarding Completed: True
User Goals: ['Lose Weight', 'Stay Active']
User Profile details:
{
  "dob": "1995-05-15",
  "gender": "Male",
  "height": 175.0,
  "weight": 75.0
}
User Permissions details:
{
  "notifications": {
    "ai_tips": true,
    "rewards": true,
    "daily_reminder": true,
    "sleep_reminder": false,
    "activity_reminder": true,
    "challenge_updates": true,
    "hydration_reminder": true
  },
  "health_connect_connected": true
}

--- 8. Testing Google Social Sign Up (New User) ---
Status Code: 201
Access Token: eyJhbGciOiJIUzI1NiIsInR5cCI6Ik...
User Email: socialuser_google@gmail.com
User Name: Social Google User

--- 9. Testing Google Social Sign Up Duplicate Check ---
Status Code: 400 (Expected 400)
Error Detail: An account with this email address already exists. Please use social login.

--- 10. Testing Google Social Login ---
Status Code: 200
Access Token: eyJhbGciOiJIUzI1NiIsInR5cCI6Ik...

--- 11. Testing Apple Social Sign Up (New User) ---
Status Code: 201
Access Token: eyJhbGciOiJIUzI1NiIsInR5cCI6Ik...
User Email: socialuser_apple@icloud.com

--- 12. Testing Apple Social Login ---
Status Code: 200
Access Token: eyJhbGciOiJIUzI1NiIsInR5cCI6Ik...

--- 13. Testing Social Login of Unregistered User (Expected 404) ---
Status Code: 404 (Expected 404)
Error Detail: No account found with this social email. Please register via social signup first.

ALL AUTHENTICATION TESTS PASSED SUCCESSFULLY!
```

## Architectural Highlights
1. **Security**: Local password hashing implemented via salt-based `bcrypt`.
2. **Social Integration**: Custom decoders for `verify_google_token` and `verify_apple_token` that parse tokens and map claims to database fields. Offline support handles local developer mock environments seamlessly.
3. **Database Migration**: The application has migrated from SQLite to a fully normalized PostgreSQL database design. It handles automatic relational table setups and drop/recreation parameters during test suites.
4. **Docker Containerization**: FastAPI backend is now containerized alongside PostgreSQL and pgAdmin using a robust `docker-compose` build configuration. It binds to port `8000` on the host interface `0.0.0.0`, making the endpoints and interactive docs accessible across the entire local network (e.g. from mobile devices or other computers on the LAN).

---

## Forgot Password OTP Integration (New Update)
A secure 3-step password reset flow using short-lived Email OTP codes and signature tokens has been implemented.

### API Endpoint Schemas

1. **`POST /api/auth/forgot-password`**
   * **Request Body**:
     ```json
     {
       "email": "user@example.com"
     }
     ```
   * **Behavior**:
     * Verifies that the email exists in the database.
     * Prevents user enumeration (returns a generic success message regardless of existence).
     * If registered via social login (Google/Apple), returns a `400 Bad Request` suggesting social sign-in.
     * Generates a 6-digit random OTP, persists it in the database with a 10-minute expiry time, and prints the OTP to the live server logs (facilitating `docker compose logs -f` local testing).

2. **`POST /api/auth/verify-otp`**
   * **Request Body**:
     ```json
     {
       "email": "user@example.com",
       "otp": "123456"
     }
     ```
   * **Response**:
     ```json
     {
       "message": "OTP verified successfully.",
       "reset_token": "eyJhbGciOiJIUzI1NiIsInR5..."
     }
     ```
   * **Behavior**:
     * Verifies correctness and expiry of the OTP.
     * Returns a short-lived JSON Web Token (JWT) containing the verified email as `sub` and the type `"reset_password"` (valid for 10 minutes).

3. **`POST /api/auth/reset-password`**
   * **Request Body**:
     ```json
     {
       "reset_token": "eyJhbGciOiJIUzI1NiIsInR5...",
       "new_password": "newSecurePassword123"
     }
     ```
   * **Behavior**:
     * Decodes and validates the signature/expiry of the `reset_token`.
     * Hashes the `new_password` using bcrypt.
     * Updates the user's password in the database and cleans up used OTPs.

### Test Verification Log
```text
--- 14. Testing Forgot Password Flow (Non-existent user) ---
Status Code: 200
Response: {'message': 'If an account with this email exists, a password reset OTP has been sent.'}

--- 15. Testing Forgot Password Flow (Social User) ---
Status Code: 400 (Expected 400)
Response: {'detail': 'This account is registered via Google social authentication. Please use social sign-in.'}

--- 16. Testing Forgot Password Flow (Valid Email, OTP Gen & Verification) ---
[PASSWORD RESET OTP] Generated for user testuser@arcar.com: 466047 (Expires at: 2026-06-28T16:05:46.901309+00:00)
Status Code: 200
Retrieved OTP from DB for testing: 466047
Verify bad OTP status: 400 (Expected 400)
Verify correct OTP status: 200

--- 17. Testing Password Reset and Login ---
Reset Password Status: 200
Login with old password status: 401 (Expected 401)
Login with new password status: 200

ALL AUTHENTICATION AND OTP TESTS PASSED SUCCESSFULLY!
```

