# Environment Agent Test Prompts

This document contains test prompts to validate all environment and user application management tools.

## Namespace Architecture

- **Cyoda Environment**: `client-{user}-{env}` - Contains Cyoda platform services
- **User Application**: `client-app-{user}-{env}-{app}` - Contains user calculation nodes

These are **separate** namespaces with different operations.

---

## 1. Environment Operations (Cyoda Platform)

### 1.1 List Environments
```
List all my environments
Show my environments
What environments do I have?
```
**Expected Tool**: `list_environments()`
**Expected Result**: List of environments (dev, staging, prod, etc.) excluding app namespaces

---

### 1.2 Describe Environment
```
Describe my dev environment
What's running in my dev environment?
Show me what's in staging
Tell me about prod environment
```
**Expected Tool**: `describe_environment(env_name="dev")`
**Expected Result**: List of Cyoda platform deployments in the environment namespace

---

###1.3 Get Environment Metrics
```
Show metrics for dev environment
What's the CPU and memory usage in staging?
Get environment metrics for prod
```
**Expected Tool**: `get_environment_metrics(env_name="dev")`
**Expected Result**: CPU and memory metrics for Cyoda platform pods

---

### 1.4 Get Environment Pods
```
Show pods in dev environment
List all pods running in staging
What pods are in prod?
```
**Expected Tool**: `get_environment_pods(env_name="dev")`
**Expected Result**: List of pods in Cyoda environment namespace

---

### 1.5 Delete Environment (with Confirmation)
```
Delete my dev environment
Remove staging environment
I want to delete prod
```
**Expected Flow**:
1. Agent asks for confirmation
2. User confirms
3. Agent calls `delete_environment(env_name="dev")`
**Expected Result**: Environment and all associated user apps deleted (CASCADE)

---

## 2. User Application Operations

### 2.1 List User Applications
```
List my applications
Show all my apps
What apps do I have in dev?
List applications in staging environment
```
**Expected Tool**: `list_user_apps(env_name="dev")`
**Expected Result**: List of user app namespaces matching `client-{user}-dev-app-*`

---

### 2.2 Get User App Details
```
Describe my-calculator app
Show details of payment-service
What deployments are in my-app?
Tell me about calculator app in dev
```
**Expected Tool**: `get_user_app_details(env_name="dev", app_name="my-calculator")`
**Expected Result**: List of deployments within the user app namespace

---

### 2.3 Scale User App
```
Scale my-calculator to 3 replicas
Set payment-service to 2 replicas in staging
Scale down my-app to 0 replicas
```
**Expected Flow**:
1. Agent may need to call `get_user_app_details()` first to get deployment_name
2. Agent calls `scale_user_app(env_name="dev", app_name="my-calculator", deployment_name="calculator-deployment", replicas=3)`
3. Limit service checks if replicas <= MAX_REPLICAS_PER_APP (default: 3)
**Expected Result**: Deployment scaled to specified replicas (if within limits)

**Limit Test**:
```
Scale my-calculator to 10 replicas
```
**Expected Result**: Error message - "Replica count exceeds maximum limit of 3"

---

### 2.4 Restart User App
```
Restart my-calculator app
Restart the payment-service deployment
I need to restart my-app in staging
```
**Expected Flow**:
1. Agent may need to call `get_user_app_details()` first to get deployment_name
2. Agent calls `restart_user_app(env_name="dev", app_name="my-calculator", deployment_name="calculator-deployment")`
**Expected Result**: Rollout restart triggered

---

### 2.5 Update User App Image
```
Update my-calculator to use image my-calc:v2.0
Change payment-service image to payment:latest
Update my-app to new-image:v3
```
**Expected Flow**:
1. Agent may need to call `get_user_app_details()` first to get deployment_name
2. Agent calls `update_user_app_image(env_name="dev", app_name="my-calculator", deployment_name="calculator-deployment", image="my-calc:v2.0")`
**Expected Result**: Image updated, rollout in progress

---

### 2.6 Get User App Status
```
What's the status of my-calculator?
Check rollout status for payment-service
Is my-app deployment complete?
```
**Expected Flow**:
1. Agent may need to call `get_user_app_details()` first to get deployment_name
2. Agent calls `get_user_app_status(env_name="dev", app_name="my-calculator", deployment_name="calculator-deployment")`
**Expected Result**: Rollout status (in progress, complete, failed)

---

### 2.7 Get User App Metrics
```
Show metrics for my-calculator app
What's the CPU usage of payment-service?
Get metrics for my-app in staging
```
**Expected Tool**: `get_user_app_metrics(env_name="dev", app_name="my-calculator")`
**Expected Result**: CPU and memory metrics for user app pods

