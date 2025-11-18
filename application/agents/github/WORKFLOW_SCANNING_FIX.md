# Intelligent Workflow and Entity Scanning Fix

## Problem

The repository analysis endpoint (`/api/v1/repository/analyze`) was not returning workflows when they existed in the repository. This was because the `_scan_versioned_resources` function expected JSON files to be named exactly the same as their parent directory (e.g., `customerworkflow/version_1/customerworkflow.json`), but many repositories use different naming conventions (e.g., `customerworkflow/version_1/CustomerWorkflow.json` with PascalCase).

### Example Issue

Repository structure:
```
application/resources/workflow/
└── customerworkflow/
    └── version_1/
        └── CustomerWorkflow.json  ❌ Not found (expected customerworkflow.json)
```

The scanner would fail to find `CustomerWorkflow.json` because it only looked for an exact match: `customerworkflow.json`.

## Solution

Enhanced the `_scan_versioned_resources` function to intelligently find JSON files using a three-tier approach:

### 1. Exact Match (Highest Priority)
First, try to find a file with the exact same name as the directory:
```python
exact_match = version_dir / f"{resource_name}.json"
if exact_match.exists():
    resource_file = exact_match
```

### 2. Case-Insensitive Match (Medium Priority)
If no exact match, search for any JSON file that matches case-insensitively:
```python
for json_file in json_files:
    if json_file.stem.lower() == resource_name.lower():
        resource_file = json_file
        break
```

This allows:
- `customerworkflow/version_1/CustomerWorkflow.json` ✅
- `orderprocessing/version_1/OrderProcessing.json` ✅
- `payment/version_1/Payment.json` ✅

### 3. Single File Fallback (Lowest Priority)
If only one JSON file exists in the directory, use it regardless of name:
```python
if not resource_file and len(json_files) == 1:
    resource_file = json_files[0]
```

This allows:
- `payment/version_1/PaymentWorkflow.json` ✅
- `order/version_1/OrderProcessingWorkflow.json` ✅

## Benefits

1. **Flexible Naming Conventions**: Supports multiple naming patterns used across different repositories
2. **Backward Compatible**: Exact matches still work as before
3. **Robust**: Handles edge cases like single JSON files with different names
4. **Consistent**: Same logic applied to both versioned and non-versioned resources
5. **Well-Tested**: Comprehensive test suite with 11 test cases covering all scenarios

## Supported Naming Patterns

The scanner now supports all of these patterns:

| Directory Structure | JSON File Name | Status |
|---------------------|----------------|--------|
| `customerworkflow/version_1/` | `customerworkflow.json` | ✅ Exact match |
| `customerworkflow/version_1/` | `CustomerWorkflow.json` | ✅ Case-insensitive |
| `customerworkflow/version_1/` | `Customerworkflow.json` | ✅ Case-insensitive |
| `payment/version_1/` | `PaymentWorkflow.json` | ✅ Single file fallback |
| `order/version_1/` | `OrderProcessing.json` | ✅ Single file fallback |

## Testing

Run the comprehensive test suite:

```bash
python3 -m pytest application/agents/github/tests/test_workflow_scanning.py -v
```

Test cases include:
- Exact case match
- Case-insensitive match
- Single file fallback
- Multiple versions
- Mixed naming conventions
- Direct JSON files (no versioning)
- Directory without version structure
- Empty directories
- Invalid JSON files
- Entity scanning (same logic)

## API Impact

The `/api/v1/repository/analyze` endpoint now correctly returns workflows regardless of naming convention:

### Before (Missing Workflows)
```json
{
  "repositoryName": "mcp-cyoda-quart-app",
  "branch": "main",
  "appType": "python",
  "entities": [...],
  "workflows": [],  ❌ Empty even though workflows exist
  "requirements": [...]
}
```

### After (Workflows Found)
```json
{
  "repositoryName": "mcp-cyoda-quart-app",
  "branch": "main",
  "appType": "python",
  "entities": [...],
  "workflows": [
    {
      "name": "customerworkflow",
      "version": "version_1",
      "path": "application/resources/workflow/customerworkflow/version_1/CustomerWorkflow.json",
      "content": {...}
    }
  ],  ✅ Workflows correctly detected
  "requirements": [...]
}
```

## Implementation Details

### Files Modified
- `application/agents/github/tools.py`: Enhanced `_scan_versioned_resources` function
  - Lines 158-203: Versioned resource scanning with intelligent file finding
  - Lines 205-246: Non-versioned resource scanning with intelligent file finding
  - Lines 95-117: Updated docstring with detailed explanation

### Files Added
- `application/agents/github/tests/test_workflow_scanning.py`: Comprehensive test suite
- `application/agents/github/WORKFLOW_SCANNING_FIX.md`: This documentation

## Future Improvements

Potential enhancements for even more robust scanning:

1. **Multiple JSON Files**: Handle directories with multiple JSON files by using metadata or configuration
2. **Nested Structures**: Support deeper nesting patterns if needed
3. **Custom Naming Rules**: Allow configuration of custom naming patterns via environment variables
4. **Performance**: Cache scanning results for frequently accessed repositories

## Related Issues

This fix addresses the issue where the GitHub agent was not intelligently finding workflows in repositories with different naming conventions, as reported in the user's curl request to `/api/v1/repository/analyze`.

