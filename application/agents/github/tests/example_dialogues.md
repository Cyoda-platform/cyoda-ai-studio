# GitHub Agent - Example Dialogues

## Overview
The GitHub Agent handles repository operations, code generation, file management, and integration with GitHub for Cyoda applications.

## Available Tools
- `analyze_repository_structure` - Analyze repository structure and contents
- `analyze_repository_structure_agentic` - AI-powered repository analysis
- `commit_and_push_changes` - Commit and push changes to GitHub
- `execute_unix_command` - Execute shell commands in repository
- `generate_application` - Generate complete Cyoda application
- `generate_code_with_cli` - Generate code using Augment CLI
- `get_entity_path` - Get path to entity definitions
- `get_workflow_path` - Get path to workflow definitions
- `get_requirements_path` - Get path to requirements file
- `get_repository_diff` - Get git diff of changes
- `pull_repository_changes` - Pull latest changes from GitHub
- `save_file_to_repository` - Save files to repository
- Repository configuration tools (clone, configure, branch management)

---

## Example Dialogue 1: Analyzing Repository Structure

**User:** Analyze my repository structure

**Agent:** I'll analyze your repository structure for you.

*[Calls: analyze_repository_structure()]*

**Agent:** 📊 **Repository Structure Analysis**

**Repository**: cyoda-customer-app
**Branch**: main
**Last Commit**: 2024-01-15 10:30:00

**Directory Structure:**
```
cyoda-customer-app/
├── application/
│   ├── entity/
│   │   ├── customer/ (2 versions)
│   │   └── order/ (1 version)
│   ├── workflow/
│   │   ├── customer/ (2 versions)
│   │   └── order/ (1 version)
│   ├── routes/
│   │   ├── customer_routes.py
│   │   └── order_routes.py
│   ├── processors/
│   │   └── customer_processor.py
│   └── criteria/
│       └── customer_criteria.py
├── common/
│   └── utils/
│       └── date_utils.py
├── tests/
│   ├── unit/
│   └── integration/
├── requirements.txt
└── README.md
```

**Summary:**
- **Entities**: 2 (customer, order)
- **Workflows**: 2 (customer, order)
- **Routes**: 2 files
- **Processors**: 1 file
- **Tests**: 2 directories

**Recommendations:**
1. Add processors for the order entity
2. Create criteria for order searching
3. Add more comprehensive tests

---

## Example Dialogue 2: Checking Repository Diff

**User:** Show me what changes I've made

**Agent:** I'll get the git diff for you.

*[Calls: get_repository_diff()]*

**Agent:** 📝 **Repository Changes**

**Modified Files (3):**

**1. application/entity/customer/version_2/customer.json**
```diff
+ {
+   "name": "phone",
+   "type": "string",
+   "required": false,
+   "description": "Customer phone number"
+ }
```

**2. application/processors/customer_processor.py**
```diff
+ def validate_phone(self, phone: str) -> bool:
+     """Validate phone number format."""
+     return len(phone) >= 10
```

**3. tests/unit/test_customer_processor.py**
```diff
+ def test_validate_phone(self):
+     """Test phone validation."""
+     assert self.processor.validate_phone("1234567890") is True
+     assert self.processor.validate_phone("123") is False
```

**Summary:**
- 3 files modified
- Added phone field to customer entity
- Added phone validation logic
- Added test for phone validation

Ready to commit these changes?

---

## Example Dialogue 3: Committing and Pushing Changes

**User:** Commit my changes with message "Add phone field to customer entity"

**Agent:** I'll commit and push your changes.

*[Calls: commit_and_push_changes(commit_message="Add phone field to customer entity")]*

**Agent:** ✅ **Changes Committed and Pushed!**

**Commit Details:**
- **Commit Hash**: `a1b2c3d4`
- **Message**: "Add phone field to customer entity"
- **Author**: developer@company.com
- **Timestamp**: 2024-01-15 11:00:00
- **Branch**: main

**Files Committed:**
- application/entity/customer/version_2/customer.json
- application/processors/customer_processor.py
- tests/unit/test_customer_processor.py

**Push Status:**
- ✅ Pushed to origin/main
- ✅ All checks passed

Your changes are now in the repository!

**GitHub Link:**
https://github.com/your-org/cyoda-customer-app/commit/a1b2c3d4

---

## Example Dialogue 4: Generating Code with CLI

**User:** Generate a processor for validating customer email addresses

**Agent:** I'll generate the email validation processor using the Augment CLI.

*[Calls: generate_code_with_cli(prompt="Create a processor for validating customer email addresses with proper format checking")]*

**Agent:** 🤖 **Code Generation Started**

