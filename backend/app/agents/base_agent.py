"""
Base Agent Class
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from app.services.claude_service import ClaudeService


class BaseAgent(ABC):
    """
    Abstract base class for AI agents.
    Provides common functionality for Claude API integration.
    """
    
    def __init__(self, claude_service: ClaudeService):
        """
        Initialize base agent.
        
        Args:
            claude_service: Claude API service instance
        """
        self.claude = claude_service
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for this agent.
        Must be implemented by subclasses.
        
        Returns:
            str: System prompt
        """
        pass
    
    @abstractmethod
    async def process(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Process a request with this agent.
        Must be implemented by subclasses.
        
        Returns:
            Dict: Processing result
        """
        pass
    
    def format_chat_history(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format chat history for Claude API.
        
        Args:
            messages: List of message dictionaries with role and content
            
        Returns:
            List: Formatted messages for Claude
        """
        formatted = []
        for msg in messages:
            formatted.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        return formatted

