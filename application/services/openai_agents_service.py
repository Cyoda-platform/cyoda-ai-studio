"""
OpenAI Agents Service for AI Assistant Application

Provides integration with OpenAI's Agents SDK for:
- Agent-based conversation with tool support
- Multi-model support via environment configuration
- Session management and persistence

Following OpenAI Agents best practices from https://github.com/openai/openai-agents-python
"""

import logging
import os
from typing import Any, Optional

from agents import Agent, Runner
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class OpenAIAgentsService:
    """
    OpenAI Agents SDK integration service.

    Supports multiple OpenAI models and provides agent-based
    conversation capabilities for the AI Assistant.
    """

    def __init__(self) -> None:
        """
        Initialize OpenAI Agents client with configuration from environment.

        Environment variables:
            OPENAI_API_KEY: Required API key for OpenAI
            OPENAI_MODEL: Model name (default: gpt-4o)
            OPENAI_TEMPERATURE: Temperature for generation (default: 0.7)
            OPENAI_MAX_TOKENS: Max output tokens (default: 8192)
        """
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning(
                "OPENAI_API_KEY not set - OpenAIAgentsService will not function"
            )

        self.model_name = os.getenv("OPENAI_MODEL", "gpt-4o")
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "8192"))

        # Initialize client
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None

        logger.info(
            f"OpenAIAgentsService initialized with model={self.model_name}, "
            f"temperature={self.temperature}, max_tokens={self.max_tokens}"
        )

    async def generate_response(
        self,
        prompt: str,
        context: Optional[list[dict[str, str]]] = None,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate AI response using OpenAI Agents.

        Args:
            prompt: User message/question
            context: Conversation history as list of {"role": "user/assistant", "content": "..."}
            system_instruction: Optional system prompt to guide AI behavior
            temperature: Override default temperature (0.0-1.0)
            max_tokens: Override default max output tokens

        Returns:
            Generated text response

        Raises:
            Exception: If API key is not configured or API call fails
        """
        if not self.client:
            raise Exception("OpenAI client not initialized - check OPENAI_API_KEY")

        try:
            # Build messages from context + current prompt
            messages = self._build_messages(prompt, context, system_instruction)

            logger.debug(
                f"Generating response with model={self.model_name}, "
                f"context_messages={len(context) if context else 0}"
            )

            # Generate response
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
            )

            # Extract text from response
            result = response.choices[0].message.content or ""
            logger.debug(f"Generated response length: {len(result)} characters")

            return result

        except Exception as e:
            logger.exception(f"Error generating response: {e}")
            raise Exception(f"Failed to generate AI response: {str(e)}") from e

    def _build_messages(
        self,
        current_prompt: str,
        context: Optional[list[dict[str, str]]] = None,
        system_instruction: Optional[str] = None,
    ) -> list[dict[str, str]]:
        """
        Build messages for API call from context and current prompt.

        Args:
            current_prompt: Current user message
            context: Previous conversation messages
            system_instruction: Optional system prompt

        Returns:
            Messages formatted for OpenAI API
        """
        messages: list[dict[str, str]] = []

        # Add system instruction if provided
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})

        # Add context messages
        if context:
            for msg in context:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                messages.append({"role": role, "content": content})

        # Add current prompt
        messages.append({"role": "user", "content": current_prompt})

        return messages

    def is_configured(self) -> bool:
        """
        Check if the service is properly configured.

        Returns:
            True if API key is set and client is initialized
        """
        return self.client is not None

    async def create_agent(
        self,
        name: str,
        instructions: str,
        tools: Optional[list[Any]] = None,
    ) -> Agent:
        """
        Create an OpenAI Agent with the given configuration.

        Args:
            name: Agent name
            instructions: System instructions for the agent
            tools: Optional list of tools the agent can use

        Returns:
            Configured Agent instance

        Raises:
            Exception: If API key is not configured
        """
        if not self.client:
            raise Exception("OpenAI client not initialized - check OPENAI_API_KEY")

        logger.debug(f"Creating agent: {name}")

        agent = Agent(
            name=name,
            instructions=instructions,
            tools=tools or [],
        )

        logger.debug(f"Agent created: {name}")
        return agent

    async def run_agent(
        self,
        agent: Agent,
        user_message: str,
        context: Optional[list[dict[str, str]]] = None,
    ) -> str:
        """
        Run an agent with a user message.

        Args:
            agent: The Agent to run
            user_message: User's message/question
            context: Optional conversation history

        Returns:
            Agent's response

        Raises:
            Exception: If agent execution fails
        """
        try:
            logger.debug(f"Running agent: {agent.name}")

            # Build full prompt with context if provided
            if context:
                # Format context as conversation history
                history_text = "\n".join(
                    [f"{msg['role']}: {msg['content']}" for msg in context]
                )
                full_prompt = f"{history_text}\nuser: {user_message}"
            else:
                full_prompt = user_message

            # Run the agent
            result = await Runner.run(agent, full_prompt)

            logger.debug(f"Agent execution completed: {agent.name}")
            return result.final_output or ""

        except Exception as e:
            logger.exception(f"Error running agent: {e}")
            raise Exception(f"Failed to run agent: {str(e)}") from e

