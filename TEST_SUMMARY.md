# Test Summary for `get_env_deploy_status` Function

## Overview
Comprehensive test suite for the `get_env_deploy_status` function in `application/agents/setup/tools.py`.

## Function Changes
The `get_env_deploy_status` function was updated to include authentication:

### Before
- Directly made GET request to deployment status endpoint
- No authentication mechanism

### After
- **Step 1**: Authenticates with `POST https://cloud-manager-cyoda.{CLIENT_HOST}/api/auth/login`
  - Uses `CYODA_CLIENT_ID` and `CYODA_CLIENT_SECRET` as username/password
- **Step 2**: Retrieves JWT token from auth response
- **Step 3**: Makes authenticated GET request with `Authorization: Bearer {token}` header

## Test Coverage

### 1. **Success Scenario** (`test_get_env_deploy_status_success`)
- Tests complete successful flow: authentication → token retrieval → status check
- Verifies correct endpoints are called with correct parameters
- Validates Authorization header is properly set

### 2. **Authentication Failures**

#### a. **401 on Login** (`test_get_env_deploy_status_auth_failure_401`)
- Tests when authentication fails (wrong credentials)
- Verifies proper error message is returned

#### b. **Missing Token** (`test_get_env_deploy_status_missing_token_in_response`)
- Tests when auth succeeds but no token is returned
- Validates error handling for malformed auth responses

#### c. **401 on Status Check** (`test_get_env_deploy_status_status_check_401`)
- Tests when token is expired/invalid during status check
- Simulates the exact error from the user's report

### 3. **Configuration Validation**

#### a. **Missing CLOUD_MANAGER_HOST** (`test_get_env_deploy_status_missing_cloud_manager_host`)
- Validates error when cloud manager host is not configured

#### b. **Missing CLIENT_HOST** (`test_get_env_deploy_status_missing_client_host`)
- Validates error when client host is not configured

#### c. **Missing Credentials** (`test_get_env_deploy_status_missing_credentials`)
- Tests when CYODA_CLIENT_ID or CYODA_CLIENT_SECRET is missing
- Ensures proper error message guides user to configure credentials

### 4. **Protocol Handling** (`test_get_env_deploy_status_localhost_uses_http`)
- Verifies localhost environments use HTTP instead of HTTPS
- Ensures proper protocol selection logic

### 5. **Token Response Variations** (`test_get_env_deploy_status_with_access_token_field`)
- Tests handling of different token field names (`token` vs `access_token`)
- Ensures compatibility with different auth implementations

### 6. **Network Errors** (`test_get_env_deploy_status_network_error`)
- Tests connection failures
- Validates error handling for network issues

## Required Environment Variables

The function requires these environment variables:
- `CLOUD_MANAGER_HOST` - Cloud manager hostname
- `CLIENT_HOST` - Client hostname for auth URL construction
- `CYODA_CLIENT_ID` - OAuth2 client ID (technical user)
- `CYODA_CLIENT_SECRET` - OAuth2 client secret (technical user)

## Test Execution

```bash
# Run all get_env_deploy_status tests
pytest application/agents/setup/tests/test_tools.py -k "get_env_deploy_status" -v

# Run all setup tools tests
pytest application/agents/setup/tests/test_tools.py -v
```

## Test Results

All 19 tests passing (10 new tests for `get_env_deploy_status` + 9 existing tests updated to async):
- ✅ 10 `get_env_deploy_status` tests
- ✅ 3 `validate_environment` tests
- ✅ 2 `check_project_structure` tests
- ✅ 4 `validate_workflow_file` tests

## Additional Changes

### Auth Middleware Created
Created `common/middleware/auth_middleware.py` to support the logs routes:
- Implements `@require_auth` decorator
- Validates JWT tokens from Authorization headers
- Attaches user info to request object (`user_id`, `is_superuser`, `org_id`)
- Returns 401 for invalid/expired/missing tokens
