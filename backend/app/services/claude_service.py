"""
Claude API Service - Integration with Anthropic Claude
"""

from anthropic import Anthropic, AsyncAnthropic
from typing import List, Dict, Any, Optional
import json

from app.config import settings


class ClaudeService:
    """
    Service for interacting with Anthropic Claude API.
    Supports tool calling and streaming responses.
    """

    def __init__(self):
        """Initialize Claude client"""
        if (
            not settings.ANTHROPIC_API_KEY
            or settings.ANTHROPIC_API_KEY == "your-api-key-here"
        ):
            print("⚠️ WARNING: ANTHROPIC_API_KEY not properly configured!")
            print(
                f"Current value: {settings.ANTHROPIC_API_KEY[:20] if settings.ANTHROPIC_API_KEY else 'None'}..."
            )
        else:
            print(f"✅ Claude API Key loaded: {settings.ANTHROPIC_API_KEY[:15]}...")

        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.async_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        # Using Claude 3 Haiku for cost-effective responses
        self.model = "claude-3-haiku-20240307"
        self.max_tokens = 4096
        print(f"🤖 ClaudeService initialized with model: {self.model}")

    def create_message(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 1.0,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a message with Claude (synchronous).

        Args:
            messages: List of message objects with role and content
            tools: Optional list of tool definitions
            system: Optional system prompt
            max_tokens: Maximum tokens in response
            temperature: Temperature for sampling (0-1)
            model: Optional model override (default: uses self.model)

        Returns:
            Dict: Claude API response
        """
        kwargs = {
            "model": model or self.model,  # Allow model override
            "messages": messages,
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": temperature,
        }

        if tools:
            kwargs["tools"] = tools

        if system:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)

        return self._format_response(response)

    async def create_message_async(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 1.0,
        use_cache: bool = True,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a message with Claude (asynchronous).

        Args:
            messages: List of message objects with role and content
            tools: Optional list of tool definitions
            system: Optional system prompt
            max_tokens: Maximum tokens in response
            temperature: Temperature for sampling (0-1)
            use_cache: Enable prompt caching for faster responses (default: True)
            model: Optional model override (default: uses self.model)

        Returns:
            Dict: Claude API response
        """
        kwargs = {
            "model": model or self.model,  # Allow model override
            "messages": messages,
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": temperature,
        }

        if tools:
            kwargs["tools"] = tools

        if system:
            # Enable prompt caching for system prompts (huge speed boost!)
            if use_cache and len(system) > 1024:  # Only cache large system prompts
                kwargs["system"] = [
                    {
                        "type": "text",
                        "text": system,
                        "cache_control": {"type": "ephemeral"},
                    }
                ]
            else:
                kwargs["system"] = system

        response = await self.async_client.messages.create(**kwargs)

        return self._format_response(response)

    def _format_response(self, response) -> Dict[str, Any]:
        """
        Format Claude API response into a dictionary.

        Args:
            response: Raw Claude API response

        Returns:
            Dict: Formatted response
        """
        return {
            "id": response.id,
            "model": response.model,
            "role": response.role,
            "content": response.content,
            "stop_reason": response.stop_reason,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        }

    def extract_text_content(self, response: Dict[str, Any]) -> str:
        """
        Extract text content from Claude response.

        Args:
            response: Claude API response

        Returns:
            str: Extracted text content
        """
        text_parts = []
        for content_block in response["content"]:
            if hasattr(content_block, "text"):
                text_parts.append(content_block.text)
            elif isinstance(content_block, dict) and "text" in content_block:
                text_parts.append(content_block["text"])

        return "\n".join(text_parts)

    def extract_tool_calls(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract tool use calls from Claude response.

        Args:
            response: Claude API response

        Returns:
            List: List of tool call objects
        """
        tool_calls = []
        for content_block in response["content"]:
            if hasattr(content_block, "type") and content_block.type == "tool_use":
                tool_calls.append(
                    {
                        "id": content_block.id,
                        "name": content_block.name,
                        "input": content_block.input,
                    }
                )
            elif (
                isinstance(content_block, dict)
                and content_block.get("type") == "tool_use"
            ):
                tool_calls.append(
                    {
                        "id": content_block["id"],
                        "name": content_block["name"],
                        "input": content_block["input"],
                    }
                )

        return tool_calls

    def create_tool_result_message(
        self, tool_use_id: str, result: Any
    ) -> Dict[str, Any]:
        """
        Create a tool result message for Claude.

        Args:
            tool_use_id: ID of the tool use
            result: Result of the tool execution

        Returns:
            Dict: Tool result message content
        """
        return {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": json.dumps(result) if not isinstance(result, str) else result,
        }

    def build_tool_definition(
        self, name: str, description: str, input_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build a tool definition for Claude.

        Args:
            name: Tool name
            description: Tool description
            input_schema: JSON schema for tool input parameters

        Returns:
            Dict: Tool definition
        """
        return {"name": name, "description": description, "input_schema": input_schema}


# Global instance
claude_service = ClaudeService()
