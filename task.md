# Arcar Wellness Backend Tasks

## Social Authentication Integration
- [x] Add explicit endpoints for Social Sign Up and Social Login (Google and Apple).
- [x] Implement robust token verification logic for Google (using Google ID Token verification) and Apple (parsing Apple ID token details).
- [x] Allow mock/developer bypass for offline local testing using `mock_google_token` and `mock_apple_token`.
- [x] Update database models/handlers to handle user creation during social signup.
- [x] Update validation schemas for social signup and login.
- [x] Add comprehensive test cases in `test_api.py` for social signup, login, and error states.
- [x] Run the tests and document logs in `complete.md`.

## PostgreSQL and Docker Containerization (Local Network Access)
- [x] Add `psycopg2-binary` package dependency to support PostgreSQL connection.
- [x] Update `app/config.py` to prioritize PostgreSQL database connections via environment variables.
- [x] Create a `Dockerfile` for the FastAPI application.
- [x] Create a `docker-compose.yml` in the project root merging PostgreSQL and pgAdmin with our FastAPI backend.
- [x] Configure the FastAPI service inside docker-compose to bind to host `0.0.0.0:8000` to make it accessible to other systems on the local network.
- [x] Create a local `.env` configuration file inside the project directory.
- [x] Update `test_api.py` and run verification tests on PostgreSQL.
- [x] Document the successful migration in `complete.md`.

## Forgot Password OTP Flow
- [x] Create database model `PasswordResetOTP` for managing generated OTPs.
- [x] Define Pydantic request and response schemas.
- [x] Implement OTP generation, logging to terminal console, and database persistence.
- [x] Implement secure 3-step endpoints: `/forgot-password`, `/verify-otp`, and `/reset-password`.
- [x] Add automated test cases for OTP flows in `test_api.py`.
- [x] Run test suite and document in `complete.md`.

