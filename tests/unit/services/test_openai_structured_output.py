"""
Unit tests for OpenAI Structured Output Handler
"""

import pytest
from pydantic import BaseModel, ValidationError

from application.services.openai.structured_output import StructuredOutputHandler


class TestPerson(BaseModel):
    """Test schema."""

    name: str
    age: int
    email: str


class TestAddress(BaseModel):
    """Test schema for merging."""

    street: str
    city: str
    zip_code: str


class TestValidateSchema:
    """Test schema validation."""

    def test_validate_schema_success(self):
        """Test successful schema validation."""
        data = {"name": "John", "age": 30, "email": "john@example.com"}
        result = StructuredOutputHandler.validate_schema(TestPerson, data)
        assert result.name == "John"
        assert result.age == 30
        assert result.email == "john@example.com"

    def test_validate_schema_missing_field(self):
        """Test validation with missing required field."""
        data = {"name": "John", "age": 30}
        with pytest.raises(ValidationError):
            StructuredOutputHandler.validate_schema(TestPerson, data)

    def test_validate_schema_wrong_type(self):
        """Test validation with wrong field type."""
        data = {"name": "John", "age": "thirty", "email": "john@example.com"}
        with pytest.raises(ValidationError):
            StructuredOutputHandler.validate_schema(TestPerson, data)

    def test_validate_schema_extra_fields(self):
        """Test validation with extra fields."""
        data = {
            "name": "John",
            "age": 30,
            "email": "john@example.com",
            "phone": "123-456-7890",
        }
        result = StructuredOutputHandler.validate_schema(TestPerson, data)
        assert result.name == "John"


class TestSchemaToJsonSchema:
    """Test schema to JSON schema conversion."""

    def test_schema_to_json_schema(self):
        """Test converting schema to JSON schema."""
        json_schema = StructuredOutputHandler.schema_to_json_schema(TestPerson)
        assert "properties" in json_schema
        assert "name" in json_schema["properties"]
        assert "age" in json_schema["properties"]
        assert "email" in json_schema["properties"]

    def test_schema_to_json_schema_required_fields(self):
        """Test JSON schema includes required fields."""
        json_schema = StructuredOutputHandler.schema_to_json_schema(TestPerson)
        assert "required" in json_schema
        assert "name" in json_schema["required"]
        assert "age" in json_schema["required"]
        assert "email" in json_schema["required"]

    def test_schema_to_json_schema_field_types(self):
        """Test JSON schema includes field types."""
        json_schema = StructuredOutputHandler.schema_to_json_schema(TestPerson)
        props = json_schema["properties"]
        assert props["name"]["type"] == "string"
        assert props["age"]["type"] == "integer"
        assert props["email"]["type"] == "string"


class TestSchemaToDict:
    """Test schema instance to dictionary conversion."""

    def test_schema_to_dict(self):
        """Test converting schema instance to dict."""
        person = TestPerson(name="John", age=30, email="john@example.com")
        result = StructuredOutputHandler.schema_to_dict(person)
        assert result["name"] == "John"
        assert result["age"] == 30
        assert result["email"] == "john@example.com"

    def test_schema_to_dict_preserves_types(self):
        """Test dict conversion preserves types."""
        person = TestPerson(name="John", age=30, email="john@example.com")
        result = StructuredOutputHandler.schema_to_dict(person)
        assert isinstance(result["name"], str)
        assert isinstance(result["age"], int)
        assert isinstance(result["email"], str)


class TestSchemaToJson:
    """Test schema instance to JSON conversion."""

    def test_schema_to_json(self):
        """Test converting schema instance to JSON."""
        person = TestPerson(name="John", age=30, email="john@example.com")
        result = StructuredOutputHandler.schema_to_json(person)
        assert isinstance(result, str)
        assert "John" in result
        assert "30" in result
        assert "john@example.com" in result

    def test_schema_to_json_valid_json(self):
        """Test JSON output is valid."""
        import json

        person = TestPerson(name="John", age=30, email="john@example.com")
        result = StructuredOutputHandler.schema_to_json(person)
        parsed = json.loads(result)
        assert parsed["name"] == "John"
        assert parsed["age"] == 30


class TestGetSchemaFields:
    """Test schema field extraction."""

    def test_get_schema_fields(self):
        """Test extracting fields from schema."""
        fields = StructuredOutputHandler.get_schema_fields(TestPerson)
        assert "name" in fields
        assert "age" in fields
        assert "email" in fields

    def test_get_schema_fields_info(self):
        """Test field information is correct."""
        fields = StructuredOutputHandler.get_schema_fields(TestPerson)
        assert "type" in fields["name"]
        assert "required" in fields["name"]
        assert "description" in fields["name"]

    def test_get_schema_fields_required(self):
        """Test required field detection."""
        fields = StructuredOutputHandler.get_schema_fields(TestPerson)
        assert fields["name"]["required"] is True
        assert fields["age"]["required"] is True
        assert fields["email"]["required"] is True


class TestMergeSchemas:
    """Test schema merging."""

    def test_merge_schemas(self):
        """Test merging two schemas."""
        merged = StructuredOutputHandler.merge_schemas(TestPerson, TestAddress)
        assert "properties" in merged
        assert "name" in merged["properties"]
        assert "street" in merged["properties"]

    def test_merge_schemas_required_fields(self):
        """Test merged schema includes all required fields."""
        merged = StructuredOutputHandler.merge_schemas(TestPerson, TestAddress)
        assert "required" in merged
        assert "name" in merged["required"]
        assert "street" in merged["required"]

    def test_merge_schemas_no_duplicates(self):
        """Test merged schema has no duplicate required fields."""
        merged = StructuredOutputHandler.merge_schemas(TestPerson, TestAddress)
        required = merged["required"]
        assert len(required) == len(set(required))

    def test_merge_schemas_all_properties(self):
        """Test merged schema includes all properties."""
        merged = StructuredOutputHandler.merge_schemas(TestPerson, TestAddress)
        props = merged["properties"]
        assert len(props) == 6  # 3 from TestPerson + 3 from TestAddress
