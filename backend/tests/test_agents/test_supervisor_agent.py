"""
Test Supervisor Agent
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.agents.supervisor_agent import supervisor_agent
from app.agents.state import create_initial_state


@pytest.mark.asyncio
async def test_classify_intent_general():
    """Test intent classification for general queries"""
    state = create_initial_state(
        user_query="What can you do?", session_id="test-123", user_id=1
    )

    with patch(
        "app.agents.supervisor_agent.claude_service.create_message_async"
    ) as mock_claude:
        # Mock Claude response
        mock_claude.return_value = {
            "content": [{"type": "text", "text": "general"}],
            "stop_reason": "end_turn",
        }

        with patch(
            "app.agents.supervisor_agent.claude_service.extract_text_content"
        ) as mock_extract:
            mock_extract.return_value = "general"

            intent = await supervisor_agent.classify_intent(state)

            assert intent == "general"
            mock_claude.assert_called_once()


@pytest.mark.asyncio
async def test_classify_intent_sql():
    """Test intent classification for SQL queries"""
    state = create_initial_state(
        user_query="How many users do we have?", session_id="test-123", user_id=1
    )

    with patch(
        "app.agents.supervisor_agent.claude_service.create_message_async"
    ) as mock_claude:
        mock_claude.return_value = {
            "content": [{"type": "text", "text": "sql"}],
            "stop_reason": "end_turn",
        }

        with patch(
            "app.agents.supervisor_agent.claude_service.extract_text_content"
        ) as mock_extract:
            mock_extract.return_value = "sql"

            intent = await supervisor_agent.classify_intent(state)

            assert intent == "sql"


@pytest.mark.asyncio
async def test_classify_intent_sql_and_dashboard():
    """Test intent classification for queries requiring both SQL and dashboard"""
    state = create_initial_state(
        user_query="Show me sales by region", session_id="test-123", user_id=1
    )

    with patch(
        "app.agents.supervisor_agent.claude_service.create_message_async"
    ) as mock_claude:
        mock_claude.return_value = {
            "content": [{"type": "text", "text": "sql_and_dashboard"}],
            "stop_reason": "end_turn",
        }

        with patch(
            "app.agents.supervisor_agent.claude_service.extract_text_content"
        ) as mock_extract:
            mock_extract.return_value = "sql_and_dashboard"

            intent = await supervisor_agent.classify_intent(state)

            assert intent == "sql_and_dashboard"


@pytest.mark.asyncio
async def test_classify_intent_dashboard_without_data():
    """Test that dashboard request without data upgrades to sql_and_dashboard"""
    state = create_initial_state(
        user_query="Create a bar chart", session_id="test-123", user_id=1
    )
    # No query_results, so should upgrade
    state["query_results"] = None

    with patch(
        "app.agents.supervisor_agent.claude_service.create_message_async"
    ) as mock_claude:
        mock_claude.return_value = {
            "content": [{"type": "text", "text": "dashboard"}],
            "stop_reason": "end_turn",
        }

        with patch(
            "app.agents.supervisor_agent.claude_service.extract_text_content"
        ) as mock_extract:
            mock_extract.return_value = "dashboard"

            intent = await supervisor_agent.classify_intent(state)

            # Should upgrade to sql_and_dashboard since no data available
            assert intent == "sql_and_dashboard"


@pytest.mark.asyncio
async def test_handle_general_query():
    """Test handling general queries"""
    state = create_initial_state(
        user_query="What databases can I connect?", session_id="test-123", user_id=1
    )

    mock_db = Mock()

    with patch(
        "app.agents.supervisor_agent.claude_service.create_message_async"
    ) as mock_claude:
        mock_claude.return_value = {
            "content": [
                {
                    "type": "text",
                    "text": "You can connect to PostgreSQL, MySQL, or SQLite databases.",
                }
            ],
            "stop_reason": "end_turn",
        }

        with patch(
            "app.agents.supervisor_agent.claude_service.extract_text_content"
        ) as mock_extract:
            mock_extract.return_value = (
                "You can connect to PostgreSQL, MySQL, or SQLite databases."
            )

            with patch(
                "app.agents.supervisor_agent.get_conversation_history"
            ) as mock_history:
                mock_history.return_value = []

                with patch(
                    "app.agents.supervisor_agent.get_database_list"
                ) as mock_db_list:
                    mock_db_list.return_value = []

                    response = await supervisor_agent.handle_general_query(
                        state, mock_db
                    )

                    assert (
                        "PostgreSQL" in response
                        or "MySQL" in response
                        or "SQLite" in response
                    )
                    mock_claude.assert_called_once()


@pytest.mark.asyncio
async def test_aggregate_response():
    """Test aggregating responses from specialized agents"""
    state = create_initial_state(
        user_query="Show me sales data", session_id="test-123", user_id=1
    )

    # Add results from specialized agents
    state["sql_query"] = "SELECT * FROM sales LIMIT 100"
    state["query_results"] = [{"region": "North", "sales": 1000}]
    state["dashboard_html"] = "<html>...</html>"

    with patch(
        "app.agents.supervisor_agent.claude_service.create_message_async"
    ) as mock_claude:
        mock_claude.return_value = {
            "content": [
                {
                    "type": "text",
                    "text": "I've retrieved your sales data and created a dashboard.",
                }
            ],
            "stop_reason": "end_turn",
        }

        with patch(
            "app.agents.supervisor_agent.claude_service.extract_text_content"
        ) as mock_extract:
            mock_extract.return_value = (
                "I've retrieved your sales data and created a dashboard."
            )

            response = await supervisor_agent.aggregate_response(state)

            assert len(response) > 0
            mock_claude.assert_called_once()


