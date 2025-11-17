# LangGraph Multi-Agent System Setup Guide

## Overview

This application now uses **LangGraph** for multi-agent orchestration with three specialized agents:

1. **Supervisor Agent** - Primary conversational interface, handles general queries and routes to specialized agents
2. **SQL Agent** - Database interaction specialist with SQL generation, validation, and execution
3. **Dashboard Agent** - Visualization specialist that creates interactive HTML dashboards

## Architecture

```
User Query
    ↓
┌──────────────────────────────────────────────┐
│   SUPERVISOR AGENT (Primary Interface)       │
│   - Handles general conversation             │
│   - Classifies intent                        │
│   - Routes to specialized agents             │
│   - Aggregates responses                     │
└──────────────────────────────────────────────┘
         ↓                            ↓
    [DIRECT RESPONSE]    OR    [DELEGATE TO AGENTS]
         ↓                            ↓
    General queries            ┌────────┐  ┌──────────┐
    answered directly          │  SQL   │  │DASHBOARD │
                               │ AGENT  │  │  AGENT   │
                               └────────┘  └──────────┘
```

## Prerequisites

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

This will install:
- `langgraph>=0.2.0` - Multi-agent orchestration framework
- `langchain>=0.3.0` - LLM application framework
- `langchain-anthropic>=0.2.0` - Claude integration for LangChain
- `redis>=5.0.0` - State persistence
- `jinja2>=3.1.2` - HTML templating for dashboards

### 2. Install and Start Redis

#### Option A: Docker (Recommended)

```bash
docker run -d \
  --name datai-redis \
  -p 6379:6379 \
  redis:latest
```

#### Option B: Windows

1. Download Redis for Windows from: https://github.com/microsoftarchive/redis/releases
2. Install and start the Redis service
3. Or use WSL: `sudo service redis-server start`

#### Option C: MacOS

```bash
brew install redis
brew services start redis
```

#### Option D: Linux

```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

### 3. Configure Environment Variables

Update your `.env` file (use `env.template` as reference):

```bash
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Agent Configuration
AGENT_MAX_RETRIES=1
AGENT_TIMEOUT=30
SQL_ROW_LIMIT=10000
DASHBOARD_MAX_CHARTS=5
SESSION_TTL_MINUTES=30
```

### 4. Verify Redis Connection

Test that Redis is accessible:

```bash
# From command line
redis-cli ping
# Should return: PONG

# Or from Python
python -c "import redis; r = redis.Redis(); print(r.ping())"
# Should return: True
```

## Running the Application

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

You should see:

```
============================================================
🚀 Starting Application...
============================================================
   🔄 Initializing Redis...
   ✅ Redis service ready
   🔄 Initializing Claude service...
   ✅ Claude service ready
   🔄 Loading agent modules...
   ✅ Agent modules loaded

============================================================
✅ Application Ready!
   📊 Multi-Agent System: ACTIVE
   🎯 Supervisor Agent: READY
   🗄️  SQL Agent: READY
   📈 Dashboard Agent: READY
============================================================
```

## Testing the Agents

### 1. Run Unit Tests

```bash
cd backend
pytest tests/test_agents/ -v
```

### 2. Test Endpoints

#### General Query (Supervisor Agent)

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "message": "What can you do?",
    "chat_id": null,
    "db_connection_id": null
  }'
```

Expected Response:
```json
{
  "message": "I can help you query databases, generate SQL, and create interactive dashboards...",
  "agent_used": "supervisor"
}
```

#### SQL Query (SQL Agent)

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "message": "How many users do we have?",
    "chat_id": null,
    "db_connection_id": "YOUR_DB_ID"
  }'
```

Expected Response:
```json
{
  "message": "You have 1,247 users in the database.",
  "sql_query": "SELECT COUNT(*) as user_count FROM users LIMIT 10000",
  "data": [{"user_count": 1247}],
  "agent_used": "sql"
}
```

#### Dashboard Creation (SQL + Dashboard Agents)

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "message": "Show me sales by region",
    "chat_id": null,
    "db_connection_id": "YOUR_DB_ID"
  }'
```

Expected Response:
```json
{
  "message": "Here's a visualization of sales by region...",
  "sql_query": "SELECT region, SUM(sales) as total FROM orders GROUP BY region LIMIT 10000",
  "data": [...],
  "dashboard_html": "<html>...</html>",
  "agent_used": "sql_and_dashboard"
}
```

## Architecture Details

### Agent Flow

1. **Intent Classification** (Supervisor)
   - Classifies query as: `general`, `sql`, `dashboard`, or `sql_and_dashboard`
   - Routes to appropriate agent(s)

2. **SQL Agent Workflow** (if SQL required)
   - Get database schema (cached in Redis for 1 hour)
   - Generate SQL query using Claude
   - Validate query for security (no DROP, DELETE, etc.)
   - Execute query with timeout
   - Retry once with error correction if failed

