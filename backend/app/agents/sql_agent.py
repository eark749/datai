"""
<<<<<<< HEAD
SQL Agent - Intelligent SQL generation and execution using LangChain
"""
from langchain_anthropic import ChatAnthropic
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import Dict, Any, Optional, List
import json

from app.config import settings
from app.models.db_connection import DBConnection
from app.agents.sql_tools import create_sql_tools
from app.services.schema_service import schema_service
=======
SQL Agent - Database interaction specialist
"""

from typing import Dict, Any
from sqlalchemy.orm import Session

from app.agents.state import AgentState
from app.agents.tools.sql_tools import (
    get_database_schema,
    generate_sql_query,
    validate_query,
    execute_query,
    fix_query
)
from app.config import settings
>>>>>>> parent of 2c6ef72 (removed architecture)


class SQLAgent:
    """
<<<<<<< HEAD
    Intelligent SQL agent that can:
    1. Understand natural language queries
    2. Determine if query requires database access
    3. Generate SQL queries when needed
    4. Execute queries and format results
    5. Auto-retry with corrected SQL on failures
    """
    
    def __init__(self, db_config: DBConnection, schema: Dict[str, Any]):
        """
        Initialize SQL agent with database config and schema.
        
        Args:
            db_config: Database connection configuration
            schema: Database schema information
        """
        self.db_config = db_config
        self.schema = schema
        self.schema_str = schema_service.format_schema_for_agent(schema)
        
        # Initialize Claude model
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            api_key=settings.ANTHROPIC_API_KEY,
            temperature=0,  # Deterministic for SQL generation
            max_tokens=4096
        )
        
        # Create SQL tools
        self.tools = create_sql_tools(db_config)
        
        # Create agent prompt
        self.prompt = self._create_prompt()
        
        # Create agent
        self.agent = create_tool_calling_agent(self.llm, self.tools, self.prompt)
        
        # Create agent executor with auto-retry
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            max_iterations=3,  # Allow retries
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )
        
        print(f"🤖 [AGENT] SQL Agent initialized for database: {db_config.database_name}")
    
    def _create_prompt(self) -> ChatPromptTemplate:
        """
        Create the agent prompt with schema context and instructions.
        
        Returns:
            ChatPromptTemplate: LangChain prompt template
        """
        system_message = f"""You are an intelligent database assistant with access to a connected database.

DATABASE SCHEMA:
{self.schema_str}

YOUR CAPABILITIES:
1. Understand natural language questions about data
2. Intelligently determine if a question requires database access
3. Generate accurate SQL queries based on the schema
4. Execute queries and interpret results
5. Provide natural, conversational responses

IMPORTANT GUIDELINES:

**When to Use Database:**
- User asks about data, statistics, counts, trends, or specific records
- Questions like "how many...", "show me...", "what is the total...", "list all..."
- Any question that requires looking at actual data to answer
- Even complex analytical questions that need data aggregation

**When NOT to Use Database:**
- General greetings ("hello", "hi", "how are you")
- Questions about your capabilities ("what can you do?")
- Requests for explanations about concepts or definitions
- Follow-up questions about previous results that don't need new data
- Casual conversation or clarification requests

**SQL Generation Rules:**
1. Always use exact table and column names from the schema
2. Only generate SELECT queries (no INSERT, UPDATE, DELETE, DROP)
3. Include appropriate WHERE clauses for filtering
4. Use JOINs when data spans multiple tables
5. Add ORDER BY for meaningful sorting
6. Use LIMIT to prevent overwhelming results (default 1000 rows max)
7. Handle NULLs appropriately
8. Use proper date/time functions for temporal queries

**Error Recovery:**
If a query fails:
1. Analyze the error message carefully
2. Check if you used correct table/column names from schema
3. Verify data types match the schema
4. Adjust the query and try again
5. Maximum 2 retry attempts

**Response Format:**
- For database queries: Provide natural language answer based on the data
- For general questions: Respond conversationally without accessing database
- Always be helpful, clear, and concise
- If data is empty or query returns no results, explain that clearly

**Natural Language Responses:**
- Don't just repeat the data - interpret it meaningfully
- Use conversational language, not technical jargon
- Provide context and insights when relevant
- Format numbers clearly (use commas for thousands, percentages, etc.)

Remember: You are intelligent enough to understand context and intent. Don't rely on keywords - 
understand what the user is actually asking for."""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        return prompt
    
    async def process_query(
        self, 
        user_query: str,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Process a user query using the SQL agent.
        
        Args:
            user_query: Natural language query from user
            chat_history: Optional chat history for context
            
        Returns:
            Dict with response, SQL query (if any), data, and metadata
        """
        print(f"\n{'='*60}")
        print(f"🤖 [AGENT] Processing query: {user_query}")
        print(f"{'='*60}\n")
        
        try:
            # Prepare input
            agent_input = {
                "input": user_query,
                "chat_history": chat_history or []
            }
            
            # Execute agent
            print(f"🧠 [AGENT] Starting agent execution...")
            result = await self.agent_executor.ainvoke(agent_input)
            
            # Extract information from result
            response_text = result.get("output", "")
            intermediate_steps = result.get("intermediate_steps", [])
            
            # Check if SQL was executed
            sql_query = None
            sql_data = []
            row_count = 0
            execution_time_ms = 0
            
            for step in intermediate_steps:
                action, observation = step
                if action.tool == "execute_sql_query":
                    print(f"🔧 [AGENT] Tool used: execute_sql_query")
                    sql_query = action.tool_input
                    print(f"📝 [AGENT] Generated SQL: {sql_query}")
                    
                    # Parse observation (JSON string)
                    try:
                        obs_data = json.loads(observation)
                        if obs_data.get("success"):
                            sql_data = obs_data.get("rows", [])
                            row_count = obs_data.get("row_count", 0)
                            execution_time_ms = obs_data.get("execution_time_ms", 0)
                            print(f"✅ [AGENT] Query successful: {row_count} rows in {execution_time_ms}ms")
                        else:
                            print(f"❌ [AGENT] Query failed: {obs_data.get('error')}")
                    except:
                        pass
            
            print(f"\n💬 [AGENT] Final response generated")
            print(f"{'='*60}\n")
            
            return {
                "success": True,
                "response": response_text,
                "sql_query": sql_query,
                "data": sql_data,
                "row_count": row_count,
                "execution_time_ms": execution_time_ms,
                "mode": "sql" if sql_query else "general"
            }
            
        except Exception as e:
            print(f"❌ [AGENT] Error processing query: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                "success": False,
                "response": f"I encountered an error while processing your query: {str(e)}",
                "sql_query": None,
                "data": [],
                "row_count": 0,
                "execution_time_ms": 0,
                "mode": "error",
                "error": str(e)
            }


