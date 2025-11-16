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
        return """You are a FAST data visualization expert. Create simple, effective dashboards in under 4 tool calls.

STRICT WORKFLOW (DO NOT DEVIATE):
1. analyze_data_structure - understand the data
2. create_chart_config (1-2 times MAX) - create simple charts
3. create_dashboard_layout - arrange the charts
4. generate_dashboard_html - FINAL STEP, then STOP

RULES:
- Maximum 2 charts total
- Choose the SIMPLEST chart type that works
- NO tables unless data is < 10 rows
- After generate_dashboard_html, you MUST stop immediately
- Do NOT ask for confirmation or explain - just execute the steps

CHART SELECTION (pick ONE):
- Multiple rows + categorical column → bar_chart
- Single value or metric → kpi_card  
- Time series → line_chart
- Default → table (only if < 10 rows)

Work quickly and efficiently. No explanations needed - just execute!"""
    
    async def process(
        self,
        query_results: Dict[str, Any],
        user_query: str,
        sql_query: Optional[str] = None,
        timeout: int = 30  # Add timeout parameter (30 seconds default)
    ) -> Dict[str, Any]:
        """
        Process query results and create a dashboard.
        
        Args:
            query_results: Results from SQL Agent (data, columns, etc.)
            user_query: Original user's natural language query
            sql_query: SQL query that was executed (optional)
            timeout: Maximum time in seconds to wait for dashboard generation
            
        Returns:
            Dict: Dashboard results including HTML and metadata
        """
        import asyncio
        
        try:
            # Run the actual process with a timeout
            return await asyncio.wait_for(
                self._process_internal(query_results, user_query, sql_query),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            print(f"⏱️ Dashboard generation timed out after {timeout} seconds")
            return {
                "success": False,
                "error": f"Dashboard generation timed out after {timeout} seconds",
                "dashboard_html": None,
                "dashboard_type": None,
                "chart_count": 0,
                "chart_types": []
            }
    
    async def _process_internal(
        self,
        query_results: Dict[str, Any],
        user_query: str,
        sql_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Internal processing method with timeout protection.
        
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
        
        # Prepare messages for Claude - Be very direct and specific
        context = f"""User Query: {user_query}

Data Summary:
- Rows: {len(data)}
- Columns: {', '.join(columns)}

IMPORTANT: Work FAST. Follow the workflow exactly:
1. Call analyze_data_structure 
2. Call create_chart_config 1-2 times maximum
3. Call create_dashboard_layout
4. Call generate_dashboard_html
5. STOP immediately after generate_dashboard_html

Create a simple, effective dashboard quickly."""
        
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
        
        # Agentic loop with tool calling - Reduced iterations for speed
        max_iterations = 6  # Reduced from 8 to 6
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            try:
                # Call Claude with tools
                print(f"📊 Dashboard Agent - Iteration {iteration}/{max_iterations}")
                print(f"📝 Sending {len(messages)} messages to Claude")
                
                response = await self.claude.create_message_async(
                    messages=messages,
                    tools=tools,
                    system=self.get_system_prompt(),
                    max_tokens=3000  # Further reduced for faster responses
                )
                
                # Check stop reason
                stop_reason = response.get("stop_reason")
                print(f"⏹️ Dashboard Agent stop_reason: {stop_reason}")
                
                # Extract text content
                text_content = self.claude.extract_text_content(response)
                if text_content:
                    print(f"💬 Dashboard Agent says: {text_content[:100]}...")
                    result["agent_thinking"].append(text_content)
                
                # Check if Claude wants to use tools
                if stop_reason == "tool_use":
                    # Extract tool calls
                    tool_calls = self.claude.extract_tool_calls(response)
                    print(f"🔨 Dashboard Agent wants to use {len(tool_calls)} tools: {[tc['name'] for tc in tool_calls]}")
                    
                    # Add assistant message with tool use
                    messages.append({
                        "role": "assistant",
                        "content": response["content"]
                    })
                    
                    # Execute each tool call
                    tool_results = []
                    dashboard_generated = False
                    
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
                            dashboard_generated = True
                            print(f"✅ Dashboard HTML generated successfully!")
                        
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
                    
                    # Early exit if dashboard was generated
                    if dashboard_generated:
                        print(f"🏁 Dashboard generated, exiting early at iteration {iteration}")
                        break
                    
                elif stop_reason == "end_turn":
                    # Claude has finished
                    print(f"🏁 Dashboard Agent ended. Success: {result['success']}")
                    if result["success"]:
                        # Successfully generated dashboard
                        break
                    else:
                        # No dashboard was generated
                        print(f"❌ ERROR: Dashboard Agent did not generate HTML")
                        result["error"] = "Dashboard Agent ended without generating HTML"
                        break
                else:
                    # Unexpected stop reason
                    result["error"] = f"Unexpected stop reason: {stop_reason}"
                    break
                    
            except Exception as e:
                print(f"💥 EXCEPTION in Dashboard Agent: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
                result["error"] = f"Agent error: {str(e)}"
                break
        
        if iteration >= max_iterations and not result["success"]:
            result["error"] = "Maximum iterations reached without generating dashboard"
        
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




