"""
Supervisor Agent - Main Routing Hub & General Chat Handler
"""

from typing import Dict, Any, Optional, List
import hashlib
import json
import re
from app.agents.base_agent import BaseAgent
from app.services.claude_service import ClaudeService


class SupervisorAgent(BaseAgent):
    """
    Supervisor Agent: Main intelligence hub that routes queries AND handles general chat.
    
    Responsibilities:
    1. Analyze user queries
    2. Decide: respond myself OR route to specialist agent
    3. Handle general conversation directly
    4. Route data queries to SQLAgent
    5. Route visualization requests to DashboardAgent
    
    Uses hybrid approach: fast pre-filter + AI for ambiguous cases
    """

    def __init__(self, claude_service: ClaudeService):
        """
        Initialize Supervisor Agent.

        Args:
            claude_service: Claude API service
        """
        super().__init__(claude_service)
        self.decision_cache = {}  # In-memory cache for routing decisions

    async def route_query(
        self, 
        query: str, 
        has_database: bool,
        chat_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Main routing method - decides action and returns decision.
        
        Args:
            query: User's query
            has_database: Whether chat has database connected
            chat_history: Previous conversation (optional)
            
        Returns:
            Dict with:
            - action: "respond" | "sql" | "dashboard"
            - reasoning: Why this decision was made
            - method: "fast-path" | "ai-routed"
            - confidence: 0.0-1.0
        """
        # Step 1: Check cache for previous AI decisions
        cache_key = self._get_cache_key(query, has_database)
        if cache_key in self.decision_cache:
            cached = self.decision_cache[cache_key]
            print(f"💾 Cache hit: {cached['action']}")
            return cached
        
        # Step 2: AI-powered decision (ALWAYS - no keywords!)
        print(f"🤖 AI analyzing query...")
        decision = await self._ai_route(query, has_database, chat_history)
        self.decision_cache[cache_key] = decision
        return decision

    def _quick_route(self, query: str, has_database: bool) -> Optional[Dict[str, Any]]:
        """
        NO fast-path. ALWAYS use AI routing for true intelligence.
        
        Args:
            query: User's query
            has_database: Whether database is connected
            
        Returns:
            Always None - everything goes through AI
        """
        # Pure AI routing - no keywords, no shortcuts, just intelligence
        return None

    async def _ai_route(
        self, 
        query: str, 
        has_database: bool, 
        chat_history: Optional[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Use Claude Haiku for intelligent routing of ambiguous queries.
        
        Args:
            query: User's query
            has_database: Whether database is connected
            chat_history: Previous conversation
            
        Returns:
            Decision dict with action, reasoning, confidence
        """
        system_prompt = """You are an intelligent routing agent for a data analysis system.

Your job: Deeply understand the user's intent and route to the appropriate action.

Available actions:
1. **respond** - I handle directly:
   - Questions ABOUT my capabilities ("can you create dashboards?", "what can you do?")
   - Casual conversation and acknowledgments ("hello", "thanks")
   - Conceptual questions about databases/SQL ("what is a foreign key?")
   - Explanations and clarifications
   - When user needs guidance or help understanding something
   - Follow-up questions that don't require data retrieval

2. **sql** - Route to SQL Agent:
   - Data retrieval requests from the database
   - Questions needing actual data to answer ("who is the first user?", "how many records?")
   - Requests to show/list/find specific data
   - Aggregations, summaries, counts from database
   - ANY query that needs SELECT to answer
   - Requires database connection

3. **dashboard** - Route to Dashboard Agent:
   - Requests to CREATE visualizations ("show me sales in a chart")
   - Explicit visualization creation ("create a dashboard", "visualize this data")
   - When user wants charts, graphs, plots with their data
   - This is for CREATING visuals, not asking about them
   - Requires database connection and data

Critical distinctions:
- "Can you create dashboards?" → **respond** (question about capability)
- "Create a dashboard of sales" → **dashboard** (action request)
- "What is a dashboard?" → **respond** (conceptual question)
- "Show me users in a chart" → **dashboard** (visualization request)
- "Who is the first user?" → **sql** (data query)
- "Do you support SQL?" → **respond** (capability question)
- "Show me all users" → **sql** (data query, no visualization)

Think about:
- Is this a QUESTION or an ACTION?
- Do they want to LEARN something or GET something done?
- Are they asking ABOUT capabilities or USING capabilities?

Respond with JSON only:
{
  "action": "respond|sql|dashboard",
  "reasoning": "brief explanation of intent",
  "confidence": 0.0-1.0
}"""

        user_prompt = f"""Query: "{query}"
Database connected: {has_database}

What action should be taken?"""

        try:
            # Use Haiku for speed (3x faster than Sonnet)
            response = await self.claude.create_message_async(
                messages=[{"role": "user", "content": user_prompt}],
                system=system_prompt,
                max_tokens=200,
                temperature=0.1,
                model="claude-3-haiku-20240307"  # Fast & cheap
            )
            
            text = self.claude.extract_text_content(response)
            decision = self._parse_decision(text)
            decision["method"] = "ai"
            return decision
            
        except Exception as e:
            print(f"⚠️ AI routing failed: {e}, defaulting to respond")
            # Fallback: respond (safest default)
            return {
                "action": "respond",
                "reasoning": f"AI routing error: {str(e)}",
                "method": "fallback",
                "confidence": 0.5
            }

    def _get_cache_key(self, query: str, has_database: bool) -> str:
        """
        Generate cache key for similar queries.
        Normalizes query to improve cache hit rate.
        """
        # Normalize: lowercase, strip, first 50 chars
        normalized = query.lower().strip()[:50]
        key = f"{normalized}:{has_database}"
        return hashlib.md5(key.encode()).hexdigest()

    def _parse_decision(self, text: str) -> Dict[str, Any]:
        """
        Parse JSON decision from Claude's response.
        Handles malformed JSON gracefully.
        """
        # Extract JSON from text
        json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # Fallback: try to extract action from text
        text_lower = text.lower()
        if "sql" in text_lower:
            action = "sql"
        elif "dashboard" in text_lower:
            action = "dashboard"
        else:
            action = "respond"
        
        return {
            "action": action,
            "reasoning": "Parsed from text (JSON failed)",
            "confidence": 0.6
        }

    async def respond(
        self,
        query: str,
        chat_history: Optional[List[Dict[str, Any]]] = None,
        needs_database: bool = False
    ) -> Dict[str, Any]:
        """
        Handle general chat directly (Supervisor responds).
        
        Args:
            query: User's query
            chat_history: Previous conversation
            needs_database: If True, user asked for data but no DB connected
            
        Returns:
            Dict with response text
        """
        system_prompt = """You are an AI assistant representing an intelligent data analysis system.

When users ask about capabilities, speak on behalf of the ENTIRE SYSTEM (use "I" to mean the system):
- "Can you create dashboards?" → "YES! I can create dashboards with various chart types..."
- "Do you support SQL?" → "YES! I can help you query your database..."
- "What can you do?" → "I can analyze data, run SQL queries, and create visualizations..."

Your role in conversations:
✅ Answer questions ABOUT the system's capabilities (speak for the whole system)
✅ Provide explanations about databases, SQL, data analysis concepts
✅ Acknowledge responses naturally ("got it!", "great!", etc.)
✅ Help users understand what's possible with their data
✅ Guide users on how to use the system

Key capabilities to mention when asked:
🔹 **Data Queries**: Run SQL queries on connected databases
🔹 **Dashboards**: Create interactive visualizations (charts, graphs, plots)
🔹 **Data Analysis**: Aggregate, filter, join, and analyze data
🔹 **Natural Language**: Understand plain English, no SQL knowledge needed

Be enthusiastic about capabilities! Don't say "I can't do X, that's another agent's job."
Instead say "Yes! I can do that - just ask me to [do the thing]."

If no database is connected and user asks for data, say:
"I'd love to help with that! First, connect a database and then I can [query/visualize] your data."

Be friendly, concise, helpful, and speak as ONE unified system."""

        # Prepare messages
        messages = []
        if chat_history:
            messages = self.format_chat_history(chat_history)
        
        messages.append({
            "role": "user",
            "content": query
        })
        
        # Special handling if they need database
        if needs_database:
            messages[-1]["content"] += "\n\n(Note: User asked for data but no database is connected)"
        
        try:
            response = await self.claude.create_message_async(
                messages=messages,
                system=system_prompt,
                max_tokens=1000,
                temperature=0.7  # More creative for conversation
            )
            
            text = self.claude.extract_text_content(response)
            
            return {
                "success": True,
                "response": text,
                "agent": "supervisor",
                "mode": "general"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "agent": "supervisor"
            }

    async def process(
        self,
        user_query: str,
        has_database: bool = False,
        chat_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Process query - route OR respond directly.
        This is a convenience method that combines routing + responding.
        
        Args:
            user_query: User's query
            has_database: Whether database is connected
            chat_history: Previous conversation
            
        Returns:
            Dict with action decision OR direct response
        """
        decision = await self.route_query(user_query, has_database, chat_history)
        
        # If action is "respond", handle it directly
        if decision["action"] == "respond":
            needs_db = decision.get("needs_database", False)
            return await self.respond(user_query, chat_history, needs_db)
        
        # Otherwise, return routing decision for ChatService to handle
        return {
            "success": True,
            "decision": decision
        }

