# Guidelines Agent - Example Dialogues

## Overview
The Guidelines Agent is a Cyoda development expert that provides guidelines, best practices, and design patterns for Pythonic Cyoda development.

## Available Tools
- `get_design_principle` - Retrieve specific Cyoda design principles
- `get_testing_guideline` - Get testing best practices and guidelines
- `load_web_page` - Load and analyze web documentation

---

## Example Dialogue 1: No Reflection Principle

**User:** Tell me about the no reflection principle

**Agent:** Let me get the details about this important design principle.

*[Calls: get_design_principle(principle_name="no reflection")]*

**Agent:** The **No Reflection Principle** is a core guideline for Cyoda development:

**Principle:**
Cyoda applications should avoid using Python reflection or dynamic code generation.

**Why This Matters:**
- **Maintainability**: Explicit code is easier to understand and maintain
- **Performance**: Reflection adds runtime overhead
- **Type Safety**: Static code enables better IDE support and type checking
- **Debugging**: Explicit code is easier to debug and trace

**What to Avoid:**
```python
# ❌ Don't do this
getattr(obj, dynamic_method_name)()
eval(code_string)
exec(code_string)
```

**What to Do Instead:**
```python
# ✅ Do this
if method_name == "process":
    obj.process()
elif method_name == "validate":
    obj.validate()
```

**Best Practice:** Use explicit conditional logic, factory patterns, or strategy patterns instead of reflection.

---

## Example Dialogue 2: Common Module Usage

**User:** How should I use the common module?

**Agent:** Let me explain the common module design principle.

*[Calls: get_design_principle(principle_name="use common module")]*

**Agent:** The **Common Module** is designed for shared utilities and base classes:

**Purpose:**
- Store reusable code used across multiple entities
- Provide base classes and utilities
- Avoid code duplication

**What Belongs in Common:**
- Base classes (e.g., `BaseProcessor`, `BaseValidator`)
- Utility functions (e.g., date formatting, string manipulation)
- Shared constants and enums
- Common data structures

**What Doesn't Belong:**
- Entity-specific business logic
- Application-specific processors
- Route handlers

**Dependency Rule:**
⚠️ **Critical**: The common module should NOT depend on application-specific modules. Dependencies should flow one way: application → common, never common → application.

**Example Structure:**
```
common/
├── utils/
│   ├── date_utils.py
│   └── string_utils.py
├── base/
│   ├── base_processor.py
│   └── base_validator.py
└── constants.py
```

---

## Example Dialogue 3: Thin Routes Pattern

**User:** What does thin routes mean?

**Agent:** Let me explain the thin routes principle.

*[Calls: get_design_principle(principle_name="thin routes")]*

**Agent:** **Thin Routes** means route handlers should be minimal proxies to EntityService without business logic.

**The Pattern:**
Route handlers should only:
1. Extract parameters from the request
2. Call EntityService methods
3. Return the response

**❌ Bad Example (Fat Route):**
```python
@router.post("/customers")
async def create_customer(customer_data: dict):
    # Don't put business logic here!
    if customer_data.get("age", 0) < 18:
        raise ValueError("Customer must be 18+")
    
    # Don't do validation here!
    if not customer_data.get("email"):
        raise ValueError("Email required")
    
    # Don't do data transformation here!
    customer_data["created_at"] = datetime.now()
    
    return entity_service.create(customer_data)
```

**✅ Good Example (Thin Route):**
```python
@router.post("/customers")
async def create_customer(customer_data: dict):
    # Just delegate to EntityService
    return entity_service.create(customer_data)
```

**Where Business Logic Goes:**
- **Processors**: Business rules and validation
- **Criteria**: Search and filter logic
- **EntityService**: Lifecycle and persistence

**Benefits:**
- Easier to test (test processors, not routes)
- Reusable business logic
- Cleaner separation of concerns

---

## Example Dialogue 4: Testing Guidelines

**User:** What are the best practices for testing Cyoda applications?

**Agent:** Let me get the testing guidelines for you.

*[Calls: get_testing_guideline(guideline_name="unit testing")]*

**Agent:** Here are the **Testing Best Practices** for Cyoda applications:

