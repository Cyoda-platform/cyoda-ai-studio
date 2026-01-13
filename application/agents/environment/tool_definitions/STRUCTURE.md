# Environment Agent Tools - Folder Structure

This document describes the organization of the Environment Agent tools after the enhanced reorganization that separates public tools from internal helpers and organizes common utilities by type.

## Directory Structure

```
tool_definitions/
├── common/                         # Shared utilities (organized by type)
│   ├── models/                     # Data Transfer Objects (DTOs)
│   │   ├── dtos.py                 # Pydantic models for requests/configs
│   │   └── __init__.py
│   ├── formatters/                 # Response formatters
│   │   ├── formatters.py           # Message and response formatting
│   │   └── __init__.py
│   ├── utils/                      # Utility functions
│   │   ├── utils.py                # Decorators, validators, helpers
│   │   └── __init__.py
│   └── __init__.py                 # Re-exports all common utilities
│
├── deployment/                     # Deployment tools and helpers (organized by visibility)
│   ├── tools/                      # Public deployment tools
│   │   ├── deploy_cyoda_environment_tool.py
│   │   ├── deploy_user_application_tool.py
│   │   ├── get_build_logs_tool.py
│   │   ├── get_deployment_status_tool.py
│   │   └── __init__.py
│   ├── helpers/                    # Internal deployment helpers
│   │   ├── _conversation_helpers.py    # Conversation state management
│   │   ├── _deployment_helpers.py      # Core deployment logic
│   │   ├── _deployment_monitor.py      # Progress monitoring
│   │   ├── _hooks.py                   # UI hook generation
│   │   ├── _tasks.py                   # Background task management
│   │   └── __init__.py
│   └── __init__.py                 # Re-exports public tools
│
├── environment/                    # Environment management tools
│   ├── check_exists_tool.py
│   ├── delete_tool.py
│   ├── describe_tool.py
│   ├── get_metrics_tool.py
│   ├── get_pods_tool.py
│   ├── list_tool.py
│   └── __init__.py
│
├── application/                    # Cyoda application tools
│   ├── get_details_tool.py
│   ├── get_status_tool.py
│   ├── restart_tool.py
│   ├── scale_tool.py
│   ├── update_image_tool.py
│   └── __init__.py
│
├── user_apps/                      # User application tools
│   ├── delete_tool.py
│   ├── get_details_tool.py
│   ├── get_metrics_tool.py
│   ├── get_pods_tool.py
│   ├── get_status_tool.py
│   ├── list_tool.py
│   ├── restart_tool.py
│   ├── scale_tool.py
│   ├── update_image_tool.py
│   └── __init__.py
│
├── other/                          # Miscellaneous tools
│   ├── issue_technical_user_tool.py
│   ├── search_logs_tool.py
│   ├── show_deployment_options_tool.py
│   └── __init__.py
│
└── __init__.py                     # Root tool definitions module
```

## Organization Principles

### 1. Common Module - Organized by Type

The `common/` module is organized into subdirectories based on the type of utility:

