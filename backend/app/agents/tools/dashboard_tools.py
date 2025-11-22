"""
Dashboard Agent Tools
"""

from typing import List, Dict, Any, Optional
import json
from jinja2 import Template

from app.services.claude_service import claude_service
from app.agents.prompts.dashboard_prompts import (
    DATA_ANALYSIS_PROMPT,
    VISUALIZATION_SELECTION_PROMPT
)
from app.config import settings


async def analyze_data_structure(
    data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Analyze data structure and characteristics.
    
    Args:
        data: Query results data
    
    Returns:
        Analysis dictionary with dimensions, metrics, data types, etc.
    """
    try:
        if not data:
            return {
                "dimensions": [],
                "metrics": [],
                "data_types": {},
                "cardinality": {},
                "has_time_series": False,
                "time_column": None
            }
        
        # Get first few rows for analysis
        sample_size = min(5, len(data))
        data_sample = json.dumps(data[:sample_size], indent=2, default=str)
        
        # Get column information
        columns = list(data[0].keys()) if data else []
        column_info = {}
        
        for col in columns:
            # Infer type from first non-null value
            sample_values = [row[col] for row in data[:10] if row.get(col) is not None]
            if sample_values:
                first_value = sample_values[0]
                if isinstance(first_value, (int, float)):
                    column_info[col] = "number"
                elif isinstance(first_value, str):
                    # Check if it's a date string
                    if any(date_indicator in col.lower() for date_indicator in ['date', 'time', 'created', 'updated']):
                        column_info[col] = "datetime"
                    else:
                        column_info[col] = "string"
                else:
                    column_info[col] = "unknown"
        
        prompt = DATA_ANALYSIS_PROMPT.format(
            data_sample=data_sample,
            columns=json.dumps(column_info, indent=2)
        )
        
        response = await claude_service.create_message_async(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.3
        )
        
        content = claude_service.extract_text_content(response)
        
        # Extract JSON from response
        analysis = _extract_json_from_response(content)
        
        # Add actual cardinality
        for col in columns:
            unique_values = len(set(str(row.get(col)) for row in data))
            if "cardinality" not in analysis:
                analysis["cardinality"] = {}
            analysis["cardinality"][col] = unique_values
        
        return analysis
        
    except Exception as e:
        print(f"❌ Error analyzing data structure: {e}")
        # Return basic fallback analysis
        columns = list(data[0].keys()) if data else []
        return {
            "dimensions": [col for col in columns if not isinstance(data[0].get(col), (int, float))],
            "metrics": [col for col in columns if isinstance(data[0].get(col), (int, float))],
            "data_types": {col: "unknown" for col in columns},
            "cardinality": {},
            "has_time_series": False,
            "time_column": None
        }


async def select_visualization(
    data_analysis: Dict[str, Any],
    query: str,
    max_charts: int = 5
) -> Dict[str, Any]:
    """
    Select best visualization types for the data.
    
    Args:
        data_analysis: Data structure analysis
        query: Original user query for context
        max_charts: Maximum number of charts
    
    Returns:
        Recommended chart types and reasoning
    """
    try:
        prompt = VISUALIZATION_SELECTION_PROMPT.format(
            data_analysis=json.dumps(data_analysis, indent=2),
            query=query,
            max_charts=max_charts
        )
        
        response = await claude_service.create_message_async(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.3
        )
        
        content = claude_service.extract_text_content(response)
        
        # Extract JSON from response
        visualization_selection = _extract_json_from_response(content)
        
        # Ensure required fields
        if "chart_types" not in visualization_selection:
            visualization_selection["chart_types"] = ["bar"]
        if "primary_chart" not in visualization_selection:
            visualization_selection["primary_chart"] = visualization_selection["chart_types"][0]
        
        return visualization_selection
        
    except Exception as e:
        print(f"❌ Error selecting visualization: {e}")
        # Return default
        return {
            "chart_types": ["bar", "table"],
            "primary_chart": "bar",
            "reasoning": "Default visualization selection"
        }


async def generate_chart_config(
    data: List[Dict[str, Any]],
    chart_type: str,
    data_analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate Chart.js configuration for a specific chart type.
    
    Args:
        data: Query results data
        chart_type: Type of chart (bar, line, pie, scatter, table)
        data_analysis: Data structure analysis
    
    Returns:
        Chart.js configuration dictionary
    """
    try:
        dimensions = data_analysis.get("dimensions", [])
        metrics = data_analysis.get("metrics", [])
        
        # Use first dimension and metric for simplicity
        x_column = dimensions[0] if dimensions else list(data[0].keys())[0]
        y_column = metrics[0] if metrics else list(data[0].keys())[1] if len(data[0].keys()) > 1 else list(data[0].keys())[0]
        
        # Extract labels and values
        labels = [str(row.get(x_column, '')) for row in data]
        values = [float(row.get(y_column, 0)) if row.get(y_column) is not None else 0 for row in data]
        
        # Limit data points for pie charts
        if chart_type == "pie" and len(labels) > 10:
            labels = labels[:10]
            values = values[:10]
        
        # Chart.js configuration
        config = {
            "type": chart_type if chart_type != "table" else "bar",
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": y_column,
                    "data": values,
                    "backgroundColor": _get_chart_colors(len(values), chart_type),
                    "borderColor": _get_border_colors(len(values), chart_type),
                    "borderWidth": 2
                }]
            },
            "options": {
                "responsive": True,
                "maintainAspectRatio": False,
                "plugins": {
                    "legend": {
                        "display": chart_type in ["pie", "line"],
                        "position": "top"
                    },
                    "title": {
                        "display": True,
                        "text": f"{y_column} by {x_column}",
                        "font": {
                            "size": 16
                        }
                    },
                    "tooltip": {
                        "enabled": True,
                        "mode": "index",
                        "intersect": False
                    }
                }
            }
        }
        
        # Add chart type specific options
        if chart_type in ["bar", "line"]:
            config["options"]["scales"] = {
                "y": {
                    "beginAtZero": True,
                    "title": {
                        "display": True,
                        "text": y_column
                    }
                },
                "x": {
                    "title": {
                        "display": True,
                        "text": x_column
                    }
                }
            }
        
        return config
        
    except Exception as e:
        print(f"❌ Error generating chart config: {e}")
        return {}


