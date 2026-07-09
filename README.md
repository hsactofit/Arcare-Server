# Arcar Wellness Backend API

This is the FastAPI backend setup for the **Atham Wellness** mobile application onboarding flow. It supports user creation, profile storage, goal selection, notification preferences, health connect synchronization, and dynamically calculated dashboard widgets.

## Tech Stack
* **Python 3.14+**
* **FastAPI** (API routing & documentation)
* **SQLAlchemy** (ORM)
* **SQLite** (Default database, self-contained)
* **Uvicorn** (Asynchronous web server)

## Project Structure
```text
/run/media/ponyo/New Volume/Ocavior/back-end/Arcare-Server/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application startup, CORS & router configs
│   ├── config.py        # Settings loader with pydantic-settings
│   ├── database.py      # Database engine, sessionmaker & get_db dependency
│   ├── models.py        # SQLAlchemy models (User, Profile, Goals, Permissions, HealthData)
│   ├── schemas.py       # Pydantic validation schemas
│   ├── crud.py          # Create, read, and update functions
│   └── routers/
│       ├── __init__.py
│       ├── onboarding.py # Endpoints for onboarding submission & status query
│       ├── health.py     # Endpoints for syncing wearable health data
│       └── dashboard.py  # Endpoints for loading dynamic dashboard widgets
├── requirements.txt     # Dependency list
└── arcar.db             # Auto-generated SQLite database file (created on start)
```

## Quick Start Guide

### 1. Create a Virtual Environment
Navigate to this directory and create a virtual environment:
```bash
python3 -m virtualenv venv
```

### 2. Activate the Virtual Environment
* **Linux/macOS:**
  ```bash
  source venv/bin/activate
  ```
* **Windows:**
  ```cmd
  venv\Scripts\activate
  ```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Server
Start the local API server with Uvicorn:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The server will start running at `http://localhost:8000`. You can test it by opening `http://localhost:8000/docs` in your browser to view the interactive Swagger UI.

---

## API Documentation

### 1. Authentication API

#### `POST /api/auth/signup`
Registers a new local user with email and password, hashing their credentials securely.
* **Request Body:**
```json
{
  "email": "testuser@arcar.com",
  "password": "securepassword123",
  "name": "Test User"
}
```
* **Response (201 Created):**
```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "user": {
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
}
```