**1. Test Structure:**
```python
class TestCustomerProcessor:
    @pytest.fixture
    def setup_method(self):
        """Setup for each test method."""
        self.processor = CustomerProcessor()
        
    @pytest.mark.asyncio
    async def test_validate_customer_age(self):
        """Test customer age validation."""
        # Arrange
        customer_data = {"name": "John", "age": 17}
        
        # Act
        result = await self.processor.validate(customer_data)
        
        # Assert
        assert result.is_valid is False
        assert "age" in result.errors
```

**2. Test Coverage:**
- ✅ Test all processors and business logic
- ✅ Test both success and failure scenarios
- ✅ Test edge cases and boundary conditions
- ✅ Test workflow transitions
- ✅ Mock external dependencies

**3. Naming Conventions:**
- Test files: `test_*.py`
- Test classes: `TestClassName`
- Test methods: `test_specific_behavior`

**4. Mocking:**
```python
@pytest.mark.asyncio
async def test_create_customer_with_mock():
    """Test customer creation with mocked EntityService."""
    # Arrange
    mock_service = AsyncMock()
    mock_service.create.return_value = {"id": "123"}
    
    # Act
    result = await create_customer(mock_service, customer_data)
    
    # Assert
    mock_service.create.assert_called_once()
```

**5. Test Organization:**
```
tests/
├── unit/
│   ├── test_processors.py
│   ├── test_criteria.py
│   └── test_validators.py
├── integration/
│   └── test_entity_service.py
└── fixtures/
    └── sample_data.py
```

---

## Example Dialogue 5: Pythonic Code Style

**User:** What makes code "Pythonic" in Cyoda development?

**Agent:** Let me explain Pythonic coding principles for Cyoda.

*[Calls: get_design_principle(principle_name="pythonic code")]*

**Agent:** **Pythonic Code** in Cyoda follows these principles:

**1. Explicit is Better Than Implicit:**
```python
# ✅ Good
def process_customer(customer_id: str, validate: bool = True):
    pass

# ❌ Bad
def process_customer(customer_id, **kwargs):
    pass
```

**2. Use Type Hints:**
```python
# ✅ Good
def get_customer(customer_id: str) -> dict:
    return entity_service.find_by_id(customer_id)

# ❌ Bad
def get_customer(customer_id):
    return entity_service.find_by_id(customer_id)
```

**3. Descriptive Names:**
```python
# ✅ Good
customer_repository = CustomerRepository()
validated_customers = filter_validated(customers)

# ❌ Bad
repo = CustomerRepository()
data = filter(customers)
```

**4. Early Returns:**
```python
# ✅ Good
def validate_customer(customer: dict) -> bool:
    if not customer.get("email"):
        return False
    if customer.get("age", 0) < 18:
        return False
    return True

# ❌ Bad (nested conditions)
def validate_customer(customer: dict) -> bool:
    if customer.get("email"):
        if customer.get("age", 0) >= 18:
            return True
    return False
```

**5. List Comprehensions:**
```python
# ✅ Good
active_customers = [c for c in customers if c["status"] == "active"]

# ❌ Bad
active_customers = []
for c in customers:
    if c["status"] == "active":
        active_customers.append(c)
```

---

## Example Dialogue 6: Error Handling Best Practices

**User:** How should I handle errors in my Cyoda application?

**Agent:** Let me get the error handling guidelines.

*[Calls: get_design_principle(principle_name="error handling")]*

**Agent:** **Error Handling Best Practices** for Cyoda applications:

**1. Use Specific Exceptions:**
```python
# ✅ Good
try:
    customer = entity_service.find_by_id(customer_id)
except EntityNotFoundException:
    raise HTTPException(status_code=404, detail="Customer not found")
except ValidationException as e:
    raise HTTPException(status_code=400, detail=str(e))

# ❌ Bad
try:
    customer = entity_service.find_by_id(customer_id)
except Exception as e:
    raise HTTPException(status_code=500, detail="Error")
```

**2. Meaningful Error Messages:**
```python
# ✅ Good
if age < 18:
    raise ValidationException(
        f"Customer age {age} is below minimum required age of 18"
    )

# ❌ Bad
if age < 18:
    raise ValidationException("Invalid age")
```

