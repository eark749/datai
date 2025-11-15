# Backend API Documentation

## Base URL
```
http://localhost:8000
```

---

## 🔐 Authentication APIs
**Base Path:** `/api/auth`

### 1. Register User
- **Endpoint:** `POST /api/auth/register`
- **Auth Required:** No
- **Purpose:** Create new user account and get tokens
- **Request Body:**
  ```json
  {
    "email": "user@example.com",
    "username": "username",
    "password": "password123"
  }
  ```
- **Returns:** User info + access & refresh tokens
- **Frontend Integration:** Registration page, auto-login after signup

### 2. Login
- **Endpoint:** `POST /api/auth/login`
- **Auth Required:** No
- **Purpose:** Authenticate user and get tokens
- **Request Body:**
  ```json
  {
    "email": "user@example.com",
    "password": "password123"
  }
  ```
- **Returns:** Access token + refresh token
- **Frontend Integration:** Login page, store tokens in localStorage/cookies

### 3. Refresh Token
- **Endpoint:** `POST /api/auth/refresh`
- **Auth Required:** No (needs refresh token)
- **Purpose:** Get new access token when expired
- **Request Body:**
  ```json
  {
    "refresh_token": "your-refresh-token"
  }
  ```
- **Returns:** New access token
- **Frontend Integration:** Token refresh interceptor in axios/fetch

### 4. Logout
- **Endpoint:** `POST /api/auth/logout`
- **Auth Required:** No (needs refresh token)
- **Purpose:** Revoke refresh token
- **Request Body:**
  ```json
  {
    "refresh_token": "your-refresh-token"
  }
  ```
- **Frontend Integration:** Logout button, clear stored tokens

---

## 💬 Chat APIs
**Base Path:** `/api`

### 5. Create New Chat
- **Endpoint:** `POST /api/new`
- **Auth Required:** Yes (Bearer token)
- **Purpose:** Start a new chat session
- **Request Body:**
  ```json
  {
    "title": "My Analysis",  // optional
    "db_connection_id": "uuid"  // optional
  }
  ```
- **Returns:** Chat object with ID
- **Frontend Integration:** "New Chat" button in sidebar

### 6. Send Chat Query (Main Endpoint)
- **Endpoint:** `POST /api/query`
- **Auth Required:** Yes
- **Rate Limited:** 10 requests/minute
- **Purpose:** Process natural language query with SQL Agent + Dashboard Agent
- **Request Body:**
  ```json
  {
    "message": "Show me sales by region",
    "chat_id": "uuid",
    "db_connection_id": "uuid"
  }
  ```
- **Returns:** SQL query, data results, dashboard HTML
- **Frontend Integration:** Main chat input, display SQL + table + dashboard

### 7. List All Chats
- **Endpoint:** `GET /api/chats?skip=0&limit=50`
- **Auth Required:** Yes
- **Purpose:** Get user's chat history
- **Frontend Integration:** Sidebar chat list

### 8. Get Chat with Messages
- **Endpoint:** `GET /api/chats/{chat_id}`
- **Auth Required:** Yes
- **Purpose:** Load specific chat with all messages
- **Frontend Integration:** When clicking a chat from sidebar

### 9. Connect Database to Chat
- **Endpoint:** `PATCH /api/{chat_id}/connect-db`
- **Auth Required:** Yes
- **Purpose:** Link a database connection to existing chat
- **Request Body:**
  ```json
  {
    "db_connection_id": "uuid"
  }
  ```
- **Frontend Integration:** Database selector dropdown in chat

### 10. Delete Chat
- **Endpoint:** `DELETE /api/chats/{chat_id}`
- **Auth Required:** Yes
- **Purpose:** Remove chat and all messages
- **Frontend Integration:** Delete button in chat menu

### 11. Archive Chat
- **Endpoint:** `PATCH /api/chats/{chat_id}/archive`
- **Auth Required:** Yes
- **Purpose:** Archive/unarchive chat
- **Frontend Integration:** Archive button in chat menu

---