3. **Dashboard Agent Workflow** (if visualization required)
   - Analyze data structure (dimensions, metrics, data types)
   - Select appropriate chart types using Claude
   - Generate Chart.js configurations
   - Create complete HTML with embedded CSS/JS
   - Add interactivity (filters, tooltips)

4. **Supervisor Aggregation**
   - Combines results from specialized agents
   - Formats natural language response
   - Saves to conversation history in Redis

### State Management

- **Redis** stores:
  - Conversation history (TTL: 30 minutes)
  - Agent state between steps
  - Database schema cache (TTL: 1 hour)
  
- **PostgreSQL** stores:
  - Chat messages
  - Query history
  - Dashboard history

### Error Handling

- **Automatic Retry**: Failed SQL queries are automatically corrected and retried once
- **User Clarification**: After retry failure, system asks user for clarification
- **Graceful Degradation**: Errors don't crash the system; supervisor provides helpful error messages

## File Structure

```
backend/app/
├── agents/
│   ├── __init__.py
│   ├── state.py                    # State schema (TypedDict)
│   ├── graph.py                    # LangGraph workflow
│   ├── supervisor_agent.py         # Supervisor agent
│   ├── sql_agent.py                # SQL agent
│   ├── dashboard_agent.py          # Dashboard agent
│   ├── prompts/
│   │   ├── supervisor_prompts.py   # Supervisor prompts
│   │   ├── sql_prompts.py          # SQL prompts
│   │   └── dashboard_prompts.py    # Dashboard prompts
│   └── tools/
│       ├── supervisor_tools.py     # Supervisor tools
│       ├── sql_tools.py            # SQL tools (5 tools)
│       └── dashboard_tools.py      # Dashboard tools (5 tools)
├── services/
│   ├── redis_service.py            # Redis client wrapper
│   ├── claude_service.py           # Claude API client
│   └── chat_service.py             # Updated with agent integration
└── api/
    └── chat.py                     # Chat endpoints (uses agents)
```

## Performance Optimization

- **Prompt Caching**: Large system prompts are cached by Claude (90% cost reduction)
- **Schema Caching**: Database schemas cached in Redis for 1 hour
- **Async Execution**: All operations are async for better concurrency
- **Connection Pooling**: Database and Redis connections are pooled

**Expected Performance**:
- General queries: <1s
- SQL queries: 2-4s
- SQL + Dashboard: 6-10s ✅ (meets <10s requirement)

## Troubleshooting

### Redis Connection Failed

```
⚠️ WARNING: Redis connection failed: Error 111 connecting to localhost:6379
```

**Solution**: Ensure Redis is running:
```bash
redis-cli ping  # Should return PONG
```

### Agent Module Import Error

```
⚠️  Startup warning: No module named 'langgraph'
```

**Solution**: Reinstall dependencies:
```bash
pip install -r requirements.txt
```

### SQL Agent Timeout

```
❌ Error executing query: Query timeout after 30 seconds
```

**Solution**: 
- Optimize your SQL query
- Increase `AGENT_TIMEOUT` in `.env`
- Check database connection

### Dashboard Generation Failed

```
❌ Dashboard Agent error: No data available
```

**Solution**: Ensure SQL agent ran successfully first
- Check `query_results` in state
- SQL query must return data before dashboard can be created

## Development Tips

### Adding New Tools

1. Create tool function in appropriate `tools/` file
2. Add tool to agent's processing logic
3. Update prompts if needed
4. Add unit tests

### Modifying Agent Behavior

- **Intent Classification**: Edit `INTENT_CLASSIFICATION_PROMPT` in `supervisor_prompts.py`
- **SQL Generation**: Edit `SQL_GENERATION_PROMPT` in `sql_prompts.py`
- **Visualization Selection**: Edit `VISUALIZATION_SELECTION_PROMPT` in `dashboard_prompts.py`

### Debugging Agent Flow

Set environment variable for verbose logging:
```bash
export LOG_LEVEL=DEBUG
```

Check the console output - each node logs its execution:
```
🎯 Supervisor: Classifying intent...
✅ Intent classified as: sql_and_dashboard
🗄️ SQL Agent: Processing query...
📊 Getting database schema...
🔧 Generating SQL query...
✅ Validating SQL query...
⚡ Executing SQL query...
✅ Query executed successfully: 5 rows
📊 Dashboard Agent: Creating dashboard...
🔍 Analyzing data structure...
📊 Selecting visualizations...
⚙️ Generating chart configurations...
🎨 Creating dashboard HTML...
✨ Adding interactivity...
✅ Dashboard created successfully with 2 charts
📋 Supervisor: Aggregating results...
```

## Next Steps

1. **Run Tests**: `pytest tests/test_agents/ -v`
2. **Test General Queries**: "What can you do?"
3. **Test SQL Queries**: "How many users do we have?" (with database connected)
4. **Test Dashboards**: "Show me sales by region" (with database connected)
5. **Monitor Performance**: Check execution times in responses

## Support

For issues or questions:
1. Check this guide first
2. Check console output for error messages
3. Review agent logs in Redis (conversation history)
4. Check FastAPI docs at http://localhost:8000/docs



