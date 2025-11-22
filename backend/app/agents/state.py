"""
Agent State Schema - Defines the state structure for LangGraph workflow
"""

from typing import TypedDict, Optional, List, Dict, Any, Literal
from uuid import UUID


class AgentState(TypedDict):
    """
    State schema for the multi-agent workflow.
    This state is passed between agents and persisted in Redis.
    """

    # User input
    user_query: str
    session_id: str
    user_id: int
    database_id: Optional[UUID]  # Changed from int to UUID

    # Conversation history
    conversation_history: List[Dict[str, Any]]

    # Intent classification
    intent: Literal["general", "sql", "dashboard", "sql_and_dashboard"]

    # SQL Agent outputs
    sql_query: Optional[str]
    query_results: Optional[List[Dict[str, Any]]]
    query_metadata: Optional[Dict[str, Any]]

    # Dashboard Agent outputs
    dashboard_html: Optional[str]
    dashboard_config: Optional[Dict[str, Any]]

    # Supervisor outputs
    supervisor_response: Optional[str]

    # Routing control
    next_agent: Literal["supervisor", "sql", "dashboard", "end"]

    # Error handling
    error: Optional[str]
    retry_count: int

    # Metadata
    agent_used: Optional[str]
    execution_time: Optional[float]
    timestamp: Optional[str]


class MessageDict(TypedDict):
    """Structure for individual messages in conversation history"""

    role: Literal["user", "assistant", "system"]
    content: str
    metadata: Optional[Dict[str, Any]]
    timestamp: Optional[str]


def create_initial_state(
    user_query: str, session_id: str, user_id: int, database_id: Optional[UUID] = None
) -> AgentState:
    """
    Create initial state for a new agent workflow.

    Args:
        user_query: User's natural language query
        session_id: Unique session identifier
        user_id: User ID from authentication
        database_id: Optional database connection ID

    Returns:
        AgentState: Initial state dictionary
    """
    return AgentState(
        user_query=user_query,
        session_id=session_id,
        user_id=user_id,
        database_id=database_id,
        conversation_history=[],
        intent="general",  # Will be classified by supervisor
        sql_query=None,
        query_results=None,
        query_metadata=None,
        dashboard_html=None,
        dashboard_config=None,
        supervisor_response=None,
        next_agent="supervisor",
        error=None,
        retry_count=0,
        agent_used=None,
        execution_time=None,
        timestamp=None,
    )