async def create_dashboard_html(
    data: List[Dict[str, Any]],
    chart_configs: List[Dict[str, Any]],
    title: str = "Data Dashboard"
) -> str:
    """
    Create complete HTML dashboard with embedded Chart.js.
    
    Args:
        data: Query results data
        chart_configs: List of Chart.js configurations
        title: Dashboard title
    
    Returns:
        Complete HTML string
    """
    try:
        template = Template(DASHBOARD_HTML_TEMPLATE)
        
        # Prepare chart sections
        chart_sections = []
        for idx, config in enumerate(chart_configs):
            chart_sections.append({
                "id": f"chart{idx}",
                "config": json.dumps(config)
            })
        
        # Render table data
        table_html = _generate_table_html(data)
        
        html = template.render(
            title=title,
            chart_sections=chart_sections,
            table_html=table_html,
            data_json=json.dumps(data, default=str)
        )
        
        return html
        
    except Exception as e:
        print(f"❌ Error creating dashboard HTML: {e}")
        return "<html><body><h1>Error generating dashboard</h1></body></html>"


async def add_interactivity(
    html: str,
    data: List[Dict[str, Any]],
    dimensions: List[str]
) -> str:
    """
    Add interactive filters and controls to dashboard HTML.
    
    Args:
        html: Base HTML string
        data: Query results data
        dimensions: Dimensional columns for filtering
    
    Returns:
        Enhanced HTML with interactivity
    """
    try:
        # For now, return the base HTML
        # In a more advanced implementation, we would add:
        # - Filter dropdowns for dimensional columns
        # - Chart type switchers
        # - Data export buttons
        # - Drill-down capabilities
        
        return html
        
    except Exception as e:
        print(f"❌ Error adding interactivity: {e}")
        return html


def _extract_json_from_response(content: str) -> Dict[str, Any]:
    """Extract JSON object from Claude response."""
    try:
        # Try to find JSON in code blocks
        import re
        json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        
        # Try to find JSON without code blocks
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        
        # Try parsing entire content
        return json.loads(content)
    except:
        return {}