---

### 2.8 Get User App Pods
```
Show pods for my-calculator
List pods running in payment-service
What pods are in my-app?
```
**Expected Tool**: `get_user_app_pods(env_name="dev", app_name="my-calculator")`
**Expected Result**: List of pods in user app namespace

---

### 2.9 Delete User App (with Confirmation)
```
Delete my-calculator app
Remove payment-service
I want to delete my-app from staging
```
**Expected Flow**:
1. Agent asks for confirmation
2. User confirms
3. Agent calls `delete_user_app(env_name="dev", app_name="my-calculator")`
**Expected Result**: User app namespace deleted (environment remains)

---

## 3. Log Search Operations

### 3.1 Search Environment Logs
```
Show logs for dev environment
Search logs for staging
Get logs for prod environment
```
**Expected Tool**: `search_logs(env_name="dev", app_name="cyoda")`
**Expected Result**: Last 15 minutes of Cyoda platform logs from dev environment

---

### 3.2 Search User App Logs
```
Show logs for my-calculator
Search logs for payment-service
Get logs for my-app in staging
```
**Expected Tool**: `search_logs(env_name="dev", app_name="my-calculator")`
**Expected Result**: Last 15 minutes of logs from user app namespace

---

### 3.3 Search with Query Filter
```
Show me errors in dev environment
Search for ERROR in my-calculator logs
Find connection timeout errors
Show warning logs in staging
```
**Expected Tool**: `search_logs(env_name="dev", app_name="cyoda", query="ERROR")`
**Expected Result**: Filtered logs matching the search query

---

### 3.4 Search with Time Range
```
Show logs from last hour
Get logs from last 24 hours for dev
Show me logs from last week
Search logs from last 30 minutes
```
**Expected Tool**: `search_logs(env_name="dev", app_name="cyoda", time_range="1h")`
**Expected Result**: Logs from specified time range

---

### 3.5 Combined Query and Time Range
```
Show ERROR logs from last hour in dev
Search for 'connection timeout' in last 24 hours
Find failures in my-app from last 6 hours
```
**Expected Tool**: `search_logs(env_name="dev", app_name="cyoda", query="ERROR", time_range="1h")`
**Expected Result**: Filtered logs from specified time range

---

### 3.6 Custom Log Size
```
Show me last 100 log entries
Get 500 logs from dev environment
Show me 10 most recent logs
```
**Expected Tool**: `search_logs(env_name="dev", app_name="cyoda", size=100)`
**Expected Result**: Specified number of log entries (max 1000)

---

## 4. Combined Scenarios

### 4.1 Environment Overview
```
Give me a complete overview of my dev environment
Show me everything in staging - environment and apps
```
**Expected Flow**:
1. Call `describe_environment(env_name="dev")` - Show Cyoda platform
2. Call `list_user_apps(env_name="dev")` - Show user applications
3. Present combined view

---

### 4.2 App Details with Metrics
```
Show me everything about my-calculator - details, status, and metrics
Give me full info on payment-service
```
**Expected Flow**:
1. Call `get_user_app_details(env_name="dev", app_name="my-calculator")`
2. Call `get_user_app_metrics(env_name="dev", app_name="my-calculator")`
3. Call `get_user_app_pods(env_name="dev", app_name="my-calculator")`
4. Present combined view

---

### 4.3 Scale with Status Check
```
Scale my-calculator to 5 replicas and check the status
```
**Expected Flow**:
1. Get deployment name via `get_user_app_details()`
2. Call `scale_user_app(env_name="dev", app_name="my-calculator", deployment_name="...", replicas=5)`
3. Call `get_user_app_status()` to check rollout
4. Present scaling result and status

---

## 5. Edge Cases & Error Handling

### 5.1 Non-Existent Environment
```
Show my test environment
List apps in nonexistent-env
```
**Expected Result**: Error message indicating environment not found

---

### 5.2 Non-Existent App
```
Describe nonexistent-app
Scale fake-app to 3 replicas
```
**Expected Result**: Error message indicating app not found

---

### 5.3 Missing Parameters
```
Scale my-app
(without specifying replicas)
```
**Expected Result**: Agent asks for missing parameter (replicas)

---

### 5.4 Invalid Parameters
```
Scale my-app to -1 replicas
Scale my-app to 100 replicas
```
**Expected Result**:
- Negative replicas: Error message "Replicas must be >= 0"
- Over limit: Error message "Replica count exceeds maximum limit of 3"

