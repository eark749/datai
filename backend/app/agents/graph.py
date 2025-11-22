"""
LangGraph Workflow - Multi-agent orchestration
"""

from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session
import time
from datetime import datetime

from app.agents.state import AgentState
from app.agents.supervisor_agent import supervisor_agent
from app.agents.sql_agent import sql_agent
from app.agents.dashboard_agent import dashboard_agent
from app.services.redis_service import redis_service
from app.config import settings


# Node functions for LangGraph


async def supervisor_classify_node(state: AgentState, db: Session) -> AgentState:
    """
    Supervisor classifies user intent.
    """
    print("\n🎯 Supervisor: Classifying intent...")

    try:
        intent = await supervisor_agent.classify_intent(state)

        print(f"✅ Intent classified as: {intent}")

        state["intent"] = intent

        # Set next agent based on intent
        if intent == "general":
            state["next_agent"] = "supervisor"
        elif intent == "sql":
            state["next_agent"] = "sql"
        elif intent == "dashboard":
            state["next_agent"] = "dashboard"
        elif intent == "sql_and_dashboard":
            state["next_agent"] = "sql"

        return state

    except Exception as e:
        print(f"❌ Error in supervisor_classify_node: {e}")
        state["error"] = str(e)
        state["next_agent"] = "supervisor"
        return state


async def supervisor_respond_node(state: AgentState, db: Session) -> AgentState:
    """
    Supervisor handles general queries directly.
    """
    print("\n💬 Supervisor: Handling general query...")

    try:
        response = await supervisor_agent.handle_general_query(state, db)

        state["supervisor_response"] = response
        state["agent_used"] = "supervisor"
        state["next_agent"] = "end"

        # Save to conversation history
        await redis_service.add_conversation_message(
            session_id=state["session_id"], role="user", content=state["user_query"]
        )
        await redis_service.add_conversation_message(
            session_id=state["session_id"], role="assistant", content=response
        )

        return state

    except Exception as e:
        print(f"❌ Error in supervisor_respond_node: {e}")
        state["error"] = str(e)
        state["supervisor_response"] = (
            "I apologize, but I encountered an error processing your request."
        )
        state["next_agent"] = "end"
        return state


async def sql_agent_node(state: AgentState, db: Session) -> AgentState:
    """
    SQL Agent processes database queries.
    """
    print("\n🗄️ SQL Agent: Processing query...")

    try:
        result = await sql_agent.process(state, db)

        state["sql_query"] = result.get("sql_query")
        state["query_results"] = result.get("query_results")
        state["query_metadata"] = result.get("query_metadata")

        if result.get("error"):
            state["error"] = result["error"]
            state["retry_count"] += 1

            # Decide whether to retry or end
            if state["retry_count"] < settings.AGENT_MAX_RETRIES and state["sql_query"]:
                print(f"🔄 Retrying SQL query (attempt {state['retry_count']})")
                state["next_agent"] = "sql"
            else:
                print("❌ Max retries reached or no query to fix")
                state["next_agent"] = "supervisor"
                state["agent_used"] = "sql_failed"
        else:
            # Success - check if dashboard is needed
            if state["intent"] == "sql_and_dashboard":
                state["next_agent"] = "dashboard"
            else:
                state["next_agent"] = "supervisor"

            state["agent_used"] = "sql"

        return state

    except Exception as e:
        print(f"❌ Error in sql_agent_node: {e}")
        state["error"] = str(e)
        state["next_agent"] = "supervisor"
        state["agent_used"] = "sql_failed"
        return state


async def dashboard_agent_node(state: AgentState) -> AgentState:
    """
    Dashboard Agent creates visualizations.
    """
    print("\n📊 Dashboard Agent: Creating dashboard...")

    try:
        result = await dashboard_agent.process(state)

        state["dashboard_html"] = result.get("dashboard_html")
        state["dashboard_config"] = result.get("dashboard_config")

        if result.get("error"):
            state["error"] = result["error"]
            state["agent_used"] = "dashboard_failed"
        else:
            # Update agent_used to reflect both agents
            if state.get("agent_used") == "sql":
                state["agent_used"] = "sql_and_dashboard"
            else:
                state["agent_used"] = "dashboard"

        state["next_agent"] = "supervisor"

        return state

    except Exception as e:
        print(f"❌ Error in dashboard_agent_node: {e}")
        state["error"] = str(e)
        state["next_agent"] = "supervisor"
        state["agent_used"] = "dashboard_failed"
        return state


