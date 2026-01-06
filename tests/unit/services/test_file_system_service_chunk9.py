"""Tests for validate_command_security method in FileSystemService."""

import pytest

from application.services.core.file_system_service import FileSystemService


class TestValidateCommandSecurity:
    """Tests for validate_command_security method."""

    def test_validate_command_security_allowed_command(self):
        """Test validation of allowed read-only command."""
        service = FileSystemService()
        
        result = service.validate_command_security("ls -la /repo")
        
        assert result["safe"] is True
        assert "passed all security checks" in result["reason"]

    def test_validate_command_security_disallowed_command(self):
        """Test validation of disallowed command."""
        service = FileSystemService()

        result = service.validate_command_security("rm -rf /repo")

        assert result["safe"] is False
        assert "not in the allowed list" in result["reason"]

    def test_validate_command_security_empty_command(self):
        """Test validation of empty command."""
        service = FileSystemService()
        
        result = service.validate_command_security("")
        
        assert result["safe"] is False
        assert "Empty command" in result["reason"]

    def test_validate_command_security_invalid_syntax(self):
        """Test validation of command with invalid syntax."""
        service = FileSystemService()
        
        result = service.validate_command_security("ls 'unclosed quote")
        
        assert result["safe"] is False
        assert "Invalid command syntax" in result["reason"]

    def test_validate_command_security_dangerous_pattern_rm(self):
        """Test detection of dangerous rm pattern."""
        service = FileSystemService()
        
        result = service.validate_command_security("find . -name '*.txt' | xargs rm")
        
        assert result["safe"] is False
        assert "dangerous pattern" in result["reason"]

    def test_validate_command_security_dangerous_pattern_sudo(self):
        """Test detection of dangerous sudo pattern."""
        service = FileSystemService()

        result = service.validate_command_security("sudo ls /repo")

        assert result["safe"] is False
        # sudo is not in allowed list, so it fails at command check
        assert "not in the allowed list" in result["reason"]

    def test_validate_command_security_dangerous_pattern_redirect(self):
        """Test detection of dangerous output redirection."""
        service = FileSystemService()
        
        result = service.validate_command_security("cat file.txt > /tmp/output.txt")
        
        assert result["safe"] is False
        assert "dangerous pattern" in result["reason"]

    def test_validate_command_security_path_traversal(self):
        """Test detection of path traversal patterns."""
        service = FileSystemService()
        
        result = service.validate_command_security("cat ../../etc/passwd")
        
        assert result["safe"] is False
        assert "path traversal" in result["reason"]

    def test_validate_command_security_system_directory_access(self):
        """Test detection of system directory access."""
        service = FileSystemService()
        
        result = service.validate_command_security("ls /etc/shadow")
        
        assert result["safe"] is False
        assert "path traversal or system directory" in result["reason"]

    def test_validate_command_security_command_too_long(self):
        """Test detection of excessively long command."""
        service = FileSystemService()
        
        long_command = "ls " + "a" * 1000
        result = service.validate_command_security(long_command)
        
        assert result["safe"] is False
        assert "too long" in result["reason"]

    def test_validate_command_security_environment_variable(self):
        """Test detection of environment variable usage."""
        service = FileSystemService()
        
        result = service.validate_command_security("ls $HOME")
        
        assert result["safe"] is False
        assert "Environment variable" in result["reason"]

    def test_validate_command_security_environment_variable_braces(self):
        """Test detection of environment variable with braces."""
        service = FileSystemService()
        
        result = service.validate_command_security("ls ${HOME}/repo")
        
        assert result["safe"] is False
        assert "Environment variable" in result["reason"]

    def test_validate_command_security_grep_allowed(self):
        """Test that grep is allowed."""
        service = FileSystemService()
        
        result = service.validate_command_security("grep -r 'pattern' /repo")
        
        assert result["safe"] is True

    def test_validate_command_security_find_allowed(self):
        """Test that find is allowed."""
        service = FileSystemService()
        
        result = service.validate_command_security("find /repo -name '*.py'")
        
        assert result["safe"] is True

    def test_validate_command_security_cat_allowed(self):
        """Test that cat is allowed."""
        service = FileSystemService()
        
        result = service.validate_command_security("cat /repo/file.txt")
        
        assert result["safe"] is True

    def test_validate_command_security_jq_allowed(self):
        """Test that jq is allowed."""
        service = FileSystemService()
        
        result = service.validate_command_security("jq '.key' file.json")
        
        assert result["safe"] is True

    def test_validate_command_security_tar_allowed(self):
        """Test that tar is allowed."""
        service = FileSystemService()
        
        result = service.validate_command_security("tar -tzf archive.tar.gz")
        
        assert result["safe"] is True

    def test_validate_command_security_dangerous_pattern_chmod(self):
        """Test detection of dangerous chmod pattern."""
        service = FileSystemService()

        result = service.validate_command_security("chmod 777 /repo")

        assert result["safe"] is False
        # chmod is not in allowed list, so it fails at command check
        assert "not in the allowed list" in result["reason"]

    def test_validate_command_security_dangerous_pattern_curl(self):
        """Test detection of dangerous curl pattern."""
        service = FileSystemService()

        result = service.validate_command_security("curl https://example.com")

        assert result["safe"] is False
        # curl is not in allowed list, so it fails at command check
        assert "not in the allowed list" in result["reason"]

    def test_validate_command_security_dangerous_pattern_npm(self):
        """Test detection of dangerous npm pattern."""
        service = FileSystemService()

        result = service.validate_command_security("npm install package")

        assert result["safe"] is False
        # npm is not in allowed list, so it fails at command check
        assert "not in the allowed list" in result["reason"]

