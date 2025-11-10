# Backend Setup Guide

## Prerequisites

- Python 3.11 or higher
- PostgreSQL 14 or higher
- pip (Python package manager)

## Installation Steps

### 1. Create Virtual Environment

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the backend directory:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# App Database (PostgreSQL)
DATABASE_URL=postgresql://your_user:your_password@localhost:5432/datai_app

# Anthropic API Key
ANTHROPIC_API_KEY=sk-ant-your-api-key-here

# JWT Secret (generate with: openssl rand -hex 32)
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database Encryption Key (generate with Python command below)
DB_ENCRYPTION_KEY=your-fernet-key-here

# App Configuration
ENVIRONMENT=development
DEBUG=True
```

### 4. Generate Encryption Key

```python
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output to `DB_ENCRYPTION_KEY` in `.env`.

### 5. Setup Database

Create the PostgreSQL database:

```sql
CREATE DATABASE datai_app;
```

Run migrations:

```bash
alembic upgrade head
```

### 6. Run the Application

```bash
# Development mode (with auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 7. Access the API

- **API Documentation (Swagger UI)**: http://localhost:8000/docs
- **Alternative Documentation (ReDoc)**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Testing

Run tests:

```bash
pytest
```

Run tests with coverage:

```bash
pytest --cov=app --cov-report=html
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login
- `POST /api/auth/refresh` - Refresh access token
- `POST /api/auth/logout` - Logout (revoke refresh token)

### Database Connections
- `POST /api/databases` - Create database connection
- `GET /api/databases` - List database connections
- `GET /api/databases/{id}` - Get database connection
- `PUT /api/databases/{id}` - Update database connection
- `DELETE /api/databases/{id}` - Delete database connection
- `POST /api/databases/{id}/test` - Test database connection

### Chat (Main Feature)
- `POST /api/query` - Send natural language query and get dashboard
- `GET /api/chats` - List all chats
- `GET /api/chats/{id}` - Get chat with messages
- `DELETE /api/chats/{id}` - Delete chat
- `PATCH /api/chats/{id}/archive` - Archive/unarchive chat

### History
- `GET /api/history/queries` - Get query history
- `GET /api/history/queries/{id}` - Get query details

## Architecture

### Two-Agent System

1. **Agent 1 (SQL Agent)**
   - Converts natural language to SQL
   - Validates queries for safety
   - Executes queries on user's database
   - Returns data results

2. **Agent 2 (Dashboard Agent)**
   - Analyzes data structure
   - Selects appropriate visualizations
   - Generates interactive HTML dashboards
   - Uses Chart.js for rendering

### Security Features

- JWT-based authentication
- Bcrypt password hashing
- SQL injection prevention
- Read-only database access for user queries
- Encrypted database credentials (Fernet)
- Rate limiting (10 requests/minute for chat endpoint)
- CORS configuration
- Request logging

### Database Structure

- **App Database**: Stores users, chats, messages, query history
- **User's Business Database**: Connected dynamically, read-only access

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql  # Linux
brew services list                 # Mac

# Test connection
psql -U your_user -d datai_app -h localhost
```

### Migration Issues

```bash
# Reset database (WARNING: deletes all data)
alembic downgrade base
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"
```

### Import Errors

```bash
# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

## Development

### Code Structure

```
backend/
├── app/
│   ├── agents/          # AI agents (SQL, Dashboard)
│   ├── api/             # API endpoints
│   ├── models/          # Database models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   ├── tools/           # Agent tools
│   └── utils/           # Utilities
├── alembic/             # Database migrations
├── tests/               # Test suite
└── requirements.txt     # Dependencies
```

### Adding New Endpoints

1. Create Pydantic schemas in `app/schemas/`
2. Create API routes in `app/api/`
3. Add router to `app/main.py`
4. Document in Swagger (automatic)

### Database Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "add new table"

# Apply migration
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Production Deployment

### Environment Variables

Set `ENVIRONMENT=production` and `DEBUG=False` in production.

### Security Checklist

- [ ] Strong JWT_SECRET_KEY
- [ ] Strong DB_ENCRYPTION_KEY
- [ ] HTTPS enabled
- [ ] CORS origins restricted
- [ ] Database credentials secured
- [ ] Rate limiting enabled
- [ ] Logging configured
- [ ] Error messages sanitized

### Performance Optimization

- Use connection pooling
- Enable query caching
- Configure worker processes
- Set up load balancing
- Monitor API performance

## Support

For issues or questions:
- Check logs: `tail -f app.log`
- Review API documentation: http://localhost:8000/docs
- Run tests: `pytest -v`


