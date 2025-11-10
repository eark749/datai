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
from app.services.claude_service import claude_service
from app.services.db_service import db_connection_manager
from fastapi import HTTPException, status


class ChatService:
    """Service for managing chats and orchestrating AI agents"""
    
    @staticmethod
    def get_or_create_chat(
        db: Session,
        user: User,
        db_connection_id: UUID,
        chat_id: Optional[UUID] = None,
        title: Optional[str] = None
    ) -> Chat:
        """
        Get existing chat or create a new one.
        
        Args:
            db: Database session
            user: Current user
            db_connection_id: Database connection ID
            chat_id: Optional existing chat ID
            title: Optional chat title
            
        Returns:
            Chat: Chat object
        """
        if chat_id:
            chat = db.query(Chat).filter(
                Chat.id == chat_id,
                Chat.user_id == user.id
            ).first()
            
            if not chat:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chat not found"
                )
            
            return chat
        else:
            # Create new chat
            new_chat = Chat(
                user_id=user.id,
                db_connection_id=db_connection_id,
                title=title or "New Chat"
            )
            db.add(new_chat)
            db.commit()
            db.refresh(new_chat)
            return new_chat
    
    @staticmethod
    def generate_chat_title(user_query: str) -> str:
        """Generate a chat title from the first user query"""
        # Take first 50 chars
        title = user_query[:50]
        if len(user_query) > 50:
            title += "..."
        return title
    
    @staticmethod
    def get_chat_history(db: Session, chat_id: UUID) -> List[Dict[str, Any]]:
        """
        Get chat history formatted for AI agents.
        
        Args:
            db: Database session
            chat_id: Chat ID
            
        Returns:
            List[Dict]: Formatted chat history
        """
        messages = db.query(Message).filter(
            Message.chat_id == chat_id
        ).order_by(Message.created_at).all()
        
        history = []
        for msg in messages:
            if msg.role in ["user", "assistant"]:
                history.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        return history
    
    @staticmethod
    async def process_chat_query(
        db: Session,
        user: User,
        user_query: str,
        db_connection_id: UUID,
        chat_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Process a chat query through Agent 1 and Agent 2.
        
        Args:
            db: Database session
            user: Current user
            user_query: User's natural language query
            db_connection_id: Database connection ID
            chat_id: Optional existing chat ID
            
        Returns:
            Dict: Complete response with SQL, data, and dashboard
        """
        # Get or create chat
        chat = ChatService.get_or_create_chat(
            db, user, db_connection_id, chat_id
        )
        
        # Update chat title if it's the first message
        if chat.message_count == 0:
            chat.title = ChatService.generate_chat_title(user_query)
        
        # Get database connection
        db_config = db.query(DBConnection).filter(
            DBConnection.id == db_connection_id,
            DBConnection.user_id == user.id
        ).first()
        
        if not db_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Database connection not found"
            )
        
        # Get chat history
        chat_history = ChatService.get_chat_history(db, chat.id)
        
        # Save user message
        user_message = Message(
            chat_id=chat.id,
            role="user",
            content=user_query,
            metadata={}
        )
        db.add(user_message)
        chat.message_count += 1
        db.commit()
        db.refresh(user_message)
        
        try:
            # Initialize Agent 1 (SQL Agent)
            sql_agent = SQLAgent(
                claude_service,
                db_config,
                db_connection_manager
            )
            
            # Process query with Agent 1
            sql_results = await sql_agent.process(user_query, chat_history)
            
            if not sql_results.get("success"):
                # SQL generation/execution failed
                error_msg = f"Could not execute query: {sql_results.get('error', 'Unknown error')}"
                
                # Save error message
                assistant_message = Message(
                    chat_id=chat.id,
                    role="assistant",
                    content=error_msg,
                    metadata={"error": True}
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
                row_count=sql_results.get("row_count", 0)
            )
            db.add(query_history)
            db.commit()
            db.refresh(query_history)
            
            # Initialize Agent 2 (Dashboard Agent)
            dashboard_agent = DashboardAgent(claude_service)
            
            # Process results with Agent 2
            dashboard_results = await dashboard_agent.process(
                query_results=sql_results,
                user_query=user_query,
                sql_query=sql_results.get("sql_query")
            )
            
            # Prepare response message
            response_content = f"I've analyzed the data and created a dashboard for you."
            
            if sql_results.get("row_count", 0) > 0:
                response_content += f"\n\nFound {sql_results['row_count']} rows."
            
            # Save assistant message
            assistant_message = Message(
                chat_id=chat.id,
                role="assistant",
                content=response_content,
                metadata={
                    "sql_query": sql_results.get("sql_query"),
                    "execution_time_ms": sql_results.get("execution_time_ms"),
                    "row_count": sql_results.get("row_count"),
                    "dashboard_type": dashboard_results.get("dashboard_type"),
                    "chart_count": dashboard_results.get("chart_count"),
                    "chart_types": dashboard_results.get("chart_types")
                }
            )
            db.add(assistant_message)
            chat.message_count += 1
            chat.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(assistant_message)
            
            # Save dashboard history
            if dashboard_results.get("success") and dashboard_results.get("dashboard_html"):
                dashboard_history = DashboardHistory(
                    user_id=user.id,
                    message_id=assistant_message.id,
                    query_history_id=query_history.id,
                    dashboard_type="html",
                    dashboard_content=dashboard_results["dashboard_html"],
                    chart_count=dashboard_results.get("chart_count", 0),
                    chart_types=dashboard_results.get("chart_types", []),
                    data_summary={}
                )
                db.add(dashboard_history)
                db.commit()
            
            return {
                "success": True,
                "chat_id": chat.id,
                "message_id": assistant_message.id,
                "user_message": user_query,
                "assistant_message": response_content,
                "sql_query": sql_results.get("sql_query"),
                "data": sql_results.get("data", []),
                "columns": sql_results.get("columns", []),
                "dashboard_html": dashboard_results.get("dashboard_html"),
                "execution_time_ms": sql_results.get("execution_time_ms", 0),
                "row_count": sql_results.get("row_count", 0)
            }
            
        except Exception as e:
            # Handle unexpected errors
            error_msg = f"An error occurred: {str(e)}"
            
            assistant_message = Message(
                chat_id=chat.id,
                role="assistant",
                content=error_msg,
                metadata={"error": True, "error_detail": str(e)}
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

