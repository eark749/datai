"""
Test Agent State Schema
"""

import pytest
from app.agents.state import create_initial_state, AgentState


def test_create_initial_state():
    """Test creating initial state"""
    state = create_initial_state(
        user_query="What is the total revenue?",
        session_id="test-session-123",
        user_id=1,
        database_id=42,
    )

    assert state["user_query"] == "What is the total revenue?"
    assert state["session_id"] == "test-session-123"
    assert state["user_id"] == 1
    assert state["database_id"] == 42
    assert state["intent"] == "general"  # Default
    assert state["next_agent"] == "supervisor"
    assert state["retry_count"] == 0
    assert state["sql_query"] is None
    assert state["dashboard_html"] is None
    assert state["error"] is None


def test_create_initial_state_no_database():
    """Test creating initial state without database"""
    state = create_initial_state(
        user_query="Hello", session_id="test-session-456", user_id=2, database_id=None
    )

    assert state["database_id"] is None
    assert state["user_query"] == "Hello"
    assert state["session_id"] == "test-session-456"


def test_state_structure():
    """Test state has all required fields"""
    state = create_initial_state(
        user_query="Test query", session_id="test-123", user_id=1
    )

    # Check all required fields exist
    required_fields = [
        "user_query",
        "session_id",
        "user_id",
        "database_id",
        "conversation_history",
        "intent",
        "sql_query",
        "query_results",
        "query_metadata",
        "dashboard_html",
        "dashboard_config",
        "supervisor_response",
        "next_agent",
        "error",
        "retry_count",
        "agent_used",
        "execution_time",
        "timestamp",
    ]

    for field in required_fields:
        assert field in state, f"Missing required field: {field}"


