# Agentic SQL Dashboard - Backend

A FastAPI backend application with AI-powered SQL generation and dashboard creation capabilities.

## Features

- **Dual AI Agents**: SQL Generator and Dashboard Creator powered by Anthropic Claude
- **JWT Authentication**: Secure user authentication with access and refresh tokens
- **PostgreSQL Integration**: Dual database architecture (app data + user business data)
- **Chat History**: Full conversation tracking with context awareness
- **Auto-generated Swagger UI**: Interactive API documentation at `/docs`

## Project Structure

```
backend/
├── app/
│   ├── models/          # SQLAlchemy ORM models
│   ├── schemas/         # Pydantic validation schemas
│   ├── api/             # API route handlers
│   ├── agents/          # AI agent implementations
│   ├── tools/           # Agent tools
│   ├── services/        # Business logic
│   └── utils/           # Utilities
├── alembic/             # Database migrations
├── tests/               # Unit & integration tests
└── requirements.txt
```

## Setup

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Configure environment variables**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Initialize database**:
```bash
alembic upgrade head
```

4. **Run the application**:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

5. **Access Swagger UI**:
Open http://localhost:8000/docs in your browser

## Environment Variables

See `.env.example` for required configuration variables.

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT tokens
- `POST /api/auth/refresh` - Refresh access token

### Database Connections
- `POST /api/databases` - Add new database connection
- `GET /api/databases` - List user's database connections
- `DELETE /api/databases/{id}` - Remove database connection

### Chat
- `POST /api/chat` - Send query and get dashboard
- `GET /api/chats` - List user's chats
- `GET /api/chats/{chat_id}` - Get specific chat
- `DELETE /api/chats/{chat_id}` - Delete chat

### History
- `GET /api/history/queries` - Get query history
- `GET /api/history/chats/{chat_id}` - Get chat history

## Database Schema

The application uses two PostgreSQL databases:

1. **App Database**: Stores users, auth, chats, messages, query history
2. **User Business Database**: User's data to be queried (read-only access)

## Security

- JWT-based authentication
- Bcrypt password hashing
- SQL injection prevention
- Read-only database access for user queries
- Encrypted database credentials
- CORS configuration

## Development

Run tests:
```bash
pytest tests/
```

Generate new migration:
```bash
alembic revision --autogenerate -m "description"
```

## License

Proprietary

