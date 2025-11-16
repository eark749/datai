"""
Chat Service - Orchestrates Agent 1 and Agent 2 flow
"""

from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID
import json

from app.models.chat import Chat, Message
from app.models.query_history import QueryHistory, DashboardHistory
from app.models.db_connection import DBConnection
from app.models.user import User
from app.agents.sql_agent import SQLAgent
from app.agents.dashboard_agent import DashboardAgent
from app.agents.supervisor_agent import SupervisorAgent
from app.services.claude_service import claude_service
from app.services.db_service import db_connection_manager
from fastapi import HTTPException, status


class ChatService:
    """Service for managing chats and orchestrating AI agents"""

    @staticmethod
    def create_empty_chat(
        db: Session,
        user: User,
        db_connection_id: Optional[UUID] = None,
        title: str = "New Chat",
    ) -> Chat:
        """
        Create a new empty chat.

        Args:
            db: Database session
            user: Current user
            db_connection_id: Optional database connection ID
            title: Chat title

        Returns:
            Chat: New chat object
        """
        new_chat = Chat(user_id=user.id, db_connection_id=db_connection_id, title=title)
        db.add(new_chat)
        db.commit()
        db.refresh(new_chat)
        return new_chat

    @staticmethod
    def connect_database_to_chat(
        db: Session, chat: Chat, db_connection_id: UUID, user_id: UUID
    ) -> Chat:
        """
        Connect database to existing chat.

        Args:
            db: Database session
            chat: Chat object
            db_connection_id: Database connection ID
            user_id: User ID for validation

        Returns:
            Chat: Updated chat

        Raises:
            HTTPException: If chat already has database or has SQL queries
        """
        # Validate chat doesn't already have a database
        if chat.db_connection_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chat already has a database connection. Cannot change database mid-chat.",
            )

        # Validate database connection exists and belongs to user
        db_config = (
            db.query(DBConnection)
            .filter(
                DBConnection.id == db_connection_id, DBConnection.user_id == user_id
            )
            .first()
        )

        if not db_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Database connection not found",
            )

        # Check if chat has any SQL queries already
        if chat.message_count > 0:
            has_sql = (
                db.query(QueryHistory).filter(QueryHistory.chat_id == chat.id).first()
            )
            if has_sql:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot add database to chat with existing SQL queries",
                )

        # Connect database
        chat.db_connection_id = db_connection_id
        db.commit()
        db.refresh(chat)
        return chat

    @staticmethod
    def get_or_create_chat(
        db: Session,
        user: User,
        db_connection_id: Optional[UUID],
        chat_id: Optional[UUID] = None,
        title: Optional[str] = None,
    ) -> Chat:
        """
        Get existing chat or create a new one.

        Args:
            db: Database session
            user: Current user
            db_connection_id: Optional database connection ID
            chat_id: Optional existing chat ID
            title: Optional chat title

        Returns:
            Chat: Chat object
        """
        if chat_id:
            chat = (
                db.query(Chat)
                .filter(Chat.id == chat_id, Chat.user_id == user.id)
                .first()
            )

            if not chat:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found"
                )

            return chat
        else:
            # Create new chat
            return ChatService.create_empty_chat(
                db, user, db_connection_id, title or "New Chat"
            )

    @staticmethod
    def generate_chat_title(user_query: str) -> str:
        """Generate a chat title from the first user query"""
        # Take first 50 chars
        title = user_query[:50]
        if len(user_query) > 50:
            title += "..."
        return title

    @staticmethod
    def get_chat_history(
        db: Session, 
        chat_id: UUID, 
        max_messages: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get chat history formatted for AI agents.
        Limits to most recent messages to prevent token overflow.

        Args:
            db: Database session
            chat_id: Chat ID
            max_messages: Maximum number of messages to include (default: 10)

        Returns:
            List[Dict]: Formatted chat history (most recent messages)
        """
        # Fetch only recent messages for performance
        messages = (
            db.query(Message)
            .filter(Message.chat_id == chat_id)
            .order_by(Message.created_at.desc())  # Descending to get most recent
            .limit(max_messages * 2)  # Fetch extra to account for filtered messages
            .all()
        )
        
        # Reverse to get chronological order
        messages = list(reversed(messages))

        history = []
        for msg in messages:
            if msg.role in ["user", "assistant"]:
                # Skip error messages from history to prevent Claude from getting confused
                if msg.message_metadata and msg.message_metadata.get("error"):
                    continue
                
                # Skip very long messages to save tokens
                content = msg.content
                if len(content) > 1000:
                    content = content[:1000] + "... (truncated)"
                    
                history.append({"role": msg.role, "content": content})
                
                # Stop if we have enough messages
                if len(history) >= max_messages:
                    break

        return history

    @staticmethod
    async def process_chat_query(
        db: Session,
        user: User,
        user_query: str,
        chat_id: Optional[UUID] = None,
        db_connection_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """
        NEW ARCHITECTURE: Process chat query with Supervisor-first routing.
        
        Flow:
        1. Supervisor analyzes query and decides: respond | sql | dashboard
        2. Execute appropriate action
        3. Return response

        Args:
            db: Database session
            user: Current user
            user_query: User's natural language query
            chat_id: Optional existing chat ID
            db_connection_id: Optional database connection ID

        Returns:
            Dict: Complete response with mode, SQL (if applicable), data, and dashboard
        """
        # Get or create chat
        chat = ChatService.get_or_create_chat(db, user, db_connection_id, chat_id)

        # Validate database consistency
        if chat.db_connection_id and db_connection_id:
            if chat.db_connection_id != db_connection_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot change database connection mid-chat",
                )

        # Update chat title if it's the first message
        if chat.message_count == 0:
            chat.title = ChatService.generate_chat_title(user_query)

        # Get chat history (limit to 8 messages for performance)
        chat_history = ChatService.get_chat_history(db, chat.id, max_messages=8)

        # Save user message
        user_message = Message(
            chat_id=chat.id,
            role="user",
            content=user_query,
            message_metadata={"timestamp": datetime.utcnow().isoformat()},
        )
        db.add(user_message)
        chat.message_count += 1
        db.commit()
        db.refresh(user_message)

        try:
            # 🎯 STEP 1: SUPERVISOR DECIDES FIRST (NEW ARCHITECTURE!)
            print(f"\n🧠 Supervisor analyzing query: '{user_query[:50]}...'")
            supervisor = SupervisorAgent(claude_service)
            
            decision = await supervisor.route_query(
                query=user_query,
                has_database=chat.db_connection_id is not None,
                chat_history=chat_history
            )
            
            print(f"✅ Decision: {decision['action']} ({decision['method']})")
            print(f"   Reasoning: {decision['reasoning']}")
            
            # 🎯 STEP 2: EXECUTE BASED ON DECISION
            if decision["action"] == "respond":
                # Supervisor handles general chat directly
                return await ChatService._execute_supervisor_response(
                    db, user, chat, user_message, user_query, 
                    chat_history, decision
                )
            
            elif decision["action"] == "sql":
                # Route to SQL Agent
                if not chat.db_connection_id:
                    return await ChatService._handle_no_database(
                        db, chat, user_message
                    )
                
                return await ChatService._execute_sql_query(
                    db, user, chat, user_message, user_query,
                    chat.db_connection_id, chat_history
                )
            
            elif decision["action"] == "dashboard":
                # Route to SQL + Dashboard Agents
                if not chat.db_connection_id:
                    return await ChatService._handle_no_database(
                        db, chat, user_message
                    )
                
                return await ChatService._execute_sql_with_dashboard(
                    db, user, chat, user_message, user_query,
                    chat.db_connection_id, chat_history
                )
            
            else:
                raise ValueError(f"Unknown action from supervisor: {decision['action']}")
                
        except Exception as e:
            # Handle unexpected errors
            error_msg = f"An error occurred: {str(e)}"
            print(f"💥 Error in process_chat_query: {error_msg}")

            assistant_message = Message(
                chat_id=chat.id,
                role="assistant",
                content=error_msg,
                message_metadata={"error": True, "error_detail": str(e)},
            )
            db.add(assistant_message)
            chat.message_count += 1
            db.commit()

            return {
                "success": False,
                "chat_id": chat.id,
                "message_id": assistant_message.id,
                "error": error_msg,
            }

    @staticmethod
    async def _execute_supervisor_response(
        db: Session,
        user: User,
        chat: Chat,
        user_message: Message,
        user_query: str,
        chat_history: List[Dict[str, Any]],
        decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute Supervisor's direct response (general chat).
        
        Args:
            db: Database session
            user: User object
            chat: Chat object
            user_message: User message object
            user_query: User's query
            chat_history: Chat history
            decision: Routing decision from Supervisor
            
        Returns:
            Dict: Response
        """
        print(f"💬 Supervisor handling response directly...")
        
        try:
            supervisor = SupervisorAgent(claude_service)
            
            # Check if user needs database
            needs_database = decision.get("needs_database", False)
            
            # Supervisor responds directly
            result = await supervisor.respond(
                query=user_query,
                chat_history=chat_history,
                needs_database=needs_database
            )
            
            if not result.get("success"):
                raise Exception(result.get("error", "Supervisor response failed"))
            
            response_text = result["response"]
            
            # Save assistant message
            assistant_message = Message(
                chat_id=chat.id,
                role="assistant",
                content=response_text,
                message_metadata={
                    "mode": "general",
                    "agent": "supervisor",
                    "method": decision.get("method", "unknown")
                }
            )
            db.add(assistant_message)
            chat.message_count += 1
            chat.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(assistant_message)
            
            return {
                "success": True,
                "chat_id": chat.id,
                "message_id": assistant_message.id,
                "user_message": user_query,
                "assistant_message": response_text,
                "mode": "general",
                "sql_query": None,
                "data": [],
                "dashboard_html": None,
                "execution_time_ms": 0,
                "row_count": 0
            }
            
        except Exception as e:
            error_msg = f"General chat error: {str(e)}"
            print(f"💥 Error in _execute_supervisor_response: {error_msg}")
            
            assistant_message = Message(
                chat_id=chat.id,
                role="assistant",
                content=error_msg,
                message_metadata={"error": True, "mode": "general"}
            )
            db.add(assistant_message)
            chat.message_count += 1
            db.commit()
            
            return {
                "success": False,
                "chat_id": chat.id,
                "message_id": assistant_message.id,
                "error": error_msg
            }

    @staticmethod
    async def _handle_no_database(
        db: Session,
        chat: Chat,
        user_message: Message
    ) -> Dict[str, Any]:
        """
        Handle case where user asks for data but no database connected.
        
        Args:
            db: Database session
            chat: Chat object
            user_message: User message object
            
        Returns:
            Dict: Friendly error response
        """
        message = ("I'd love to help with that query, but you need to connect a database first. "
                   "You can connect a database from the Database Management page. "
                   "Once connected, I'll be able to run SQL queries and retrieve data for you!")
        
        assistant_message = Message(
            chat_id=chat.id,
            role="assistant",
            content=message,
            message_metadata={"mode": "general", "error": "no_database"}
        )
        db.add(assistant_message)
        chat.message_count += 1
        chat.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(assistant_message)
        
        return {
            "success": True,  # Not really an error, just informational
            "chat_id": chat.id,
            "message_id": assistant_message.id,
            "user_message": user_message.content,
            "assistant_message": message,
            "mode": "general",
            "sql_query": None,
            "data": [],
            "dashboard_html": None
        }

    @staticmethod
    def _process_general_query(
        db: Session,
        user: User,
        chat: Chat,
        user_message: Message,
        user_query: str,
        chat_history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Handle general chat questions without database.

        Args:
            db: Database session
            user: User object
            chat: Chat object
            user_message: User message object
            user_query: User's question
            chat_history: Chat history

        Returns:
            Dict: Response with general conversation
        """
        try:
            # System prompt for general conversation
            system_prompt = """You are a helpful AI assistant specializing in data analysis, SQL, and databases.
The user is asking general questions without a connected database.

You can help with:
- Explaining SQL concepts and syntax
- Database design and best practices
- Data analysis techniques
- General questions about data
- Answering conceptual questions

Be conversational, helpful, and educational."""

            # Prepare messages for Claude
            messages = chat_history + [{"role": "user", "content": user_query}]

            # Call Claude for general conversation (using sync method)
            response = claude_service.create_message(
                messages=messages, system=system_prompt
            )

            assistant_text = claude_service.extract_text_content(response)

            # Save assistant message
            assistant_message = Message(
                chat_id=chat.id,
                role="assistant",
                content=assistant_text,
                message_metadata={"mode": "general"},
            )
            db.add(assistant_message)
            chat.message_count += 1
            chat.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(assistant_message)

            return {
                "success": True,
                "chat_id": chat.id,
                "message_id": assistant_message.id,
                "user_message": user_query,
                "assistant_message": assistant_text,
                "mode": "general",
                "sql_query": None,
                "data": [],
                "dashboard_html": None,
                "execution_time_ms": 0,
                "row_count": 0,
            }

        except Exception as e:
            error_msg = f"Error in general chat: {str(e)}"

            assistant_message = Message(
                chat_id=chat.id,
                role="assistant",
                content=error_msg,
                message_metadata={"error": True, "mode": "general"},
            )
            db.add(assistant_message)
            chat.message_count += 1
            db.commit()

            return {
                "success": False,
                "chat_id": chat.id,
                "message_id": assistant_message.id,
                "error": error_msg,
            }

    @staticmethod
    async def _execute_sql_query(
        db: Session,
        user: User,
        chat: Chat,
        user_message: Message,
        user_query: str,
        db_connection_id: UUID,
        chat_history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Execute SQL query (no dashboard).
        
        Args:
            db: Database session
            user: User object
            chat: Chat object
            user_message: User message object
            user_query: User's query
            db_connection_id: Database connection ID
            chat_history: Chat history

        Returns:
            Dict: Response with SQL and data
        """
        print(f"📊 Executing SQL query...")
        
        try:
            # Get database connection
            db_config = (
                db.query(DBConnection)
                .filter(
                    DBConnection.id == db_connection_id, DBConnection.user_id == user.id
                )
                .first()
            )

            if not db_config:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Database connection not found",
                )
            
            # Initialize SQL Agent
            sql_agent = SQLAgent(claude_service, db_config, db_connection_manager)

            # Process query
            sql_results = await sql_agent.process(user_query, chat_history)

            if not sql_results.get("success"):
                # SQL generation/execution failed
                error_msg = f"Could not execute query: {sql_results.get('error', 'Unknown error')}"

                # Save error message
                assistant_message = Message(
                    chat_id=chat.id,
                    role="assistant",
                    content=error_msg,
                    message_metadata={"error": True, "mode": "sql"},
                )
                db.add(assistant_message)
                chat.message_count += 1
                db.commit()

                return {
                    "success": False,
                    "chat_id": chat.id,
                    "message_id": assistant_message.id,
                    "mode": "sql",
                    "error": error_msg,
                }

            # Save query history
            query_history = QueryHistory(
                user_id=user.id,
                chat_id=chat.id,
                message_id=user_message.id,
                db_connection_id=db_connection_id,
                natural_language_query=user_query,
                generated_sql=sql_results.get("sql_query", ""),
                sql_valid=True,
                execution_status="success",
                execution_time_ms=sql_results.get("execution_time_ms", 0),
                row_count=sql_results.get("row_count", 0),
            )
            db.add(query_history)
            db.commit()
            db.refresh(query_history)

            # Format response based on results
            row_count = sql_results.get("row_count", 0)
            data = sql_results.get("data", [])
            
            if row_count == 0:
                response_content = "No results found for your query."
            elif row_count == 1 and len(data) > 0:
                # Single row - describe it
                response_content = "Here's what I found:\n\n"
                row = data[0]
                for key, value in row.items():
                    if value is not None:
                        response_content += f"• **{key}**: {value}\n"
            else:
                # Multiple rows - summarize
                response_content = f"Found {row_count} results."
                if row_count <= 10:
                    response_content += "\n\n"
                    for idx, row in enumerate(data, 1):
                        response_content += f"{idx}. "
                        # Show first few columns
                        items = list(row.items())[:3]
                        response_content += ", ".join([f"{k}: {v}" for k, v in items if v is not None])
                        response_content += "\n"

            # Save assistant message
            assistant_message = Message(
                chat_id=chat.id,
                role="assistant",
                content=response_content,
                message_metadata={
                    "mode": "sql",
                    "agent": "sql",
                    "sql_query": sql_results.get("sql_query"),
                    "execution_time_ms": sql_results.get("execution_time_ms"),
                    "row_count": sql_results.get("row_count"),
                },
            )
            db.add(assistant_message)
            chat.message_count += 1
            chat.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(assistant_message)

            return {
                "success": True,
                "chat_id": chat.id,
                "message_id": assistant_message.id,
                "user_message": user_query,
                "assistant_message": response_content,
                "mode": "sql",
                "sql_query": sql_results.get("sql_query"),
                "execution_time_ms": sql_results.get("execution_time_ms", 0),
                "row_count": sql_results.get("row_count", 0),
                "data": sql_results.get("data", []),
                "columns": sql_results.get("columns", []),
                "dashboard_html": None
            }

        except Exception as e:
            # Handle unexpected errors
            error_msg = f"SQL query error: {str(e)}"
            print(f"💥 Error in _execute_sql_query: {error_msg}")

            assistant_message = Message(
                chat_id=chat.id,
                role="assistant",
                content=error_msg,
                message_metadata={"error": True, "error_detail": str(e), "mode": "sql"},
            )
            db.add(assistant_message)
            chat.message_count += 1
            db.commit()

            return {
                "success": False,
                "chat_id": chat.id,
                "message_id": assistant_message.id,
                "mode": "sql",
                "error": error_msg,
            }

    @staticmethod
    async def _execute_sql_with_dashboard(
        db: Session,
        user: User,
        chat: Chat,
        user_message: Message,
        user_query: str,
        db_connection_id: UUID,
        chat_history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Execute SQL query + create dashboard.
        
        Args:
            db: Database session
            user: User object
            chat: Chat object
            user_message: User message object
            user_query: User's query
            db_connection_id: Database connection ID
            chat_history: Chat history

        Returns:
            Dict: Response with SQL, data, and dashboard
        """
        print(f"📊📈 Executing SQL + Dashboard...")
        
        try:
            # Step 1: Execute SQL query
            # Get DB config
            db_config = (
                db.query(DBConnection)
                .filter(
                    DBConnection.id == db_connection_id, DBConnection.user_id == user.id
                )
                .first()
            )

            if not db_config:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Database connection not found",
                )
            
            sql_agent = SQLAgent(claude_service, db_config, db_connection_manager)
            sql_results = await sql_agent.process(user_query, chat_history)
            
            if not sql_results.get("success"):
                error_msg = f"Could not execute query: {sql_results.get('error', 'Unknown error')}"
                assistant_message = Message(
                    chat_id=chat.id,
                    role="assistant",
                    content=error_msg,
                    message_metadata={"error": True, "mode": "sql"},
                )
                db.add(assistant_message)
                chat.message_count += 1
                db.commit()
                return {
                    "success": False,
                    "chat_id": chat.id,
                    "message_id": assistant_message.id,
                    "error": error_msg
                }
            
            # Save query history
            query_history = QueryHistory(
                user_id=user.id,
                chat_id=chat.id,
                message_id=user_message.id,
                db_connection_id=db_connection_id,
                natural_language_query=user_query,
                generated_sql=sql_results.get("sql_query", ""),
                sql_valid=True,
                execution_status="success",
                execution_time_ms=sql_results.get("execution_time_ms", 0),
                row_count=sql_results.get("row_count", 0),
            )
            db.add(query_history)
            db.commit()
            db.refresh(query_history)
            
            # Step 2: Create dashboard
            dashboard_agent = DashboardAgent(claude_service)
            
            try:
                dashboard_results = await dashboard_agent.process(
                    query_results=sql_results,
                    user_query=user_query,
                    sql_query=sql_results.get("sql_query"),
                    timeout=30
                )
                
                if not dashboard_results.get("success"):
                    print(f"⚠️ Dashboard failed: {dashboard_results.get('error')}")
                    # Continue with SQL only
                    response_content = f"Found {sql_results['row_count']} results, but couldn't create visualization."
                    dashboard_html = None
                else:
                    response_content = f"I've created a dashboard with the data. Found {sql_results['row_count']} rows."
                    dashboard_html = dashboard_results.get("dashboard_html")
                    
            except Exception as e:
                print(f"💥 Dashboard exception: {str(e)}")
                response_content = f"Found {sql_results['row_count']} results, but couldn't create visualization."
                dashboard_html = None
                dashboard_results = {"success": False}
            
            # Save assistant message
            assistant_message = Message(
                chat_id=chat.id,
                role="assistant",
                content=response_content,
                message_metadata={
                    "mode": "sql",
                    "agent": "sql+dashboard",
                    "sql_query": sql_results.get("sql_query"),
                    "execution_time_ms": sql_results.get("execution_time_ms"),
                    "row_count": sql_results.get("row_count"),
                    "dashboard_type": dashboard_results.get("dashboard_type"),
                    "chart_count": dashboard_results.get("chart_count", 0),
                },
            )
            db.add(assistant_message)
            chat.message_count += 1
            chat.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(assistant_message)
            
            # Save dashboard history if successful
            if dashboard_results.get("success") and dashboard_html:
                dashboard_history = DashboardHistory(
                    user_id=user.id,
                    message_id=assistant_message.id,
                    query_history_id=query_history.id,
                    dashboard_type="html",
                    dashboard_content=dashboard_html,
                    chart_count=dashboard_results.get("chart_count", 0),
                    chart_types=dashboard_results.get("chart_types", []),
                    data_summary={},
                )
                db.add(dashboard_history)
                db.commit()
            
            return {
                "success": True,
                "chat_id": chat.id,
                "message_id": assistant_message.id,
                "user_message": user_query,
                "assistant_message": response_content,
                "mode": "sql",
                "sql_query": sql_results.get("sql_query"),
                "execution_time_ms": sql_results.get("execution_time_ms", 0),
                "row_count": sql_results.get("row_count", 0),
                "data": sql_results.get("data", []),
                "columns": sql_results.get("columns", []),
                "dashboard_html": dashboard_html
            }
            
        except Exception as e:
            error_msg = f"Dashboard query error: {str(e)}"
            print(f"💥 Error in _execute_sql_with_dashboard: {error_msg}")
            
            assistant_message = Message(
                chat_id=chat.id,
                role="assistant",
                content=error_msg,
                message_metadata={"error": True, "mode": "sql"},
            )
            db.add(assistant_message)
            chat.message_count += 1
            db.commit()
            
            return {
                "success": False,
                "chat_id": chat.id,
                "message_id": assistant_message.id,
                "error": error_msg
            }