def _get_chart_colors(count: int, chart_type: str) -> List[str]:
    """Get color array for charts."""
    colors = [
        'rgba(54, 162, 235, 0.7)',   # Blue
        'rgba(255, 99, 132, 0.7)',   # Red
        'rgba(75, 192, 192, 0.7)',   # Green
        'rgba(255, 206, 86, 0.7)',   # Yellow
        'rgba(153, 102, 255, 0.7)',  # Purple
        'rgba(255, 159, 64, 0.7)',   # Orange
        'rgba(199, 199, 199, 0.7)',  # Gray
        'rgba(83, 102, 255, 0.7)',   # Indigo
        'rgba(255, 99, 255, 0.7)',   # Pink
        'rgba(99, 255, 132, 0.7)'    # Light Green
    ]
    
    if chart_type == "pie":
        return colors[:count]
    else:
        return colors[0]


def _get_border_colors(count: int, chart_type: str) -> List[str]:
    """Get border color array for charts."""
    colors = [
        'rgba(54, 162, 235, 1)',
        'rgba(255, 99, 132, 1)',
        'rgba(75, 192, 192, 1)',
        'rgba(255, 206, 86, 1)',
        'rgba(153, 102, 255, 1)',
        'rgba(255, 159, 64, 1)',
        'rgba(199, 199, 199, 1)',
        'rgba(83, 102, 255, 1)',
        'rgba(255, 99, 255, 1)',
        'rgba(99, 255, 132, 1)'
    ]
    
    if chart_type == "pie":
        return colors[:count]
    else:
        return colors[0]


def _generate_table_html(data: List[Dict[str, Any]], max_rows: int = 100) -> str:
    """Generate HTML table from data."""
    if not data:
        return "<p>No data to display</p>"
    
    columns = list(data[0].keys())
    rows = data[:max_rows]
    
    html = ['<div class="table-container">']
    html.append('<table class="data-table">')
    html.append('<thead><tr>')
    for col in columns:
        html.append(f'<th>{col}</th>')
    html.append('</tr></thead>')
    html.append('<tbody>')
    
    for row in rows:
        html.append('<tr>')
        for col in columns:
            value = row.get(col, '')
            html.append(f'<td>{value}</td>')
        html.append('</tr>')
    
    html.append('</tbody></table>')
    
    if len(data) > max_rows:
        html.append(f'<p class="table-note">Showing {max_rows} of {len(data)} rows</p>')
    
    html.append('</div>')
    
    return '\n'.join(html)


DASHBOARD_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f7fa;
            padding: 20px;
        }
        
        .dashboard {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .dashboard-header {
            background: white;
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 24px;
        }
        
        h1 {
            color: #2c3e50;
            font-size: 28px;
            font-weight: 600;
        }
        
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 24px;
            margin-bottom: 24px;
        }
        
        .chart-container {
            background: white;
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            height: 400px;
        }
        
        .table-container {
            background: white;
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow-x: auto;
        }
        
        .data-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .data-table th {
            background: #f8f9fa;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #2c3e50;
            border-bottom: 2px solid #dee2e6;
        }
        
        .data-table td {
            padding: 12px;
            border-bottom: 1px solid #dee2e6;
            color: #495057;
        }
        
        .data-table tr:hover {
            background: #f8f9fa;
        }
        
        .table-note {
            margin-top: 12px;
            color: #6c757d;
            font-size: 14px;
        }
        
        @media (max-width: 768px) {
            .charts-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="dashboard-header">
            <h1>{{ title }}</h1>
        </div>
        
        <div class="charts-grid">
            {% for chart in chart_sections %}
            <div class="chart-container">
                <canvas id="{{ chart.id }}"></canvas>
            </div>
            {% endfor %}
        </div>
        
        {{ table_html | safe }}
    </div>
    
    <script>
        // Initialize charts
        {% for chart in chart_sections %}
        const ctx{{ loop.index }} = document.getElementById('{{ chart.id }}').getContext('2d');
        const chart{{ loop.index }} = new Chart(ctx{{ loop.index }}, {{ chart.config | safe }});
        {% endfor %}
    </script>
</body>
</html>
"""



