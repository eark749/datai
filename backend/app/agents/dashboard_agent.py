"""
Dashboard Agent (Agent 2) - Dashboard Creator
"""
from typing import Dict, List, Any, Optional
import json

from app.agents.base_agent import BaseAgent
from app.services.claude_service import ClaudeService
from app.tools.dashboard_tools import DashboardTools


class DashboardAgent(BaseAgent):
    """
    Agent 2: Dashboard Creator.
    Analyzes query results and generates interactive HTML dashboards with visualizations.
    """
    
    def __init__(self, claude_service: ClaudeService):
        """
        Initialize Dashboard Agent.
        
        Args:
            claude_service: Claude API service
        """
        super().__init__(claude_service)
        self.tools = DashboardTools()
    
    def get_system_prompt(self) -> str:
        """
        Get system prompt for Dashboard Agent.
        
        Returns:
            str: System prompt
        """
        return """You are an expert data visualization specialist and dashboard designer. Your role is to:

1. Analyze query results to understand data structure and patterns
2. Select the most appropriate visualizations for the data
3. Create beautiful, interactive dashboards with multiple charts
4. Ensure visualizations clearly communicate insights

Guidelines:
- Start by analyzing the data structure to understand column types and relationships
- Choose visualization types that best represent the data:
  * KPI cards for single important metrics
  * Bar charts for categorical comparisons
  * Line charts for trends over time
  * Pie charts for proportions (use sparingly)
  * Scatter plots for correlations
  * Tables for detailed data listings
- Create 1-5 charts that tell a cohesive story
- Use clear, descriptive titles for charts
- Consider the user's original question when designing visualizations
- Generate complete, professional HTML dashboards with Chart.js

Process:
1. Call analyze_data_structure to understand the data
2. Create appropriate chart configs using create_chart_config (1-5 charts)
3. Arrange charts using create_dashboard_layout
4. Generate final HTML with generate_dashboard_html

Remember: Your dashboards should be visually appealing, easy to understand, and provide clear insights from the data."""
    
    async def process(
        self,
        query_results: Dict[str, Any],
        user_query: str,
        sql_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process query results and create a dashboard.
        
        Args:
            query_results: Results from SQL Agent (data, columns, etc.)
            user_query: Original user's natural language query
            sql_query: SQL query that was executed (optional)
            
        Returns:
            Dict: Dashboard results including HTML and metadata
        """
        # Extract data and columns
        data = query_results.get("data", [])
        columns = query_results.get("columns", [])
        
        if not data or not columns:
            return {
                "success": False,
                "error": "No data to visualize",
                "dashboard_html": None
            }
        
        # Prepare messages for Claude
        context = f"""User Query: {user_query}

Data Summary:
- Rows: {len(data)}
- Columns: {', '.join(columns)}

Create an interactive dashboard that visualizes this data and answers the user's question."""
        
        if sql_query:
            context += f"\n\nSQL Query Used:\n{sql_query}"
        
        messages = [{
            "role": "user",
            "content": context
        }]
        
        # Get tool definitions
        tools = self.tools.get_tool_definitions()
        
        # Initialize result tracking
        result = {
            "success": False,
            "dashboard_html": None,
            "dashboard_type": "html",
            "chart_count": 0,
            "chart_types": [],
            "error": None,
            "agent_thinking": []
        }
        
        # Store the data for tool calls
        self._current_data = data
        self._current_columns = columns
        
        # Agentic loop with tool calling
        max_iterations = 15
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            try:
                # Call Claude with tools
                response = await self.claude.create_message_async(
                    messages=messages,
                    tools=tools,
                    system=self.get_system_prompt(),
                    max_tokens=8192
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
                        
                        # Inject actual data for analyze_data_structure
                        if tool_name == "analyze_data_structure":
                            tool_input["data"] = self._current_data
                            tool_input["columns"] = self._current_columns
                        
                        # Execute the tool
                        tool_result = self.tools.execute_tool(tool_name, tool_input)
                        
                        # Track dashboard generation
                        if tool_name == "generate_dashboard_html" and isinstance(tool_result, str):
                            result["dashboard_html"] = tool_result
                            result["success"] = True
                        
                        # Track chart metadata
                        if tool_name == "create_dashboard_layout":
                            charts = tool_input.get("charts", [])
                            result["chart_count"] = len(charts)
                            result["chart_types"] = [c.get("type") for c in charts if c.get("type")]
                        
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
                        # Successfully generated dashboard
                        break
                    else:
                        # No dashboard was generated
                        result["error"] = "Could not generate dashboard"
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
        
        # Clean up temporary data
        self._current_data = None
        self._current_columns = None
        
        return result
    
    def process_sync(
        self,
        query_results: Dict[str, Any],
        user_query: str,
        sql_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synchronous version of process (for non-async contexts).
        
        Args:
            query_results: Results from SQL Agent
            user_query: Original user's natural language query
            sql_query: SQL query that was executed (optional)
            
        Returns:
            Dict: Dashboard results including HTML and metadata
        """
        import asyncio
        
        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run async process
        return loop.run_until_complete(self.process(query_results, user_query, sql_query))


