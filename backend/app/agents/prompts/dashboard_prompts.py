"""
Dashboard Agent Prompts
"""

DASHBOARD_AGENT_SYSTEM_PROMPT = """You are a data visualization expert that creates interactive, beautiful dashboards.

Your responsibilities:
1. Analyze data structure and characteristics
2. Select the most appropriate visualization types
3. Generate clean, interactive HTML dashboards
4. Ensure visualizations are accessible and user-friendly

Guidelines:
- Choose chart types based on data characteristics
- Use consistent color schemes
- Add tooltips and interactivity
- Make dashboards responsive
- Include appropriate labels and legends
- Follow data visualization best practices
"""

DATA_ANALYSIS_PROMPT = """Analyze the following data and describe its structure:

Data Sample (first 5 rows):
{data_sample}

Column Information:
{columns}

Identify:
1. Dimensions (categorical columns for grouping)
2. Metrics (numerical columns for aggregation)
3. Data types for each column
4. Cardinality (number of unique values) for categorical columns
5. Whether time-series data is present

Respond in JSON format:
{{
  "dimensions": ["column1", "column2"],
  "metrics": ["column3", "column4"],
  "data_types": {{"column1": "string", "column2": "number"}},
  "cardinality": {{"column1": 5, "column2": 10}},
  "has_time_series": true/false,
  "time_column": "column_name or null"
}}
"""

VISUALIZATION_SELECTION_PROMPT = """Based on the data structure, recommend the best visualization types:

Data Analysis:
{data_analysis}

User Query Context:
{query}

Available Chart Types:
- bar: Best for comparing categories
- line: Best for trends over time
- pie: Best for proportions (use sparingly)
- scatter: Best for relationships between two variables
- table: Best for detailed data inspection

Recommend up to {max_charts} chart types that would best display this data.

Respond in JSON format:
{{
  "chart_types": ["bar", "line"],
  "primary_chart": "bar",
  "reasoning": "Bar chart is ideal for comparing sales across regions, line chart shows trends."
}}
"""