async def create_sql_agent(
    db_config: DBConnection,
    schema: Optional[Dict[str, Any]] = None
) -> SQLAgent:
    """
    Factory function to create a SQL agent.
    
    Args:
        db_config: Database connection configuration
        schema: Optional pre-loaded schema (will load if not provided)
        
    Returns:
        SQLAgent: Initialized SQL agent
    """
    print(f"🔧 [AGENT] Creating SQL agent for database: {db_config.database_name}")
    
    # Load schema if not provided
    if schema is None:
        print(f"📊 [AGENT] Loading database schema...")
        schema = await schema_service.get_or_load_schema(db_config)
    
    # Create and return agent
    agent = SQLAgent(db_config, schema)
    return agent
=======
    SQL Agent that handles database querying and data retrieval.
    """
    
    def __init__(self):
        """Initialize SQL agent"""
        self.max_retries = settings.AGENT_MAX_RETRIES
        self.row_limit = settings.SQL_ROW_LIMIT
    
    async def process(
        self,
        state: AgentState,
        db: Session
    ) -> Dict[str, Any]:
        """
        Process SQL query request.
        
        Args:
            state: Current agent state
            db: Database session
        
        Returns:
            Updated state with SQL results
        """
        try:
            query = state["user_query"]
            database_id = state.get("database_id")
            
            if not database_id:
                return {
                    "error": "No database connection specified. Please connect a database first.",
                    "sql_query": None,
                    "query_results": None
                }
            
            # Step 1: Get database schema
            print("📊 Getting database schema...")
            schema = await get_database_schema(database_id, db)
            
            # Step 2: Generate SQL query
            print("🔧 Generating SQL query...")
            sql_query = await generate_sql_query(
                query=query,
                schema=schema,
                row_limit=self.row_limit
            )
            
            # Step 3: Validate query
            print("✅ Validating SQL query...")
            validation = await validate_query(sql_query, schema)
            
            if not validation["is_valid"]:
                error_msg = "SQL query validation failed: " + ", ".join(validation["issues"])
                
                # Try to fix if retries available
                if state["retry_count"] < self.max_retries:
                    print("🔄 Attempting to fix query...")
                    sql_query = await fix_query(
                        query=sql_query,
                        error=error_msg,
                        schema=schema
                    )
                    # Re-validate
                    validation = await validate_query(sql_query, schema)
                    if not validation["is_valid"]:
                        return {
                            "error": error_msg,
                            "sql_query": sql_query,
                            "query_results": None
                        }
                else:
                    return {
                        "error": error_msg,
                        "sql_query": sql_query,
                        "query_results": None
                    }
            
            # Step 4: Execute query
            print("⚡ Executing SQL query...")
            results = await execute_query(
                query=sql_query,
                db_connection_id=database_id,
                db=db,
                timeout=settings.AGENT_TIMEOUT
            )
            
            print(f"✅ Query executed successfully: {results['metadata']['row_count']} rows")
            
            return {
                "sql_query": sql_query,
                "query_results": results["data"],
                "query_metadata": results["metadata"],
                "error": None
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ SQL Agent error: {error_msg}")
            
            # Try to fix if retries available and we have a query
            if state["retry_count"] < self.max_retries and state.get("sql_query"):
                print("🔄 Attempting to fix query after error...")
                try:
                    schema = await get_database_schema(database_id, db)
                    fixed_query = await fix_query(
                        query=state["sql_query"],
                        error=error_msg,
                        schema=schema
                    )
                    
                    # Try executing fixed query
                    results = await execute_query(
                        query=fixed_query,
                        db_connection_id=database_id,
                        db=db,
                        timeout=settings.AGENT_TIMEOUT
                    )
                    
                    print(f"✅ Fixed query executed successfully: {results['metadata']['row_count']} rows")
                    
                    return {
                        "sql_query": fixed_query,
                        "query_results": results["data"],
                        "query_metadata": results["metadata"],
                        "error": None
                    }
                except Exception as retry_error:
                    print(f"❌ Retry failed: {retry_error}")
            
            return {
                "error": f"Failed to execute SQL query: {error_msg}",
                "sql_query": state.get("sql_query"),
                "query_results": None
            }


# Global instance
sql_agent = SQLAgent()


>>>>>>> parent of 2c6ef72 (removed architecture)





