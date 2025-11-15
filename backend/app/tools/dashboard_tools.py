"""
Dashboard Tools for Agent 2 - Dashboard Creator
"""
from typing import Dict, List, Any, Optional
import json
from collections import Counter


class DashboardTools:
    """
    Tools for analyzing data and creating interactive dashboards.
    Used by Agent 2 (Dashboard Agent) for visualization generation.
    """
    
    def __init__(self):
        """Initialize dashboard tools"""
        pass
    
    def analyze_data_structure(self, data: List[Dict[str, Any]], columns: List[str]) -> Dict[str, Any]:
        """
        Analyze data structure to determine optimal visualizations.
        
        Args:
            data: List of data rows
            columns: List of column names
            
        Returns:
            Dict: Data analysis including types, cardinality, statistics
            
        Tool Definition for Claude:
        {
            "name": "analyze_data_structure",
            "description": "Analyzes the structure of query results to understand data types, cardinality, patterns, and relationships. Use this first to determine what visualizations would be most appropriate.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "data": {"type": "array", "description": "Array of data rows"},
                    "columns": {"type": "array", "items": {"type": "string"}, "description": "Array of column names"}
                },
                "required": ["data", "columns"]
            }
        }
        """
        if not data or not columns:
            return {
                "error": "No data to analyze",
                "row_count": 0,
                "column_count": 0
            }
        
        analysis = {
            "row_count": len(data),
            "column_count": len(columns),
            "columns": []
        }
        
        for col in columns:
            col_analysis = self._analyze_column(data, col)
            analysis["columns"].append(col_analysis)
        
        # Determine suggested chart types
        analysis["suggested_charts"] = self._suggest_chart_types(analysis)
        
        return analysis
    
    def _analyze_column(self, data: List[Dict[str, Any]], column_name: str) -> Dict[str, Any]:
        """Analyze a single column"""
        values = [row.get(column_name) for row in data if row.get(column_name) is not None]
        
        if not values:
            return {
                "name": column_name,
                "type": "empty",
                "unique_count": 0,
                "null_count": len(data)
            }
        
        # Determine data type
        sample_value = values[0]
        col_type = "string"
        
        if isinstance(sample_value, (int, float)):
            col_type = "numeric"
        elif isinstance(sample_value, bool):
            col_type = "boolean"
        
        # Calculate statistics
        unique_values = list(set(values))
        cardinality = len(unique_values)
        
        result = {
            "name": column_name,
            "type": col_type,
            "unique_count": cardinality,
            "null_count": len(data) - len(values),
            "sample_values": unique_values[:5]
        }
        
        # Numeric statistics
        if col_type == "numeric":
            numeric_values = [float(v) for v in values if v is not None]
            if numeric_values:
                result["min"] = min(numeric_values)
                result["max"] = max(numeric_values)
                result["avg"] = sum(numeric_values) / len(numeric_values)
        
        # Cardinality classification
        if cardinality == 1:
            result["cardinality_type"] = "constant"
        elif cardinality < 10:
            result["cardinality_type"] = "low"
        elif cardinality < 100:
            result["cardinality_type"] = "medium"
        else:
            result["cardinality_type"] = "high"
        
        return result
    
    def _suggest_chart_types(self, analysis: Dict[str, Any]) -> List[str]:
        """Suggest appropriate chart types based on data analysis"""
        suggestions = []
        columns = analysis.get("columns", [])
        
        numeric_cols = [c for c in columns if c["type"] == "numeric"]
        categorical_cols = [c for c in columns if c["type"] == "string" and c["cardinality_type"] in ["low", "medium"]]
        
        # Single numeric column -> KPI card
        if len(numeric_cols) == 1 and len(columns) == 1:
            suggestions.append("kpi_card")
        
        # Categorical + Numeric -> Bar chart
        if len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
            suggestions.append("bar_chart")
            suggestions.append("pie_chart")
        
        # Time series data -> Line chart
        time_cols = [c for c in columns if any(keyword in c["name"].lower() for keyword in ["date", "time", "month", "year", "day"])]
        if time_cols and numeric_cols:
            suggestions.append("line_chart")
        
        # Two numeric columns -> Scatter plot
        if len(numeric_cols) >= 2:
            suggestions.append("scatter_plot")
        
        # Always include table as fallback
        suggestions.append("table")
        
        return list(set(suggestions))
    
    def create_chart_config(
        self,
        chart_type: str,
        data: List[Dict[str, Any]],
        x_axis: Optional[str] = None,
        y_axis: Optional[str] = None,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a chart configuration.
        
        Args:
            chart_type: Type of chart (bar, line, pie, scatter, table, kpi_card)
            data: Data to visualize
            x_axis: X-axis column name
            y_axis: Y-axis column name
            title: Chart title
            
        Returns:
            Dict: Chart configuration
            
        Tool Definition for Claude:
        {
            "name": "create_chart_config",
            "description": "Creates a configuration for a specific chart type. Returns a JSON config that can be used to render the chart.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "chart_type": {"type": "string", "enum": ["bar_chart", "line_chart", "pie_chart", "scatter_plot", "table", "kpi_card"]},
                    "data": {"type": "array", "description": "Data to visualize"},
                    "x_axis": {"type": "string", "description": "X-axis column name"},
                    "y_axis": {"type": "string", "description": "Y-axis column name"},
                    "title": {"type": "string", "description": "Chart title"}
                },
                "required": ["chart_type", "data"]
            }
        }
        """
        config = {
            "type": chart_type,
            "title": title or f"{chart_type.replace('_', ' ').title()}",
            "data": data,
            "x_axis": x_axis,
            "y_axis": y_axis
        }
        
        return config
    
    def create_dashboard_layout(
        self,
        charts: List[Dict[str, Any]],
        title: str = "Dashboard"
    ) -> Dict[str, Any]:
        """
        Create a dashboard layout with multiple charts.
        
        Args:
            charts: List of chart configurations
            title: Dashboard title
            
        Returns:
            Dict: Dashboard layout configuration
            
        Tool Definition for Claude:
        {
            "name": "create_dashboard_layout",
            "description": "Creates a responsive dashboard layout that arranges multiple charts in a grid. Automatically determines optimal positioning based on chart types.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "charts": {"type": "array", "description": "Array of chart configurations"},
                    "title": {"type": "string", "description": "Dashboard title"}
                },
                "required": ["charts"]
            }
        }
        """
        # Limit to max 5 charts
        charts = charts[:5]
        
        layout = {
            "title": title,
            "charts": charts,
            "grid": self._calculate_grid_layout(len(charts))
        }
        
        return layout
    
    def _calculate_grid_layout(self, chart_count: int) -> Dict[str, Any]:
        """Calculate optimal grid layout for charts"""
        if chart_count == 1:
            return {"columns": 1, "rows": 1}
        elif chart_count == 2:
            return {"columns": 2, "rows": 1}
        elif chart_count == 3:
            return {"columns": 3, "rows": 1}
        elif chart_count == 4:
            return {"columns": 2, "rows": 2}
        else:  # 5+
            return {"columns": 3, "rows": 2}
    
    def generate_dashboard_html(
        self,
        layout: Dict[str, Any],
        interactive: bool = True
    ) -> str:
        """
        Generate complete HTML dashboard with Chart.js visualizations.
        
        Args:
            layout: Dashboard layout configuration
            interactive: Whether to add interactive features
            
        Returns:
            str: Complete HTML dashboard code
            
        Tool Definition for Claude:
        {
            "name": "generate_dashboard_html",
            "description": "Generates complete, self-contained HTML code for the dashboard with embedded Chart.js visualizations. The HTML includes all necessary styling and JavaScript.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "layout": {"type": "object", "description": "Dashboard layout configuration"},
                    "interactive": {"type": "boolean", "description": "Whether to include interactive features"}
                },
                "required": ["layout"]
            }
        }
        """
        title = layout.get("title", "Dashboard")
        charts = layout.get("charts", [])
        grid = layout.get("grid", {"columns": 2, "rows": 2})
        
        # Generate HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .dashboard-container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .dashboard-header {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .dashboard-header h1 {{
            color: #333;
            font-size: 28px;
            font-weight: 600;
        }}
        .dashboard-grid {{
            display: grid;
            grid-template-columns: repeat({grid['columns']}, 1fr);
            gap: 20px;
        }}
        .chart-container {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .chart-title {{
            font-size: 18px;
            font-weight: 600;
            color: #333;
            margin-bottom: 15px;
        }}
        .kpi-card {{
            text-align: center;
            padding: 40px 20px;
        }}
        .kpi-value {{
            font-size: 48px;
            font-weight: 700;
            color: #667eea;
        }}
        .kpi-label {{
            font-size: 16px;
            color: #666;
            margin-top: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #333;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        @media (max-width: 768px) {{
            .dashboard-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="dashboard-container">
        <div class="dashboard-header">
            <h1>{title}</h1>
        </div>
        <div class="dashboard-grid">
"""
        
        # Generate charts
        for i, chart in enumerate(charts):
            chart_html = self._generate_chart_html(chart, i, interactive)
            html += chart_html
        
        html += """
        </div>
    </div>
    <script>
        // Initialize all charts
        window.addEventListener('load', function() {
            initializeCharts();
        });
    </script>
</body>
</html>"""
        
        return html
    
    def _generate_chart_html(self, chart: Dict[str, Any], index: int, interactive: bool) -> str:
        """Generate HTML for a single chart"""
        chart_type = chart.get("type", "table")
        title = chart.get("title", "Chart")
        data = chart.get("data", [])
        
        if chart_type == "kpi_card":
            return self._generate_kpi_card_html(chart)
        elif chart_type == "table":
            return self._generate_table_html(chart)
        else:
            return self._generate_chartjs_html(chart, index, interactive)
    
    def _generate_kpi_card_html(self, chart: Dict[str, Any]) -> str:
        """Generate KPI card HTML"""
        title = chart.get("title", "KPI")
        data = chart.get("data", [])
        y_axis = chart.get("y_axis")
        
        value = "N/A"
        if data and y_axis:
            values = [row.get(y_axis) for row in data if row.get(y_axis) is not None]
            if values:
                value = f"{sum(values):,.2f}" if isinstance(values[0], (int, float)) else str(values[0])
        
        return f"""
            <div class="chart-container kpi-card">
                <div class="kpi-value">{value}</div>
                <div class="kpi-label">{title}</div>
            </div>
"""
    
    def _generate_table_html(self, chart: Dict[str, Any]) -> str:
        """Generate table HTML"""
        title = chart.get("title", "Data Table")
        data = chart.get("data", [])
        
        if not data:
            return f"""
            <div class="chart-container">
                <div class="chart-title">{title}</div>
                <p>No data available</p>
            </div>
"""
        
        # Get columns from first row
        columns = list(data[0].keys())
        
        table_html = f"""
            <div class="chart-container">
                <div class="chart-title">{title}</div>
                <table>
                    <thead>
                        <tr>
                            {''.join(f'<th>{col}</th>' for col in columns)}
                        </tr>
                    </thead>
                    <tbody>
"""
        
        # Add rows (limit to 20)
        for row in data[:20]:
            table_html += "<tr>"
            for col in columns:
                value = row.get(col, "")
                table_html += f"<td>{value}</td>"
            table_html += "</tr>\n"
        
        table_html += """
                    </tbody>
                </table>
            </div>
"""
        
        return table_html
    
    def _generate_chartjs_html(self, chart: Dict[str, Any], index: int, interactive: bool) -> str:
        """Generate Chart.js visualization HTML"""
        chart_type = chart.get("type", "bar_chart")
        title = chart.get("title", "Chart")
        data = chart.get("data", [])
        x_axis = chart.get("x_axis")
        y_axis = chart.get("y_axis")
        
        canvas_id = f"chart{index}"
        
        # Map chart types to Chart.js types
        chartjs_type_map = {
            "bar_chart": "bar",
            "line_chart": "line",
            "pie_chart": "pie",
            "scatter_plot": "scatter"
        }
        chartjs_type = chartjs_type_map.get(chart_type, "bar")
        
        # Prepare data for Chart.js
        labels = [str(row.get(x_axis, "")) for row in data] if x_axis else []
        values = [row.get(y_axis, 0) for row in data] if y_axis else []
        
        html = f"""
            <div class="chart-container">
                <div class="chart-title">{title}</div>
                <canvas id="{canvas_id}"></canvas>
            </div>
            <script>
                (function() {{
                    const ctx = document.getElementById('{canvas_id}');
                    new Chart(ctx, {{
                        type: '{chartjs_type}',
                        data: {{
                            labels: {json.dumps(labels)},
                            datasets: [{{
                                label: '{y_axis or "Value"}',
                                data: {json.dumps(values)},
                                backgroundColor: 'rgba(102, 126, 234, 0.6)',
                                borderColor: 'rgba(102, 126, 234, 1)',
                                borderWidth: 2
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: true,
                            plugins: {{
                                legend: {{
                                    display: {'true' if chartjs_type == 'pie' else 'false'}
                                }}
                            }}
                        }}
                    }});
                }})();
            </script>
"""
        
        return html
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get Claude-compatible tool definitions for dashboard tools"""
        return [
            {
                "name": "analyze_data_structure",
                "description": "Analyzes the structure of query results to understand data types, cardinality, patterns, and relationships. Use this first to determine what visualizations would be most appropriate.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "data": {"type": "array", "description": "Array of data rows"},
                        "columns": {"type": "array", "items": {"type": "string"}, "description": "Array of column names"}
                    },
                    "required": ["data", "columns"]
                }
            },
            {
                "name": "create_chart_config",
                "description": "Creates a configuration for a specific chart type. Returns a JSON config that can be used to render the chart.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "chart_type": {"type": "string", "description": "Type of chart: bar_chart, line_chart, pie_chart, scatter_plot, table, kpi_card"},
                        "data": {"type": "array", "description": "Data to visualize"},
                        "x_axis": {"type": "string", "description": "X-axis column name (for bar, line, scatter)"},
                        "y_axis": {"type": "string", "description": "Y-axis column name (for bar, line, scatter)"},
                        "title": {"type": "string", "description": "Chart title"}
                    },
                    "required": ["chart_type", "data"]
                }
            },
            {
                "name": "create_dashboard_layout",
                "description": "Creates a responsive dashboard layout that arranges multiple charts in a grid. Automatically determines optimal positioning based on chart types.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "charts": {"type": "array", "description": "Array of chart configurations from create_chart_config"},
                        "title": {"type": "string", "description": "Dashboard title"}
                    },
                    "required": ["charts"]
                }
            },
            {
                "name": "generate_dashboard_html",
                "description": "Generates complete, self-contained HTML code for the dashboard with embedded Chart.js visualizations. The HTML includes all necessary styling and JavaScript. This should be the final step.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "layout": {"type": "object", "description": "Dashboard layout from create_dashboard_layout"},
                        "interactive": {"type": "boolean", "description": "Whether to include interactive features (default: true)"}
                    },
                    "required": ["layout"]
                }
            }
        ]
    
    def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """Execute a tool by name"""
        if tool_name == "analyze_data_structure":
            return self.analyze_data_structure(
                tool_input.get("data", []),
                tool_input.get("columns", [])
            )
        elif tool_name == "create_chart_config":
            return self.create_chart_config(
                tool_input.get("chart_type"),
                tool_input.get("data", []),
                tool_input.get("x_axis"),
                tool_input.get("y_axis"),
                tool_input.get("title")
            )
        elif tool_name == "create_dashboard_layout":
            return self.create_dashboard_layout(
                tool_input.get("charts", []),
                tool_input.get("title", "Dashboard")
            )
        elif tool_name == "generate_dashboard_html":
            return self.generate_dashboard_html(
                tool_input.get("layout", {}),
                tool_input.get("interactive", True)
            )
        else:
            return {"error": f"Unknown tool: {tool_name}"}




