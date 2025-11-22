"""
Agent Tools - Specialized tools for each agent
"""

from app.agents.tools.supervisor_tools import (
    get_conversation_history,
    get_database_list,
    explain_query,
    get_system_capabilities
)

from app.agents.tools.sql_tools import (
    get_database_schema,
    generate_sql_query,
    validate_query,
    execute_query,
    fix_query
)

from app.agents.tools.dashboard_tools import (
    analyze_data_structure,
    select_visualization,
    create_dashboard_html,
    add_interactivity,
    generate_chart_config
)

__all__ = [
    # Supervisor tools
    "get_conversation_history",
    "get_database_list",
    "explain_query",
    "get_system_capabilities",
    # SQL tools
    "get_database_schema",
    "generate_sql_query",
    "validate_query",
    "execute_query",
    "fix_query",
    # Dashboard tools
    "analyze_data_structure",
    "select_visualization",
    "create_dashboard_html",
    "add_interactivity",
    "generate_chart_config"
]