#### `POST /api/auth/login`
Authenticates local credentials, returning JWT keys and complete user data (including profile, goals, and notification rules if they exist).
* **Request Body:**
```json
{
  "email": "testuser@arcar.com",
  "password": "securepassword123"
}
```
* **Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "testuser@arcar.com",
    "name": "Test User",
    "provider": "email",
    "onboarding_completed": true,
    "completed_at": "2026-06-27T22:13:26.089207",
    "profile": {
      "dob": "1995-05-15",
      "gender": "Male",
      "height": 175.0,
      "weight": 75.0
    },
    "goals": [
      "Lose Weight",
      "Stay Active"
    ],
    "permissions": {
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
  }
}
```

#### `POST /api/auth/social-login`
Registers or authenticates Google/Apple OAuth single sign-ons.
* **Request Body:**
```json
{
  "email": "socialuser@gmail.com",
  "name": "Social Google User",
  "provider": "google"
}
```
* **Response (200 OK):** Returns JWT access/refresh tokens and user details.

#### `POST /api/auth/refresh`
Exchanges a valid refresh token for a newly issued access token.
* **Request Body:**
```json
{
  "refresh_token": "eyJhbGciOi..."
}
```
* **Response (200 OK):** Returns new `access_token` alongside current `refresh_token` and user details.

---

### 2. Onboarding API

#### `POST /api/onboarding`
Saves or updates the onboarding information.
* **Request Body JSON Example:**
```json
{
  "auth": {
    "name": "Prabhash Shankar",
    "email": "prabhashshankar3360@gmail.com",
    "provider": "google"
  },
  "goals": [
    "Lose Weight",
    "Stay Active",
    "Eat Healthier"
  ],
  "profile": {
    "dob": "1998-01-01",
    "gender": "Female",
    "height": 180,
    "weight": 80
  },
  "permissions": {
    "notifications": {
      "ai_tips": true,
      "rewards": false,
      "daily_reminder": true,
      "sleep_reminder": true,
      "activity_reminder": true,
      "challenge_updates": false,
      "hydration_reminder": true
    },
    "health_connect_connected": true
  },
  "completed_at": "2026-06-27T22:13:26.089207Z",
  "onboarding_completed": true
}
```
* **Response (201 Created):**
```json
{
  "message": "Onboarding completed and saved successfully"
}
```

#### `GET /api/onboarding/{email}`
Fetches onboarding details for a given email address.

#### `GET /api/onboarding/status/{email}`
Checks whether the user has completed onboarding.
* **Response:**
```json
{
  "onboarding_completed": true,
  "completed_at": "2026-06-27T22:13:26.089207",
  "exists": true
}
```

---

### 2. Wearable Health Sync API

#### `POST /api/health/sync/{email}`
Syncs wearable metrics from Google Health Connect or Apple Health.
* **Request Body JSON Example:**
```json
{
  "steps": 8540,
  "calories": 420,
  "sleep_duration_hours": 7.5,
  "water_intake_ml": 1800,
  "workouts_count": 2,
  "heart_rate_bpm": 74
}
```
* **Response:** Returns updated health metrics JSON.

#### `GET /api/health/data/{email}`
Fetches the latest synced health data.

#### `POST /api/health/metric/{email}`
Logs or updates a single health metric for the user. If the metric is `steps`, it automatically calculates and updates the `calories` burned.
* **Request Body JSON Example:**
```json
{
  "metric": "steps",
  "value": 10000,
  "date": "2026-07-09"
}
```
* **Response (200 OK):**
```json
{
  "message": "Successfully logged steps value of 10000.0",
  "metric": "steps",
  "value": 10000.0,
  "date": "2026-07-09",
  "calories_burned": 429,
  "health_data": {
    "date": "2026-07-09",
    "steps": 10000,
    "calories": 429,
    "sleep_duration_hours": 0.0,
    "water_intake_ml": 0,
    "workouts_count": 0,
    "heart_rate_bpm": 70,
    "updated_at": "2026-07-09T02:20:00Z"
  }
}
```

#### `GET /api/health/graph/{email}`
Retrieves aggregated health metric graph data for the user based on the selected period: `days` (last 7 days daily), `weeks` (last 4 weeks weekly aggregates), `month` (last 3 months monthly aggregates), or `years` (last 5 years yearly aggregates). Includes overall averages, totals (for sum-based metrics), and personalized health feedback.
* **Query Parameters:**
  * `metric` (required): The metric to fetch (`steps`, `calories`, `sleep`, `water`, `workouts`, or `heart_rate`).
  * `period` (optional, default: `days`): Aggregation period (`days`, `weeks`, `month`, or `years`).
* **Response (200 OK):**
```json
{
  "metric": "steps",
  "period": "days",
  "data": [
    { "label": "2026-07-08", "value": 8500.0 },
    { "label": "2026-07-09", "value": 10000.0 }
  ],
  "feedback": "Outstanding! You average 9250 steps, maintaining a highly active lifestyle. Meeting this level consistently is excellent for cardiovascular health, weight management, and metabolic rate.",
  "average": 9250.0,
  "total": 18500.0
}
```

---

### 3. Dashboard API

#### `GET /api/dashboard/{email}`
Compiles a customized daily dashboard based on the user's profile, goals, and synced health metrics. It outputs:
1. **Wellness Score**: Compiled dynamically from steps, calories, sleep, and hydration levels relative to targets.
2. **Daily Summary**: Custom greeting containing profile-derived insights.
3. **Recommendations**: Bullet points tailored to their specific onboarding goals.
4. **Widgets**: Detailed widget cards including `Daily Steps`, `Calories Burned`, `Water Intake`, `Active Challenges`, `Rewards Points`, and `AI Wellness Buddy` statuses.
