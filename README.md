# Kriya Authentication Backend

Phone-based authentication service built with FastAPI for Plane integration.

## Features

- 📱 Phone number-based user registration
- 🔐 JWT-based authentication (stateless with revocation support)
- 🔄 Automatic login for existing users
- 🗄️ PostgreSQL database
- 🚀 Fast and async with FastAPI
- 🔒 Secure server-to-server communication with Plane
- ✅ Token revocation support (logout functionality)

## Architecture

```
User → Frontend → Kriya Backend (generates JWT) → Plane Backend (validates JWT) → Authenticated
```

**JWT Token Flow:**
1. User registers/logs in → Kriya generates JWT token
2. JWT contains: user_id, phone_number, token_version, expiration, issuer
3. Plane validates JWT by calling Kriya
4. Kriya decodes JWT, queries user by user_id (one DB query)
5. Kriya checks token_version matches user.token_version (revocation)
6. **No token storage in database!** - JWT is truly stateless

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

3. **Run database migration (add token_version column):**

```bash
# Option 1: Run migration SQL file
psql -U postgres -d kriya_db -f migrations/add_token_version.sql

# Option 2: Run manually
psql -U postgres -d kriya_db -c "ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0;"
```

3. **Configure environment:**

Create a `.env` file in the `kriya-backend` directory with the following:

```bash
# Application
DEBUG=True

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/kriya_db

# JWT Security (CHANGE IN PRODUCTION!)
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production-min-32-chars-recommended
JWT_ALGORITHM=HS256
TOKEN_EXPIRY_HOURS=24

# Plane Integration
PLANE_API_KEY=shared-secret-key-for-plane-kriya-communication

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:8000
```

**Important:** Use a strong `JWT_SECRET_KEY` (minimum 32 characters recommended) in production!

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
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMTIzZTQ1NjctZTg5Yi0xMmQzLWE0NTYtNDI2NjE0MTc0MDAwIiwicGhvbmVfbnVtYmVyIjoiKzEyMzQ1Njc4OTAiLCJleHAiOjE2OTk5OTk5OTksImlhdCI6MTY5OTkxMzU5OSwiaXNzIjoia3JpeWEtYXV0aCJ9.signature",
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

**Note:** The token is now a JWT (JSON Web Token) containing user information.

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
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
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
- token_version (Integer) -- For JWT revocation ✅
- created_at (DateTime)
- updated_at (DateTime)
```

**How JWT Revocation Works:**
- JWT contains `token_version` (e.g., 0)
- When user logs out, increment `user.token_version` to 1
- All old JWTs with version 0 become invalid
- No need to store JWT strings in database! ✅

### Tokens Table (Optional)
```sql
- id (UUID, Primary Key)
- user_id (UUID, Foreign Key → users.id)
- token (String) -- For audit logging only
- expires_at (DateTime)
- created_at (DateTime)
```

**Note:** The tokens table is now **optional** and only used for audit logging. JWT validation does NOT require token storage!

## Security

- **JWT Authentication**: Tokens are cryptographically signed and self-validating
- **API Key Authentication**: Server-to-server endpoints require API key
- **Token Expiry**: JWTs expire after configured hours (default: 24 hours)
- **Token Revocation**: Revoked tokens tracked in database for logout functionality
- **Phone Validation**: Basic phone number format validation
- **CORS**: Configured allowed origins

### JWT Security Benefits
- ✅ **Stateless**: No database lookup needed for validation (except revocation check)
- ✅ **Tamper-proof**: Cryptographically signed to prevent modification
- ✅ **Industry standard**: Well-tested and widely adopted
- ✅ **Performance**: Fast validation via signature verification

## Configuration

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` |
| `PORT` | Server port | `8001` |
| `JWT_SECRET_KEY` | Secret key for JWT signing | Required (min 32 chars) |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
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
2. Use strong `JWT_SECRET_KEY` (minimum 32 characters, use random string)
3. Use strong `PLANE_API_KEY` 
4. Configure proper `DATABASE_URL`
5. Use production WSGI server (uvicorn with workers):

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 4
```

**Generate Strong JWT Secret:**
```python
import secrets
print(secrets.token_urlsafe(32))  # Generates a secure 32-byte secret
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

