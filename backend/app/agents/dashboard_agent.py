"""
Dashboard Agent - Visualization specialist
"""

from typing import Dict, Any

from app.agents.state import AgentState
from app.agents.tools.dashboard_tools import (
    analyze_data_structure,
    select_visualization,
    create_dashboard_html,
    add_interactivity,
    generate_chart_config
)
from app.config import settings


class DashboardAgent:
    """
    Dashboard Agent that creates interactive visualizations.
    """
    
    def __init__(self):
        """Initialize dashboard agent"""
        self.max_charts = settings.DASHBOARD_MAX_CHARTS
    
    async def process(self, state: AgentState) -> Dict[str, Any]:
        """
        Process dashboard creation request.
        
        Args:
            state: Current agent state with query results
        
        Returns:
            Updated state with dashboard HTML
        """
        try:
            query = state["user_query"]
            data = state.get("query_results")
            
            if not data:
                return {
                    "error": "No data available to create dashboard. Please run a SQL query first.",
                    "dashboard_html": None,
                    "dashboard_config": None
                }
            
            if len(data) == 0:
                return {
                    "error": "Query returned no data to visualize.",
                    "dashboard_html": None,
                    "dashboard_config": None
                }
            
            # Step 1: Analyze data structure
            print("🔍 Analyzing data structure...")
            data_analysis = await analyze_data_structure(data)
            
            # Step 2: Select visualization types
            print("📊 Selecting visualizations...")
            visualization_selection = await select_visualization(
                data_analysis=data_analysis,
                query=query,
                max_charts=self.max_charts
            )
            
            # Step 3: Generate chart configurations
            print("⚙️ Generating chart configurations...")
            chart_configs = []
            chart_types = visualization_selection.get("chart_types", ["bar"])
            
            for chart_type in chart_types[:self.max_charts]:
                if chart_type != "table":  # Table is handled separately
                    config = await generate_chart_config(
                        data=data,
                        chart_type=chart_type,
                        data_analysis=data_analysis
                    )
                    if config:
                        chart_configs.append(config)
            
            # Step 4: Create dashboard HTML
            print("🎨 Creating dashboard HTML...")
            title = f"Dashboard: {query[:50]}..." if len(query) > 50 else f"Dashboard: {query}"
            dashboard_html = await create_dashboard_html(
                data=data,
                chart_configs=chart_configs,
                title=title
            )
            
            # Step 5: Add interactivity (optional enhancement)
            print("✨ Adding interactivity...")
            dimensions = data_analysis.get("dimensions", [])
            dashboard_html = await add_interactivity(
                html=dashboard_html,
                data=data,
                dimensions=dimensions
            )
            
            print(f"✅ Dashboard created successfully with {len(chart_configs)} charts")
            
            return {
                "dashboard_html": dashboard_html,
                "dashboard_config": {
                    "chart_types": chart_types,
                    "data_analysis": data_analysis,
                    "visualization_selection": visualization_selection
                },
                "error": None
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Dashboard Agent error: {error_msg}")
            
            return {
                "error": f"Failed to create dashboard: {error_msg}",
                "dashboard_html": None,
                "dashboard_config": None
            }


# Global instance
dashboard_agent = DashboardAgent()



