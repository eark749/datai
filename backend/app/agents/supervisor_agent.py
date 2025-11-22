"""
Supervisor Agent - Primary conversational interface and orchestrator
"""

from typing import Dict, Any
from sqlalchemy.orm import Session

from app.agents.state import AgentState
from app.services.claude_service import claude_service
from app.agents.prompts.supervisor_prompts import (
    SUPERVISOR_SYSTEM_PROMPT,
    INTENT_CLASSIFICATION_PROMPT,
    RESPONSE_FORMAT_TEMPLATE
)
from app.agents.tools.supervisor_tools import (
    get_conversation_history,
    get_database_list,
    explain_query,
    get_system_capabilities
)


class SupervisorAgent:
    """
    Supervisor Agent that handles general conversation and routes to specialized agents.
    """
    
    def __init__(self):
        """Initialize supervisor agent"""
        self.system_prompt = SUPERVISOR_SYSTEM_PROMPT
    
    async def classify_intent(self, state: AgentState) -> str:
        """
        Classify user query intent.
        
        Args:
            state: Current agent state
        
        Returns:
            Intent classification: "general", "sql", "dashboard", "sql_and_dashboard"
        """
        try:
            query = state["user_query"]
            
            # Check if dashboard is requested but we already have data
            has_previous_data = state.get("query_results") is not None
            
            prompt = INTENT_CLASSIFICATION_PROMPT.format(query=query)
            
            response = await claude_service.create_message_async(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0.2
            )
            
            intent = claude_service.extract_text_content(response).strip().lower()
            
            # Validate intent
            valid_intents = ["general", "sql", "dashboard", "sql_and_dashboard"]
            if intent not in valid_intents:
                # Default to general if unclear
                intent = "general"
            
            # If dashboard requested but no data, upgrade to sql_and_dashboard
            if intent == "dashboard" and not has_previous_data:
                intent = "sql_and_dashboard"
            
            return intent
            
        except Exception as e:
            print(f"❌ Error classifying intent: {e}")
            return "general"
    
    async def handle_general_query(
        self,
        state: AgentState,
        db: Session
    ) -> str:
        """
        Handle general queries directly without specialized agents.
        
        Args:
            state: Current agent state
            db: Database session
        
        Returns:
            Response string
        """
        try:
            query = state["user_query"]
            user_id = state["user_id"]
            session_id = state["session_id"]
            
            # Get conversation history
            history = await get_conversation_history(session_id, limit=5)
            
            # Build context
            context_parts = []
            
            # Add conversation history
            if history:
                context_parts.append("Recent conversation:")
                for msg in history[-3:]:  # Last 3 messages
                    context_parts.append(f"{msg['role']}: {msg['content'][:200]}")
            
            # Check if query is about databases
            if any(keyword in query.lower() for keyword in ['database', 'connect', 'connection']):
                databases = await get_database_list(user_id, db)
                if databases:
                    context_parts.append(f"\nAvailable databases: {', '.join([db['name'] for db in databases])}")
                else:
                    context_parts.append("\nNo databases connected yet.")
            
            # Check if query is about capabilities
            if any(keyword in query.lower() for keyword in ['can you', 'what do', 'capabilities', 'help']):
                capabilities = await get_system_capabilities()
                context_parts.append(f"\nSystem capabilities: {capabilities}")
            
            # Check if asking to explain previous query
            if any(keyword in query.lower() for keyword in ['explain', 'what did', 'how does']):
                if state.get("sql_query"):
                    explanation = await explain_query(state["sql_query"])
                    context_parts.append(f"\nSQL Query Explanation: {explanation}")
            
            context = "\n".join(context_parts)
            
            # Generate response
            messages = [
                {"role": "user", "content": RESPONSE_FORMAT_TEMPLATE.format(
                    query=query,
                    context=context
                )}
            ]
            
            response = await claude_service.create_message_async(
                messages=messages,
                system=self.system_prompt,
                max_tokens=1000,
                temperature=0.7
            )
            
            return claude_service.extract_text_content(response)
            
        except Exception as e:
            print(f"❌ Error handling general query: {e}")
            return "I apologize, but I encountered an error processing your request. Please try again."
    
    async def aggregate_response(self, state: AgentState) -> str:
        """
        Aggregate results from specialized agents into final response.
        
        Args:
            state: Current agent state with results from specialized agents
        
        Returns:
            Final response string
        """
        try:
            query = state["user_query"]
            
            context_parts = []
            
            # Add SQL results
            if state.get("sql_query") and state.get("query_results"):
                row_count = len(state["query_results"])
                context_parts.append(f"SQL query executed successfully, returning {row_count} rows.")
                context_parts.append(f"SQL: {state['sql_query']}")
            
            # Add dashboard info
            if state.get("dashboard_html"):
                context_parts.append("Interactive dashboard created successfully.")
            
            # Add error info
            if state.get("error"):
                context_parts.append(f"Note: {state['error']}")
            
            context = "\n".join(context_parts)
            
            # Generate natural language response
            messages = [
                {"role": "user", "content": RESPONSE_FORMAT_TEMPLATE.format(
                    query=query,
                    context=context
                )}
            ]
            
            response = await claude_service.create_message_async(
                messages=messages,
                system=self.system_prompt,
                max_tokens=800,
                temperature=0.7
            )
            
            return claude_service.extract_text_content(response)
            
        except Exception as e:
            print(f"❌ Error aggregating response: {e}")
            return "Results retrieved successfully. Please see the data and visualizations above."


# Global instance
supervisor_agent = SupervisorAgent()