- **models/** - Data structures (DTOs, Pydantic models)
- **formatters/** - Response and message formatting
- **utils/** - Utility functions, decorators, validators

This separation makes it easy to find related functionality and avoids mixing different types of utilities in a single file.

### 2. Deployment Module - Organized by Visibility

The `deployment/` module separates public tools from internal helpers:

- **tools/** - Public deployment tools that are exposed to the agent
- **helpers/** - Internal helper modules (prefixed with `_`) used by the tools

This separation:
- Clearly distinguishes the public API from internal implementation
- Prevents accidental direct use of internal helpers
- Makes it easier to refactor internal helpers without affecting the public interface
- Improves code navigation and understanding

### 3. Other Modules - Flat Structure

The remaining modules (`environment/`, `application/`, `user_apps/`, `other/`) maintain a flat structure since they:
- Only contain public tools (no internal helpers)
- Have a manageable number of files (5-10 each)
- Are organized by domain, which is already clear

## Module Exports

### Common Module

The `common/__init__.py` re-exports all utilities from subdirectories:

```python
# Models (DTOs)
from .models.dtos import (
    DeployUserApplicationRequest,
    DeploymentConfig,
    SearchLogsRequest,
    DeployCyodaEnvironmentRequest,
)

# Formatters
from .formatters.formatters import (
    format_deployment_started_message,
    format_environment_deployment_message,
    format_validation_error,
    format_env_name_prompt_suggestion,
    format_app_name_prompt_suggestion,
)

# Utils
from .utils.utils import (
    DeploymentResult,
    require_authenticated_user,
    handle_tool_errors,
    construct_environment_url,
    validate_required_params,
    format_error_response,
    get_task_service,
    get_deployment_status_tool,
)
```

### Deployment Module

The `deployment/__init__.py` only exports public tools:

```python
# Public tools
from .tools import (
    deploy_cyoda_environment,
    deploy_user_application,
    get_deployment_status,
    get_build_logs,
)

# Internal helpers (for backward compatibility with tests)
from .helpers import (
    handle_deployment_success,
    monitor_deployment_progress,
)
```

## Import Examples

### Importing from Common Utilities

```python
# From within tool_definitions/ (same level)
from ..common.models.dtos import DeploymentConfig
from ..common.formatters.formatters import format_deployment_started_message
from ..common.utils.utils import require_authenticated_user

# From outside tool_definitions/ (e.g., tests)
from application.agents.environment.tool_definitions.common import (
    DeploymentConfig,
    format_deployment_started_message,
    require_authenticated_user,
)
```

### Importing Deployment Tools

```python
# Public tools - from within tool_definitions/
from ..deployment.tools.deploy_cyoda_environment_tool import deploy_cyoda_environment

# Public tools - from outside
from application.agents.environment.tool_definitions.deployment import deploy_cyoda_environment

# Internal helpers - from within deployment/tools/
from ..helpers._deployment_helpers import handle_deployment_success

# Internal helpers - from outside (discouraged, but possible for tests)
from application.agents.environment.tool_definitions.deployment.helpers._deployment_helpers import handle_deployment_success
```

### Importing Other Tools

```python
# From within tool_definitions/
from ..environment.list_tool import list_environments
from ..application.get_status_tool import get_application_status

# From outside
from application.agents.environment.tool_definitions.environment import list_environments
from application.agents.environment.tool_definitions.application import get_application_status
```

## Benefits of This Structure

### 1. Enhanced Navigation
- **Common utilities organized by type** - Easy to find DTOs, formatters, or utils
- **Public vs Internal separation** - Clear distinction in deployment module
- **Domain grouping** - Related tools grouped by function (environment, application, etc.)

### 2. Improved Maintainability
- **Smaller, focused modules** - Each file has a single, clear purpose
- **Clear boundaries** - Public tools in `tools/`, internal helpers in `helpers/`
- **Type-based organization** - DTOs in `models/`, formatters in `formatters/`, etc.

### 3. Better Discoverability
- **Logical grouping** - Related functionality grouped together
- **Consistent structure** - Predictable locations for different types of code
- **Clear naming** - `_` prefix for internal helpers

### 4. Encapsulation
- **Hidden implementation** - Internal helpers not exposed through main exports
- **Stable public API** - Tools in `tools/` folder are the public interface
- **Flexible refactoring** - Internal helpers can change without affecting external users

## File Count Summary

| Module       | Subdirectories | Files | Description                           |
|--------------|----------------|-------|---------------------------------------|
| common/      | 3              | 7     | Shared utilities (by type)            |
| deployment/  | 2              | 11    | Deployment tools & helpers (by visibility) |
| environment/ | 0              | 7     | Environment management                |
| application/ | 0              | 6     | Cyoda application tools               |
| user_apps/   | 0              | 10    | User application tools                |
| other/       | 0              | 4     | Miscellaneous tools                   |
| **TOTAL**    | **5**          | **45**| All environment agent tools           |

## Migration Notes

This structure evolved from the previous organization through two major reorganizations:

### First Reorganization (6 Domain Folders)
Created the initial domain-based organization:
- `common/`, `deployment/`, `environment/`, `application/`, `user_apps/`, `other/`

### Second Reorganization (Enhanced Structure)
Added subdirectories within `common/` and `deployment/`:
- **Common**: Split into `models/`, `formatters/`, `utils/`
- **Deployment**: Split into `tools/` (public) and `helpers/` (internal)

## Test Results

After reorganization:
- **124 tests passing** (same as before reorganization)
- **3 tests failing** (pre-existing failures, not related to reorganization)
- **10 tests skipped**

The reorganization maintained full backward compatibility while improving code organization.

## Additional Resources

- See `/application/agents/environment/tools.py` for the main tool registry
- See individual `__init__.py` files for module-specific exports
- See test files for usage examples: `/tests/unit/agents/environment/test_environment_tools.py`
