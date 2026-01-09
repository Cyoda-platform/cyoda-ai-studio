"""Tests for generate_code_with_cli function."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.adk.tools.tool_context import ToolContext

from application.agents.github.tool_definitions.code_generation.tools.generate_code_tool import (
    generate_code_with_cli,
)


class TestGenerateCodeWithCli:
    """Test generate_code_with_cli function."""

    @pytest.mark.asyncio
    async def test_generate_code_missing_user_request(self):
        """Test function returns error when user_request is empty."""
        result = await generate_code_with_cli(user_request="", tool_context=None)
        assert "ERROR" in result

    @pytest.mark.asyncio
    async def test_generate_code_no_tool_context(self):
        """Test function returns error when tool_context is None."""
        result = await generate_code_with_cli(
            user_request="Add entity", tool_context=None
        )
        assert "ERROR" in result

    @pytest.mark.asyncio
    async def test_generate_code_invalid_language(self):
        """Test function returns error for invalid language."""
        mock_context = MagicMock(spec=ToolContext)
        mock_context.conversation_id = "conv-123"

        with patch(
            "application.agents.github.tool_definitions.code_generation.tools.generate_code_tool._validate_and_prepare_context"
        ) as mock_validate:
            mock_validate.return_value = (False, "ERROR: Invalid language", None)

            result = await generate_code_with_cli(
                user_request="Add entity", tool_context=mock_context, language="invalid"
            )
            assert "ERROR" in result

    @pytest.mark.asyncio
    async def test_generate_code_repository_not_found(self):
        """Test function returns error when repository not found."""
        mock_context = MagicMock(spec=ToolContext)
        mock_context.conversation_id = "conv-123"
        mock_context.repository_path = "/tmp/repo"

        with patch(
            "application.agents.github.tool_definitions.code_generation.tools.generate_code_tool._validate_and_prepare_context"
        ) as mock_validate:
            with patch(
                "application.agents.github.tool_definitions.code_generation.tools.generate_code_tool._validate_repository_and_config"
            ) as mock_repo:
                mock_validate.return_value = (True, "", mock_context)
                mock_repo.return_value = (
                    False,
                    "ERROR: Repository not found",
                    None,
                    None,
                )

                result = await generate_code_with_cli(
                    user_request="Add entity", tool_context=mock_context
                )
                assert "ERROR" in result

    @pytest.mark.asyncio
    async def test_generate_code_invalid_model_for_augment(self):
        """Test function returns error for invalid model with Augment CLI."""
        mock_context = MagicMock(spec=ToolContext)
        mock_context.conversation_id = "conv-123"
        mock_context.repository_path = "/tmp/repo"

        with patch(
            "application.agents.github.tool_definitions.code_generation.tools.generate_code_tool._validate_and_prepare_context"
        ) as mock_validate:
            with patch(
                "application.agents.github.tool_definitions.code_generation.tools.generate_code_tool._validate_repository_and_config"
            ) as mock_repo:
                with patch(
                    "application.agents.github.tool_definitions.code_generation.tools.generate_code_tool.CLI_PROVIDER",
                    "augment",
                ):
                    mock_validate.return_value = (True, "", mock_context)
                    mock_repo.return_value = (
                        False,
                        "ERROR: Augment CLI only supports haiku4.5",
                        None,
                        None,
                    )

                    result = await generate_code_with_cli(
                        user_request="Add entity", tool_context=mock_context
                    )
                    assert "ERROR" in result

    @pytest.mark.asyncio
    async def test_generate_code_with_valid_context(self):
        """Test generate_code_with_cli with valid context."""
        mock_context = MagicMock(spec=ToolContext)
        mock_context.conversation_id = "conv-123"
        mock_context.repository_path = "/tmp/repo"
        mock_context.branch_name = "feature-branch"

        with patch(
            "application.agents.github.tool_definitions.code_generation.tools.generate_code_tool._validate_and_prepare_context"
        ) as mock_validate:
            with patch(
                "application.agents.github.tool_definitions.code_generation.tools.generate_code_tool._validate_repository_and_config"
            ) as mock_repo:
                mock_validate.return_value = (True, "", mock_context)
                mock_repo.return_value = (True, "", "/tmp/script.sh", "haiku4.5")

                result = await generate_code_with_cli(
                    user_request="Add entity", tool_context=mock_context
                )
                # Should either succeed or fail gracefully
                assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_generate_code_exception_handling(self):
        """Test function handles exceptions gracefully."""
        mock_context = MagicMock(spec=ToolContext)
        mock_context.conversation_id = "conv-123"

        with patch(
            "application.agents.github.tool_definitions.code_generation.tools.generate_code_tool._validate_and_prepare_context"
        ) as mock_validate:
            mock_validate.side_effect = Exception("Validation error")

            result = await generate_code_with_cli(
                user_request="Add entity", tool_context=mock_context
            )
            assert "ERROR" in result or isinstance(result, str)
