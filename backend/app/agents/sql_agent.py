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
    
    def get_system_prompt(self) -> str:
        """
        Get system prompt for SQL Agent.
        
        Returns:
            str: System prompt
        """
        return """You are an expert SQL query generator and database analyst. Your role is to:

1. Understand the user's natural language questions about their data
2. Use the database schema to write accurate SQL queries
3. Validate queries for safety and correctness
4. Execute queries and return results

Guidelines:
- Always call get_database_schema first to understand the available tables and columns
- Generate clean, efficient SQL queries that answer the user's question
- Use proper JOINs when querying related tables
- Always validate SQL queries before execution
- Only generate SELECT queries (read-only operations)
- Handle errors gracefully and provide helpful explanations
- Consider performance and limit results when appropriate
- Explain what the query does in simple terms

Remember: You must ONLY generate SELECT queries. Never use DELETE, UPDATE, INSERT, DROP, or other destructive operations."""
    
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
        
        # Prepare messages for Claude
        messages = self.format_chat_history(chat_history)
        messages.append({
            "role": "user",
            "content": user_query
        })
        
        # Get tool definitions
        tools = self.tools.get_tool_definitions()
        
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
        
        # Agentic loop with tool calling
        max_iterations = 10
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            try:
                # Call Claude with tools
                response = await self.claude.create_message_async(
                    messages=messages,
                    tools=tools,
                    system=self.get_system_prompt(),
                    max_tokens=4096
                )
                
                # Check stop reason
                stop_reason = response.get("stop_reason")
                
                # Extract text content
                text_content = self.claude.extract_text_content(response)
                if text_content:
                    result["agent_thinking"].append(text_content)
                
                # Check if Claude wants to use tools
                if stop_reason == "tool_use":
                    # Extract tool calls
                    tool_calls = self.claude.extract_tool_calls(response)
                    
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
                    if result["success"]:
                        # Successfully executed query
                        break
                    else:
                        # No query was executed
                        result["error"] = "Could not generate and execute SQL query"
                        break
                else:
                    # Unexpected stop reason
                    result["error"] = f"Unexpected stop reason: {stop_reason}"
                    break
                    
            except Exception as e:
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



