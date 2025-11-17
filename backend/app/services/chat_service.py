"""
Chat Service - Orchestration Layer (Agents removed - ready for new architecture)
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
from app.services.claude_service import claude_service
from app.services.db_service import db_connection_manager
from fastapi import HTTPException, status


class ChatService:
    """Service for managing chats - ready for new architecture implementation"""

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
                # Skip error messages from history to prevent confusion
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
        Process chat query using LangGraph multi-agent workflow.

        Args:
            db: Database session
            user: Current user
            user_query: User's natural language query
            chat_id: Optional existing chat ID
            db_connection_id: Optional database connection ID

        Returns:
            Dict: Response with agent results
        """
        from app.agents.state import create_initial_state
        from app.agents.graph import run_agent_workflow
        import time
        
        start_time = time.time()
        
        # Get or create chat
        chat = ChatService.get_or_create_chat(db, user, db_connection_id, chat_id)

        # Validate database consistency
        if chat.db_connection_id and db_connection_id:
            if chat.db_connection_id != db_connection_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot change database connection mid-chat",
                )
        
        # Use chat's database connection if available
        effective_db_id = chat.db_connection_id or db_connection_id

        # Update chat title if it's the first message
        if chat.message_count == 0:
            chat.title = ChatService.generate_chat_title(user_query)

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
            # Create initial state for agent workflow
            initial_state = create_initial_state(
                user_query=user_query,
                session_id=str(chat.id),
                user_id=user.id,
                database_id=effective_db_id  # Pass UUID directly, not converted to int
            )
            
            # Run agent workflow
            final_state = await run_agent_workflow(initial_state, db)
            
            # Extract results
            response_text = final_state.get("supervisor_response", "I processed your request.")
            sql_query = final_state.get("sql_query")
            query_results = final_state.get("query_results", [])
            dashboard_html = final_state.get("dashboard_html")
            agent_used = final_state.get("agent_used", "supervisor")
            error = final_state.get("error")
            execution_time = final_state.get("execution_time", 0)
            
            # Prepare metadata
            message_metadata = {
                "agent_used": agent_used,
                "execution_time": execution_time,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if error:
                message_metadata["error"] = error
            
            if sql_query:
                message_metadata["sql_query"] = sql_query
            
            if dashboard_html:
                message_metadata["has_dashboard"] = True
            
            # Save assistant message
            assistant_message = Message(
                chat_id=chat.id,
                role="assistant",
                content=response_text,
                message_metadata=message_metadata,
            )
            db.add(assistant_message)
            chat.message_count += 1
            chat.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(assistant_message)
            
            # Save SQL query history if applicable
            if sql_query and query_results is not None:
                query_history = QueryHistory(
                    user_id=user.id,
                    db_connection_id=effective_db_id,
                    chat_id=chat.id,
                    message_id=assistant_message.id,
                    query_text=sql_query,
                    result_data=query_results[:100],  # Store first 100 rows
                    row_count=len(query_results),
                    execution_time_ms=int(execution_time * 1000),
                    status="success" if not error else "failed",
                )
                db.add(query_history)
            
            # Save dashboard history if applicable
            if dashboard_html:
                dashboard_history = DashboardHistory(
                    user_id=user.id,
                    chat_id=chat.id,
                    message_id=assistant_message.id,
                    dashboard_html=dashboard_html,
                    dashboard_config=final_state.get("dashboard_config", {}),
                )
                db.add(dashboard_history)
            
            db.commit()
            
            total_time = time.time() - start_time
            
            return {
                "success": True,
                "chat_id": chat.id,
                "message_id": assistant_message.id,
                "user_message": user_query,
                "assistant_message": response_text,
                "mode": agent_used or "supervisor",  # Ensure mode is never None
                "sql_query": sql_query,
                "data": query_results if query_results is not None else [],  # Ensure data is always a list
                "dashboard_html": dashboard_html,
                "execution_time_ms": int(total_time * 1000),
                "row_count": len(query_results) if query_results else 0,
                "error": error
            }
                
        except Exception as e:
            # Handle unexpected errors
            error_msg = f"An error occurred: {str(e)}"
            print(f"💥 Error in process_chat_query: {error_msg}")
            import traceback
            traceback.print_exc()

            # Rollback the transaction to clear the error state
            db.rollback()

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
