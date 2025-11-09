# Kriya Authentication Backend

Phone-based authentication service built with FastAPI for Plane integration.

## Features

- 📱 Phone number-based user registration
- 🔐 Token-based authentication
- 🔄 Automatic login for existing users
- 🗄️ PostgreSQL database
- 🚀 Fast and async with FastAPI
- 🔒 Secure server-to-server communication with Plane

## Architecture

```
User → Frontend → Kriya Backend (generates token) → Plane Backend (validates token) → Authenticated
```

## Installation

### Prerequisites

- Python 3.10+
- PostgreSQL 13+

### Setup

1. **Create PostgreSQL database:**

```bash
# Login to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE kriya_db;

# Exit
\q
```

2. **Install dependencies:**

```bash
cd kriya-backend
pip install -r requirements.txt
```

3. **Configure environment:**

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your settings
nano .env
```

4. **Run the server:**

```bash
# Development mode with auto-reload
python -m app.main

# Or using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

5. **Verify installation:**

Visit: http://localhost:8001/docs for API documentation

## API Endpoints

### 1. Register/Login User

**POST** `/api/auth/register`

Register new user or login existing user with phone number.

**Request:**
```json
{
  "phone_number": "+1234567890",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Registration successful",
  "token": "kriya_8f7d9c2a-4b5e-11ef-9a3d-0242ac120002",
  "user": {
    "id": "uuid-here",
    "phone_number": "+1234567890",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "created_at": "2024-11-09T10:30:00Z"
  },
  "expires_at": "2024-11-10T10:30:00Z"
}
```

### 2. Validate Token

**POST** `/api/auth/validate-token`

Validate authentication token (used by Plane backend).

**Headers:**
```
X-API-Key: shared-secret-key-for-plane-kriya-communication
```

**Request:**
```json
{
  "token": "kriya_8f7d9c2a-4b5e-11ef-9a3d-0242ac120002"
}
```

**Response:**
```json
{
  "valid": true,
  "user": {
    "id": "uuid-here",
    "phone_number": "+1234567890",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "created_at": "2024-11-09T10:30:00Z"
  },
  "message": "Token is valid"
}
```

### 3. Get User Info

**GET** `/api/auth/user?token=<token>`

Get user information by token.

### 4. Logout

**DELETE** `/api/auth/logout?token=<token>`

Invalidate user token.

## Database Schema

### Users Table
```sql
- id (UUID, Primary Key)
- phone_number (String, Unique)
- first_name (String)
- last_name (String)
- email (String, Optional)
- created_at (DateTime)
- updated_at (DateTime)
```

### Tokens Table
```sql
- id (UUID, Primary Key)
- user_id (UUID, Foreign Key → users.id)
- token (String, Unique)
- is_active (Boolean)
- expires_at (DateTime)
- created_at (DateTime)
```

## Security

- **API Key Authentication**: Server-to-server endpoints require API key
- **Token Expiry**: Tokens expire after configured hours (default: 24 hours)
- **Phone Validation**: Basic phone number format validation
- **CORS**: Configured allowed origins

## Configuration

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` |
| `PORT` | Server port | `8001` |
| `TOKEN_EXPIRY_HOURS` | Token validity period | `24` |
| `PLANE_API_KEY` | Shared secret with Plane | Required |
| `ALLOWED_ORIGINS` | CORS allowed origins | `[]` |

## Development

```bash
# Run with auto-reload
uvicorn app.main:app --reload --port 8001

# Access API docs
open http://localhost:8001/docs

# Run tests (if added)
pytest
```

## Production Deployment

1. Set `DEBUG=False` in `.env`
2. Use strong `SECRET_KEY` and `PLANE_API_KEY`
3. Configure proper `DATABASE_URL`
4. Use production WSGI server (uvicorn with workers):

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 4
```

## Integration with Plane

1. Ensure Plane backend has these environment variables:
```bash
KRIYA_BACKEND_URL=http://localhost:8001
KRIYA_API_KEY=shared-secret-key-for-plane-kriya-communication
```

2. The API key must match in both Kriya and Plane backends.

## Troubleshooting

**Database Connection Error:**
- Ensure PostgreSQL is running
- Check `DATABASE_URL` in `.env`
- Verify database exists

**CORS Error:**
- Add your frontend URL to `ALLOWED_ORIGINS`
- Restart the server

**Token Validation Failed:**
- Check API key matches between Kriya and Plane
- Ensure token hasn't expired
- Verify token exists in database

## License

MIT License