## 🗄️ Database Connection APIs
**Base Path:** `/api/databases`

### 12. Create Database Connection
- **Endpoint:** `POST /api/databases`
- **Auth Required:** Yes
- **Purpose:** Add new database connection
- **Request Body:**
  ```json
  {
    "name": "Production DB",
    "db_type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "database_name": "mydb",
    "username": "user",
    "password": "pass",
    "db_schema": "public"  // optional
  }
  ```
- **Supported DB Types:** postgresql, mysql, sqlite, mssql
- **Frontend Integration:** "Add Database" form/modal

### 13. List Database Connections
- **Endpoint:** `GET /api/databases?skip=0&limit=50`
- **Auth Required:** Yes
- **Purpose:** Get all user's database connections
- **Frontend Integration:** Database management page, database selector

### 14. Get Database Connection
- **Endpoint:** `GET /api/databases/{connection_id}`
- **Auth Required:** Yes
- **Purpose:** Get specific database details
- **Frontend Integration:** Edit database form

### 15. Update Database Connection
- **Endpoint:** `PUT /api/databases/{connection_id}`
- **Auth Required:** Yes
- **Purpose:** Update connection details
- **Request Body:** Same as create (all fields optional)
- **Frontend Integration:** Edit database form submission

### 16. Delete Database Connection
- **Endpoint:** `DELETE /api/databases/{connection_id}`
- **Auth Required:** Yes
- **Purpose:** Remove database connection
- **Frontend Integration:** Delete button in database list

### 17. Test Database Connection
- **Endpoint:** `POST /api/databases/{connection_id}/test`
- **Auth Required:** Yes
- **Purpose:** Verify database connection works
- **Returns:** Success status, response time, error message
- **Frontend Integration:** "Test Connection" button in database form

---

## 📊 Query History APIs
**Base Path:** `/api/history`

### 18. Get Query History
- **Endpoint:** `GET /api/history/queries`
- **Auth Required:** Yes
- **Query Parameters:**
  - `db_connection_id` (optional): Filter by database
  - `execution_status` (optional): success/error/timeout
  - `start_date` (optional): ISO datetime
  - `end_date` (optional): ISO datetime
  - `skip` (default: 0): Pagination
  - `limit` (default: 50): Page size
- **Purpose:** View past query executions
- **Frontend Integration:** History page with filters

### 19. Get Query Details
- **Endpoint:** `GET /api/history/queries/{query_id}`
- **Auth Required:** Yes
- **Purpose:** View specific query execution details
- **Frontend Integration:** Clicking on history item

---

## 🏥 Health Check APIs
**Base Path:** `/`

### 20. Root Endpoint
- **Endpoint:** `GET /`
- **Auth Required:** No
- **Purpose:** API status check
- **Returns:** API name, version, status

### 21. Health Check
- **Endpoint:** `GET /health`
- **Auth Required:** No
- **Purpose:** Service health monitoring
- **Returns:** Health status, environment

---

## 🔒 Authentication Header Format

All authenticated endpoints require:
```
Authorization: Bearer <access_token>
```

---

## 📝 Response Formats

### Success Response
```json
{
  "id": "uuid",
  "field": "value",
  ...
}
```

### Error Response
```json
{
  "detail": "Error message"
}
```

---

## 🎯 Frontend Integration Priority

1. **Authentication Flow:** Implement login/register first
2. **Database Setup:** Add database connection management
3. **Chat Interface:** Create chat UI with query endpoint
4. **History View:** Add query history viewing
5. **Dashboard Display:** Render HTML dashboards from query responses

---

## 🔧 Key Features

- **Two-Agent System:** 
  - Agent 1 (SQL): Converts natural language → SQL
  - Agent 2 (Dashboard): Generates HTML visualizations
- **Secure:** Password encryption, JWT tokens
- **Rate Limited:** 10 queries/minute on main endpoint
- **CORS Enabled:** Configure allowed origins in settings
- **Database Support:** PostgreSQL, MySQL, SQLite, MS SQL Server

---

## 📦 API Documentation

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