**Generating:** Email validation processor
**Using Model:** sonnet4
**Estimated Time:** 2-3 minutes

*[Generation in progress...]*

**Agent:** ✅ **Code Generation Complete!**

**Generated Files:**

**1. application/processors/customer/email_validator.py**
```python
"""Customer email validation processor."""

import re
from typing import Tuple


class EmailValidator:
    """Validates customer email addresses."""
    
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    def validate_email(self, email: str) -> Tuple[bool, str]:
        """
        Validate email format.
        
        Args:
            email: Email address to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not email:
            return False, "Email is required"
        
        if not self.EMAIL_PATTERN.match(email):
            return False, "Invalid email format"
        
        if len(email) > 255:
            return False, "Email too long (max 255 characters)"
        
        return True, ""
```

**2. tests/unit/test_email_validator.py**
```python
"""Tests for email validator."""

import pytest
from application.processors.customer.email_validator import EmailValidator


class TestEmailValidator:
    @pytest.fixture
    def validator(self):
        return EmailValidator()
    
    def test_valid_email(self, validator):
        is_valid, error = validator.validate_email("user@example.com")
        assert is_valid is True
        assert error == ""
    
    def test_invalid_email_no_at(self, validator):
        is_valid, error = validator.validate_email("userexample.com")
        assert is_valid is False
        assert "Invalid email format" in error
    
    def test_empty_email(self, validator):
        is_valid, error = validator.validate_email("")
        assert is_valid is False
        assert "required" in error
```

**Summary:**
- ✅ Processor created with email validation logic
- ✅ Comprehensive tests included
- ✅ Follows Pythonic best practices
- ✅ Type hints and docstrings added

Would you like me to commit these generated files?

---

## Example Dialogue 5: Saving Files to Repository

**User:** Save this entity definition to the repository

```json
{
  "name": "product",
  "version": "version_1",
  "fields": [
    {"name": "product_id", "type": "string", "required": true},
    {"name": "name", "type": "string", "required": true},
    {"name": "price", "type": "number", "required": true}
  ]
}
```

**Agent:** I'll save this entity definition to the repository.

*[Calls: save_file_to_repository(
    file_path="application/entity/product/version_1/product.json",
    content=<entity_json>
)]*

**Agent:** ✅ **File Saved Successfully!**

**File Details:**
- **Path**: `application/entity/product/version_1/product.json`
- **Size**: 245 bytes
- **Status**: New file created

**Entity Summary:**
- **Name**: product
- **Version**: version_1
- **Fields**: 3 (product_id, name, price)
- **Required Fields**: All fields required

**Next Steps:**
1. Create a workflow for the product entity
2. Generate routes and processors
3. Add tests
4. Commit the changes

Would you like me to help with any of these next steps?

---

## Example Dialogue 6: Pulling Latest Changes

**User:** Pull the latest changes from GitHub

**Agent:** I'll pull the latest changes for you.

*[Calls: pull_repository_changes()]*

**Agent:** 🔄 **Pulling Latest Changes**

**Pull Status:**
- **Branch**: main
- **Remote**: origin

**Changes Retrieved:**
```
From github.com:your-org/cyoda-customer-app
   a1b2c3d..e5f6g7h  main -> origin/main
Updating a1b2c3d..e5f6g7h
Fast-forward
```

**Updated Files (4):**
- ✅ application/entity/invoice/version_1/invoice.json (new)
- ✅ application/workflow/invoice/version_1/invoiceworkflow.json (new)
- ✅ application/routes/invoice_routes.py (new)
- ✅ README.md (modified)

**Summary:**
- 3 new files added
- 1 file modified
- New invoice entity and workflow added by team member

Your local repository is now up to date!

---

## Example Dialogue 7: Getting Entity Path

**User:** Where are my entity definitions stored?

**Agent:** Let me get the entity path for you.

*[Calls: get_entity_path()]*

**Agent:** 📁 **Entity Definitions Location**

**Path**: `application/entity/`

**Current Entities:**
```
application/entity/
├── customer/
│   ├── version_1/
│   │   └── customer.json
│   └── version_2/
│       └── customer.json
├── order/
│   └── version_1/
│       └── order.json
├── product/
│   └── version_1/
│       └── product.json
└── invoice/
    └── version_1/
        └── invoice.json
```

**Entity Summary:**
- **Total Entities**: 4
- **Total Versions**: 5
- **Naming Convention**: `{entity_name}/version_{n}/{entity_name}.json`

To add a new entity, create:
```
application/entity/{entity_name}/version_1/{entity_name}.json
```

---

## Example Dialogue 8: Executing Unix Commands

**User:** Run the tests in my repository

**Agent:** I'll execute the test command for you.

*[Calls: execute_unix_command(command="pytest tests/ -v")]*

