"""
Redis Service - Simplified in-memory version (no Redis required)
"""

import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID


class RedisService:
    """
    Simplified in-memory service (no Redis required).
    State is stored in memory and cleared on restart.
    """

    def __init__(self):
        """Initialize in-memory storage"""
        self.state_store: Dict[str, Any] = {}
        self.schema_cache: Dict[UUID, Any] = {}  # Changed from int to UUID
        self.conversations: Dict[str, List[Dict]] = {}
        print("✅ In-memory state service initialized (no Redis required)")

    async def set_state(
        self,
        session_id: str,
        state: Dict[str, Any],
        ttl_minutes: Optional[int] = None
    ) -> bool:
        """
        Store agent state in memory.

        Args:
            session_id: Unique session identifier
            state: State dictionary to store
            ttl_minutes: Ignored (no TTL in memory)

        Returns:
            bool: Success status
        """
        try:
            self.state_store[session_id] = state
            return True
        except Exception as e:
            print(f"❌ Error storing state: {e}")
            return False

    async def get_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve agent state from memory.

        Args:
            session_id: Unique session identifier

        Returns:
            Optional[Dict]: State dictionary or None if not found
        """
        try:
            return self.state_store.get(session_id)
        except Exception as e:
            print(f"❌ Error retrieving state: {e}")
            return None

    async def delete_state(self, session_id: str) -> bool:
        """
        Delete agent state from memory.

        Args:
            session_id: Unique session identifier

        Returns:
            bool: Success status
        """
        try:
            if session_id in self.state_store:
                del self.state_store[session_id]
            return True
        except Exception as e:
            print(f"❌ Error deleting state: {e}")
            return False

    async def cache_schema(
        self,
        db_connection_id: UUID,
        schema: Dict[str, Any],
        ttl_minutes: int = 60
    ) -> bool:
        """
        Cache database schema in memory.

        Args:
            db_connection_id: Database connection ID (UUID)
            schema: Schema dictionary
            ttl_minutes: Ignored (no TTL in memory)

        Returns:
            bool: Success status
        """
        try:
            self.schema_cache[db_connection_id] = schema
            return True
        except Exception as e:
            print(f"❌ Error caching schema: {e}")
            return False

    async def get_cached_schema(
        self,
        db_connection_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached database schema from memory.

        Args:
            db_connection_id: Database connection ID

        Returns:
            Optional[Dict]: Schema dictionary or None if not found
        """
        try:
            return self.schema_cache.get(db_connection_id)
        except Exception as e:
            print(f"❌ Error retrieving cached schema: {e}")
            return None

    async def add_conversation_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a message to conversation history in memory.

        Args:
            session_id: Unique session identifier
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional metadata

        Returns:
            bool: Success status
        """
        try:
            if session_id not in self.conversations:
                self.conversations[session_id] = []
            
            message = {
                "role": role,
                "content": content,
                "metadata": metadata or {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.conversations[session_id].append(message)
            return True
        except Exception as e:
            print(f"❌ Error adding conversation message: {e}")
            return False

    async def get_conversation_history(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Retrieve conversation history from memory.

        Args:
            session_id: Unique session identifier
            limit: Optional limit on number of messages

        Returns:
            list: List of message dictionaries
        """
        try:
            messages = self.conversations.get(session_id, [])
            
            if limit and len(messages) > limit:
                return messages[-limit:]
            
            return messages
        except Exception as e:
            print(f"❌ Error retrieving conversation history: {e}")
            return []

    def close(self):
        """Clean up (no-op for in-memory)"""
        print("✅ In-memory service cleaned up")


# Global instance
redis_service = RedisService()

