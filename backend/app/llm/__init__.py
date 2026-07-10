"""LLM integration — public barrel (agentic R5).

Import from here for chat + tools::

    from app.llm import chat_completion, build_system_prompt, TOOL_DEFINITIONS, execute_tool
"""

from app.llm.client import LLMProviderError, LLMResponse, chat_completion
from app.llm.prompts import build_system_prompt
from app.llm.tools import TOOL_DEFINITIONS, execute_tool

__all__ = [
    "LLMProviderError",
    "LLMResponse",
    "chat_completion",
    "build_system_prompt",
    "TOOL_DEFINITIONS",
    "execute_tool",
]
