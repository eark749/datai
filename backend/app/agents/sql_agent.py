"""
SQL Agent (Agent 1) - SQL Generator & Data Retriever
"""
from typing import Dict, List, Any, Optional
import json

from app.agents.base_agent import BaseAgent
from app.services.claude_service import ClaudeService
from app.tools.sql_tools import SQLTools
from app.models.db_connection import DBConnection
from app.services.db_service import DBConnectionManager


class SQLAgent(BaseAgent):
    """
    Agent 1: SQL Generator and Data Retriever.
    Converts natural language queries to SQL, validates them, and executes them.
    """
    
    def __init__(
        self,
        claude_service: ClaudeService,
        db_connection: DBConnection,
        db_manager: DBConnectionManager
    ):
        """
        Initialize SQL Agent.
        
        Args:
            claude_service: Claude API service
            db_connection: Database connection configuration
            db_manager: Database connection manager
        """
        super().__init__(claude_service)
        self.db_connection = db_connection
        self.tools = SQLTools(db_connection, db_manager)
    
    def get_system_prompt(self, schema_info: Dict[str, Any] = None) -> str:
        """
        Get system prompt for SQL Agent.
        
        Args:
            schema_info: Pre-loaded database schema information
        
        Returns:
            str: System prompt
        """
        base_prompt = """You are a SQL data retrieval specialist working as part of a larger system.

🎯 Your Role:
Fetch data from the database by generating and executing SQL SELECT queries.

✅ What You Do:
- Convert data questions into SQL queries
- Execute queries and return results
- Handle: "who", "what", "show me", "list", "find", "count", "how many"
- Aggregations: count, sum, average, max, min, group by
- Joins across multiple tables
- **For visualization requests**: Extract the underlying DATA need and fetch it
  (Example: "create a chart of users" → Query users data; "show sales over time" → Query sales with dates)

🎨 Visualization Requests:
When users ask for charts/dashboards/visualizations:
1. **DON'T refuse** - you're part of the visualization pipeline!
2. Focus on the DATA they want to visualize (ignore "chart", "dashboard" keywords)
3. Fetch the data with appropriate columns
4. Return the results - DashboardAgent will handle the visual rendering

Examples:
- "create a chart of all users" → SELECT username, email, created_at FROM users
- "show me sales trends" → SELECT date, total_sales FROM sales ORDER BY date
- "dashboard of login dates" → SELECT username, last_login FROM users

📝 Use Chat History:
If user says "create it again" or "show me that chart", look at chat history to understand what data they want.

⚡ Workflow:
1. Understand what DATA is needed (ignore visualization keywords)
2. Check database schema
3. Generate appropriate SQL SELECT query
4. Call execute_sql tool
5. Return data (DashboardAgent will visualize if needed)

🛡️ Safety:
- ONLY SELECT queries (read-only)
- NEVER: DELETE, UPDATE, INSERT, DROP, ALTER, TRUNCATE
- Use JOINs for related data
- Add LIMIT for large datasets

Tools:
1. execute_sql - Execute query and get results (PRIMARY TOOL)
2. validate_sql - Validate before execution (optional)
"""
        
        # Include schema in prompt if provided
        if schema_info and not schema_info.get("error"):
            schema_str = "\n\n=== DATABASE SCHEMA ===\n"
            schema_str += f"Database: {schema_info.get('database_name')}\n"
            schema_str += f"Type: {schema_info.get('database_type')}\n\n"
            
            for table in schema_info.get('tables', []):
                schema_str += f"Table: {table['table_name']}\n"
                schema_str += "Columns:\n"
                for col in table['columns']:
                    nullable = "NULL" if col['nullable'] else "NOT NULL"
                    schema_str += f"  - {col['name']} ({col['type']}) {nullable}\n"
                
                if table['primary_keys']:
                    schema_str += f"Primary Keys: {', '.join(table['primary_keys'])}\n"
                
                if table['foreign_keys']:
                    schema_str += "Foreign Keys:\n"
                    for fk in table['foreign_keys']:
                        schema_str += f"  - {', '.join(fk['columns'])} -> {fk['referred_table']}.{', '.join(fk['referred_columns'])}\n"
                
                schema_str += "\n"
            
            schema_str += "======================\n"
            return base_prompt + schema_str
        
        return base_prompt + "\n\nNote: Call get_database_schema first to see the database structure."
    
    async def process(
        self,
        user_query: str,
        chat_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Process a natural language query and return SQL results.
        
        Args:
            user_query: User's natural language query
            chat_history: Optional previous conversation history
            
        Returns:
            Dict: Results containing SQL, data, and execution info
        """
        if chat_history is None:
            chat_history = []
        
        # PRE-LOAD SCHEMA for faster processing (uses cache)
        print(f"⚡ Pre-loading database schema...")
        schema_info = self.tools.get_database_schema(use_cache=True)
        
        # ALWAYS include chat history - let Claude's intelligence decide if it's relevant
        messages = self.format_chat_history(chat_history)
        
        messages.append({
            "role": "user",
            "content": user_query
        })
        
        # Get tool definitions (remove get_database_schema since we pre-loaded it)
        tools = [t for t in self.tools.get_tool_definitions() if t['name'] != 'get_database_schema']
        
        # Initialize result tracking
        result = {
            "success": False,
            "user_query": user_query,
            "sql_query": None,
            "data": [],
            "columns": [],
            "row_count": 0,
            "execution_time_ms": 0,
            "error": None,
            "agent_thinking": []
        }
        
        # Agentic loop with tool calling (reduced iterations for speed)
        max_iterations = 5  # Reduced from 10 to 5
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            try:
                # Call Claude with tools
                print(f"🤖 SQL Agent - Iteration {iteration}/{max_iterations}")
                print(f"📝 Sending {len(messages)} messages to Claude")
                print(f"🔧 Tools available: {[t['name'] for t in tools]}")
                
                # Debug: Show last few messages
                for i, msg in enumerate(messages[-2:]):
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    if isinstance(content, str):
                        preview = content[:100]
                    else:
                        preview = str(content)[:100]
                    print(f"  Message {i}: [{role}] {preview}...")
                
                response = await self.claude.create_message_async(
                    messages=messages,
                    tools=tools,
                    system=self.get_system_prompt(schema_info),  # Pass pre-loaded schema
                    max_tokens=2048  # Reduced from 4096 for faster responses
                )
                
                # Check stop reason
                stop_reason = response.get("stop_reason")
                print(f"⏹️ Claude stop_reason: {stop_reason}")
                
                # Extract text content
                text_content = self.claude.extract_text_content(response)
                if text_content:
                    print(f"💬 Claude says: {text_content[:200]}...")
                    result["agent_thinking"].append(text_content)
                
                # Check if Claude wants to use tools
                if stop_reason == "tool_use":
                    # Extract tool calls
                    tool_calls = self.claude.extract_tool_calls(response)
                    print(f"🔨 Claude wants to use {len(tool_calls)} tools: {[tc['name'] for tc in tool_calls]}")
                    
                    # Add assistant message with tool use
                    messages.append({
                        "role": "assistant",
                        "content": response["content"]
                    })
                    
                    # Execute each tool call
                    tool_results = []
                    for tool_call in tool_calls:
                        tool_name = tool_call["name"]
                        tool_input = tool_call["input"]
                        
                        # Execute the tool
                        tool_result = self.tools.execute_tool(tool_name, tool_input)
                        
                        # Track SQL query
                        if tool_name == "execute_sql" and tool_result.get("success"):
                            result["sql_query"] = tool_input.get("sql_query")
                            result["data"] = tool_result.get("data", [])
                            result["columns"] = tool_result.get("columns", [])
                            result["row_count"] = tool_result.get("row_count", 0)
                            result["execution_time_ms"] = tool_result.get("execution_time_ms", 0)
                            result["success"] = True
                        
                        # Create tool result message
                        tool_result_content = self.claude.create_tool_result_message(
                            tool_call["id"],
                            tool_result
                        )
                        tool_results.append(tool_result_content)
                    
                    # Add tool results to messages
                    messages.append({
                        "role": "user",
                        "content": tool_results
                    })
                    
                elif stop_reason == "end_turn":
                    # Claude has finished
                    print(f"🏁 Claude ended conversation. Success: {result['success']}")
                    if result["success"]:
                        # Successfully executed query
                        break
                    else:
                        # No query was executed
                        print(f"❌ ERROR: Claude did not call any tools to execute SQL")
                        print(f"📄 Full response content: {response.get('content')}")
                        result["error"] = "Could not generate and execute SQL query"
                        break
                else:
                    # Unexpected stop reason
                    result["error"] = f"Unexpected stop reason: {stop_reason}"
                    break
                    
            except Exception as e:
                print(f"💥 EXCEPTION in SQL Agent: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
                result["error"] = f"Agent error: {str(e)}"
                break
        
        if iteration >= max_iterations:
            result["error"] = "Maximum iterations reached"
        
        return result
    
    def process_sync(
        self,
        user_query: str,
        chat_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Synchronous version of process (for non-async contexts).
        
        Args:
            user_query: User's natural language query
            chat_history: Optional previous conversation history
            
        Returns:
            Dict: Results containing SQL, data, and execution info
        """
        import asyncio
        
        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run async process
        return loop.run_until_complete(self.process(user_query, chat_history))