async def supervisor_aggregate_node(state: AgentState, db: Session) -> AgentState:
    """
    Supervisor aggregates results from specialized agents.
    """
    print("\n📋 Supervisor: Aggregating results...")

    try:
        response = await supervisor_agent.aggregate_response(state)

        state["supervisor_response"] = response
        state["next_agent"] = "end"

        # Save to conversation history
        await redis_service.add_conversation_message(
            session_id=state["session_id"], role="user", content=state["user_query"]
        )

        # Create assistant response with metadata
        assistant_content = response
        metadata = {
            "agent_used": state.get("agent_used"),
            "has_sql": state.get("sql_query") is not None,
            "has_dashboard": state.get("dashboard_html") is not None,
        }

        await redis_service.add_conversation_message(
            session_id=state["session_id"],
            role="assistant",
            content=assistant_content,
            metadata=metadata,
        )

        return state

    except Exception as e:
        print(f"❌ Error in supervisor_aggregate_node: {e}")
        state["error"] = str(e)
        state["supervisor_response"] = (
            "I apologize, but I encountered an error processing your request."
        )
        state["next_agent"] = "end"
        return state


# Routing function


def route_next(
    state: AgentState,
) -> Literal["supervisor_respond", "sql", "dashboard", "aggregate", "end"]:
    """
    Route to next node based on state.
    """
    next_agent = state.get("next_agent", "end")

    if next_agent == "supervisor":
        # Check if this is after specialized agent processing
        if state.get("sql_query") or state.get("dashboard_html"):
            return "aggregate"
        else:
            return "supervisor_respond"
    elif next_agent == "sql":
        return "sql"
    elif next_agent == "dashboard":
        return "dashboard"
    elif next_agent == "end":
        return "end"
    else:
        return "end"


# Graph creation


def create_agent_graph(db: Session) -> StateGraph:
    """
    Create the LangGraph workflow.

    Args:
        db: Database session

    Returns:
        Compiled StateGraph
    """

    # Create wrapper functions that properly handle async
    async def classify_wrapper(state: AgentState) -> AgentState:
        return await supervisor_classify_node(state, db)

    async def supervisor_respond_wrapper(state: AgentState) -> AgentState:
        return await supervisor_respond_node(state, db)

    async def sql_wrapper(state: AgentState) -> AgentState:
        return await sql_agent_node(state, db)

    async def aggregate_wrapper(state: AgentState) -> AgentState:
        return await supervisor_aggregate_node(state, db)

    # Create graph
    workflow = StateGraph(AgentState)

    # Add nodes with proper async wrappers
    workflow.add_node("classify", classify_wrapper)
    workflow.add_node("supervisor_respond", supervisor_respond_wrapper)
    workflow.add_node("sql", sql_wrapper)
    workflow.add_node("dashboard", dashboard_agent_node)
    workflow.add_node("aggregate", aggregate_wrapper)

    # Set entry point
    workflow.set_entry_point("classify")

    # Add conditional edges
    workflow.add_conditional_edges(
        "classify",
        route_next,
        {
            "supervisor_respond": "supervisor_respond",
            "sql": "sql",
            "dashboard": "dashboard",
            "aggregate": "aggregate",
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "sql",
        route_next,
        {
            "supervisor_respond": "supervisor_respond",
            "sql": "sql",  # For retries
            "dashboard": "dashboard",
            "aggregate": "aggregate",
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "dashboard",
        route_next,
        {
            "supervisor_respond": "supervisor_respond",
            "aggregate": "aggregate",
            "end": END,
        },
    )

    # Terminal nodes
    workflow.add_edge("supervisor_respond", END)
    workflow.add_edge("aggregate", END)

    # Compile graph
    return workflow.compile()


async def run_agent_workflow(state: AgentState, db: Session) -> AgentState:
    """
    Run the agent workflow.

    Args:
        state: Initial state
        db: Database session

    Returns:
        Final state with results
    """
    start_time = time.time()

    try:
        # Create graph
        graph = create_agent_graph(db)

        # Add timestamp
        state["timestamp"] = datetime.utcnow().isoformat()

        # Run workflow
        print(f"\n{'=' * 60}")
        print(f"🚀 Starting agent workflow for query: {state['user_query'][:50]}...")
        print(f"{'=' * 60}")

        final_state = await graph.ainvoke(state)

        # Add execution time
        execution_time = time.time() - start_time
        final_state["execution_time"] = round(execution_time, 3)

        print(f"\n{'=' * 60}")
        print(f"✅ Workflow completed in {execution_time:.2f}s")
        print(f"Agent used: {final_state.get('agent_used')}")
        print(f"{'=' * 60}\n")

        # Save final state to memory (optional)
        await redis_service.set_state(session_id=state["session_id"], state=final_state)

        return final_state

    except Exception as e:
        print(f"\n❌ Workflow error: {e}")
        execution_time = time.time() - start_time

        state["error"] = str(e)
        state["execution_time"] = round(execution_time, 3)
        state["supervisor_response"] = (
            "I apologize, but I encountered an error processing your request."
        )

        return state