**Agent:** 🧪 **Running Tests**

**Command**: `pytest tests/ -v`

**Output:**
```
============================= test session starts ==============================
platform linux -- Python 3.12.0, pytest-7.4.0
collected 45 items

tests/unit/test_customer_processor.py::test_validate_email PASSED      [  2%]
tests/unit/test_customer_processor.py::test_validate_phone PASSED      [  4%]
tests/unit/test_customer_processor.py::test_validate_age PASSED        [  6%]
tests/unit/test_email_validator.py::test_valid_email PASSED            [  8%]
tests/unit/test_email_validator.py::test_invalid_email PASSED          [ 11%]
...
tests/integration/test_customer_api.py::test_create_customer PASSED    [ 97%]
tests/integration/test_customer_api.py::test_get_customer PASSED       [100%]

============================== 45 passed in 3.42s ===============================
```

**Test Results:**
- ✅ **All tests passed!** (45/45)
- **Duration**: 3.42 seconds
- **Coverage**: Unit and integration tests

Your code is ready for deployment!

---

## Example Dialogue 9: Generating Complete Application

**User:** Generate a complete application for managing products with CRUD operations

**Agent:** I'll generate a complete Cyoda application for product management.

*[Calls: generate_application(
    entity_name="product",
    description="Product management with CRUD operations including create, read, update, delete, and search"
)]*

**Agent:** 🚀 **Generating Complete Application**

**Entity**: product
**Features**: Full CRUD operations
**Estimated Time**: 5-7 minutes

*[Generation in progress...]*

**Agent:** ✅ **Application Generation Complete!**

**Generated Components:**

**1. Entity Definition**
- `application/entity/product/version_1/product.json`

**2. Workflow**
- `application/workflow/product/version_1/productworkflow.json`
- States: DRAFT, ACTIVE, DISCONTINUED

**3. Routes** (12 endpoints)
- `application/routes/product_routes.py`
  - POST /products (create)
  - GET /products/{id} (read)
  - PUT /products/{id} (update)
  - DELETE /products/{id} (delete)
  - GET /products (list/search)
  - POST /products/{id}/activate (workflow)
  - POST /products/{id}/discontinue (workflow)

**4. Processors**
- `application/processors/product/validation_processor.py`
- `application/processors/product/enrichment_processor.py`

**5. Criteria**
- `application/criteria/product_criteria.py`

**6. Tests** (28 tests)
- `tests/unit/test_product_processor.py`
- `tests/unit/test_product_criteria.py`
- `tests/integration/test_product_api.py`

**Summary:**
- 📦 6 component types generated
- 📝 12 API endpoints
- 🧪 28 tests included
- ✅ All tests passing

**Next Steps:**
1. Review generated code
2. Customize business logic if needed
3. Commit changes
4. Deploy to environment

Would you like me to commit these changes?

---

## Example Dialogue 10: Complete Workflow - New Feature

**User:** I need to add a discount feature to customer orders

**Agent:** I'll help you add a discount feature. Let me start by analyzing the current repository structure.

*[Calls: analyze_repository_structure()]*

**Agent:** I can see you have customer and order entities. I'll generate the discount functionality.

*[Calls: generate_code_with_cli(
    prompt="Add discount calculation feature to orders. Include discount percentage field, validation, and calculation logic in processor"
)]*

**Agent:** ✅ **Discount Feature Generated!**

**Changes Made:**

**1. Updated Order Entity**
- Added `discount_percentage` field (0-100)
- Added `discount_amount` field (calculated)
- Added `final_total` field (after discount)

**2. Created Discount Processor**
- Validates discount percentage (0-100)
- Calculates discount amount
- Computes final total
- Handles edge cases

**3. Updated Tests**
- Test discount validation
- Test discount calculation
- Test edge cases (0%, 100%, invalid values)

Let me show you the diff:

*[Calls: get_repository_diff()]*

**Agent:** Here are the changes. Would you like me to commit them?

**User:** Yes, commit with message "Add discount feature to orders"

*[Calls: commit_and_push_changes(commit_message="Add discount feature to orders")]*

**Agent:** ✅ **Changes committed and pushed!**

Your discount feature is now in the repository and ready for deployment!

---

## Tips for Interacting with GitHub Agent

1. **Repository Analysis**: Ask to analyze structure and contents
2. **Code Generation**: Request generation of entities, processors, routes, etc.
3. **File Management**: Save, read, and modify files in the repository
4. **Git Operations**: Commit, push, pull, and view diffs
5. **Command Execution**: Run tests, builds, and other commands
6. **Complete Features**: Request end-to-end feature generation
7. **Branch Management**: Configure and manage repository branches