**3. Log Errors Appropriately:**
```python
# ✅ Good
try:
    result = process_customer(customer_data)
except Exception as e:
    logger.error(f"Failed to process customer {customer_id}: {e}", exc_info=True)
    raise

# ❌ Bad
try:
    result = process_customer(customer_data)
except:
    pass  # Silent failure
```

**4. Don't Catch What You Can't Handle:**
```python
# ✅ Good
def get_customer(customer_id: str) -> dict:
    # Let exceptions propagate if we can't handle them
    return entity_service.find_by_id(customer_id)

# ❌ Bad
def get_customer(customer_id: str) -> dict:
    try:
        return entity_service.find_by_id(customer_id)
    except Exception:
        return {}  # Hiding errors
```

---

## Example Dialogue 7: Code Organization

**User:** How should I organize my processor code?

**Agent:** Let me explain the code organization principles.

*[Calls: get_design_principle(principle_name="code organization")]*

**Agent:** **Processor Organization Best Practices:**

**1. Single Responsibility:**
Each processor should handle one entity or one aspect of business logic.

```python
# ✅ Good - Focused processor
class CustomerValidationProcessor:
    def validate_age(self, customer: dict) -> bool:
        return customer.get("age", 0) >= 18
    
    def validate_email(self, customer: dict) -> bool:
        email = customer.get("email", "")
        return "@" in email and "." in email

# ❌ Bad - Too many responsibilities
class MegaProcessor:
    def validate_customer(self, customer: dict):
        pass
    def process_order(self, order: dict):
        pass
    def send_email(self, email: str):
        pass
```

**2. Function Length:**
Keep functions under 25-30 lines (excluding docstrings).

```python
# ✅ Good - Short, focused function
def calculate_discount(customer: dict, order_total: float) -> float:
    if customer.get("vip_status"):
        return order_total * 0.1
    return 0.0

# If a function is too long, extract helper methods
```

**3. Module Structure:**
```
application/processors/customer/
├── __init__.py
├── validation_processor.py
├── enrichment_processor.py
└── notification_processor.py
```

**4. Avoid Deep Nesting:**
```python
# ✅ Good - Flat structure with early returns
def process_customer(customer: dict) -> dict:
    if not customer.get("email"):
        raise ValidationException("Email required")
    
    if customer.get("age", 0) < 18:
        raise ValidationException("Must be 18+")
    
    return enrich_customer_data(customer)

# ❌ Bad - Deep nesting
def process_customer(customer: dict) -> dict:
    if customer.get("email"):
        if customer.get("age", 0) >= 18:
            return enrich_customer_data(customer)
        else:
            raise ValidationException("Must be 18+")
    else:
        raise ValidationException("Email required")
```

---

## Example Dialogue 8: Multi-turn Conversation

**User:** I'm writing a new processor. What should I keep in mind?

**Agent:** Great! Let me share the key principles for writing processors.

*[Calls: get_design_principle(principle_name="processor design")]*

**Agent:** Here are the **Key Principles for Processor Design**:

1. **Single Responsibility** - One processor, one purpose
2. **Type Hints** - Always use type annotations
3. **Descriptive Names** - Clear function and variable names
4. **Error Handling** - Explicit exception handling
5. **Testability** - Easy to unit test

**User:** Should I put validation logic in the processor?

**Agent:** Yes! Processors are the perfect place for validation logic. Here's how:

```python
class CustomerProcessor:
    def validate(self, customer_data: dict) -> ValidationResult:
        """Validate customer data before creation."""
        errors = []
        
        if not customer_data.get("email"):
            errors.append("Email is required")
        
        if customer_data.get("age", 0) < 18:
            errors.append("Customer must be 18 or older")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors
        )
```

Keep validation separate from business logic processing for better testability.

**User:** What about database access?

**Agent:** Good question! **Never access the database directly from processors.** Instead:

- Use **EntityService** for entity operations
- Processors should receive data and return processed data
- Let EntityService handle persistence

This keeps your processors testable and follows the separation of concerns principle.

---

## Tips for Interacting with Guidelines Agent

1. **Ask About Principles**: Request specific design principles or patterns
2. **Code Review**: Ask for feedback on code structure and organization
3. **Best Practices**: Inquire about testing, error handling, or code style
4. **Examples**: Request code examples for specific patterns
5. **Comparisons**: Ask about good vs. bad practices