---

## 6. Test Execution Checklist

Use this checklist to verify all tools work correctly:

### Environment Tools
- [ ] `list_environments()` - Lists environments correctly
- [ ] `describe_environment()` - Shows Cyoda platform deployments
- [ ] `get_environment_metrics()` - Returns metrics for environment
- [ ] `get_environment_pods()` - Lists environment pods
- [ ] `delete_environment()` - Deletes environment with cascade

### User App Tools
- [ ] `list_user_apps()` - Lists user applications
- [ ] `get_user_app_details()` - Shows app deployments
- [ ] `scale_user_app()` - Scales deployment
- [ ] `restart_user_app()` - Restarts deployment
- [ ] `update_user_app_image()` - Updates image
- [ ] `get_user_app_status()` - Returns rollout status
- [ ] `get_user_app_metrics()` - Returns app metrics
- [ ] `get_user_app_pods()` - Lists app pods
- [ ] `delete_user_app()` - Deletes app namespace

### Log Management Tools
- [ ] `search_logs()` - Searches logs for environment
- [ ] `search_logs()` - Searches logs for user app
- [ ] `search_logs()` - Filters logs with query
- [ ] `search_logs()` - Searches with time range
- [ ] `search_logs()` - Custom log size

### Agent Behavior
- [ ] No infinite loops (circuit breaker at 25 turns)
- [ ] Direct tool calls (no agent bouncing)
- [ ] Proper error messages
- [ ] User-friendly output formatting
- [ ] Confirmation for destructive operations

---

## 7. Expected Agent Behavior

### Good Agent Behavior ✅
- Calls tools directly without bouncing between agents
- Asks for confirmation before destructive operations
- Provides clear, formatted output
- Handles errors gracefully
- Guides user when parameters are missing

### Bad Agent Behavior ❌
- Transfers between agents repeatedly
- Doesn't call the right tool
- Doesn't ask for confirmation before deletions
- Returns raw JSON without formatting
- Gets stuck in loops

---

## Notes

- All operations require user to be logged in
- Environment names: typically `dev`, `staging`, `prod`
- App names: typically lowercase with hyphens (e.g., `my-calculator`, `payment-service`)
- Deployment names: usually `{app-name}-deployment` but can vary
- For scale/restart/update/status operations, agent may need to call `get_user_app_details()` first to determine deployment name

---

## 7. Resource Limits & Quotas

### Current Limits (Configurable via Environment Variables)

| Resource | Default Limit | Environment Variable | Description |
|----------|---------------|---------------------|-------------|
| **Max Replicas per App** | 3 | `MAX_REPLICAS_PER_APP` | Maximum replicas for any user app deployment |
| **Max Apps per Environment** | 10 | `MAX_APPS_PER_ENVIRONMENT` | Maximum user apps in one environment |
| **Max Environments per User** | 5 | `MAX_ENVIRONMENTS_PER_USER` | Maximum environments per user |
| **Max CPU per App** | 2 cores | `MAX_CPU_PER_APP` | Maximum CPU allocation |
| **Max Memory per App** | 4Gi | `MAX_MEMORY_PER_APP` | Maximum memory allocation |

### Enforced Operations

Currently enforced:
- ✅ **Scale User App** - Checks `MAX_REPLICAS_PER_APP`

Future enforcement:
- ⏳ **Deploy User App** - Will check `MAX_APPS_PER_ENVIRONMENT`
- ⏳ **Deploy Environment** - Will check `MAX_ENVIRONMENTS_PER_USER`
- ⏳ **Resource Requests** - Will check CPU/memory limits

### Future Integration

The `ResourceLimitService` is designed for easy integration with:
- **User Quota Service API** - Per-user quotas from backend
- **Database-backed Quotas** - Persistent quota management
- **Tiered Limits** - Free/Paid/Enterprise tiers with different limits
- **Dynamic Quotas** - Adjust limits based on usage patterns

### Limit Error Messages

When a limit is exceeded, users receive:
```json
{
  "error": "Replica count exceeds maximum limit of 3",
  "limit": 3,
  "requested": 10,
  "message": "❌ Replica count exceeds maximum limit of 3\n   Requested: 10\n   Limit: 3"
}
```

### Testing Limits

To test different limits, set environment variables:
```bash
export MAX_REPLICAS_PER_APP=5
export MAX_APPS_PER_ENVIRONMENT=20
export MAX_ENVIRONMENTS_PER_USER=10
```

Then restart the application to apply new limits.
