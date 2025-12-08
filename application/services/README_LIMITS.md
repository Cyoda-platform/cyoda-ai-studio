# Resource Limit Service

Clean, extensible service for managing user resource quotas and limits.

## Overview

The `ResourceLimitService` provides centralized limit checking for user operations. It's designed to be easily extended with a user quota service API in the future.

## Architecture

```
┌─────────────────────────────────────────┐
│         User Operation Request          │
│    (scale_user_app, deploy_app, etc)    │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│      ResourceLimitService                │
│  ┌───────────────────────────────────┐  │
│  │  check_replica_limit()            │  │
│  │  check_app_count_limit()          │  │
│  │  check_environment_count_limit()  │  │
│  └───────────────────────────────────┘  │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  Future: User Quota Service API          │
│  - Per-user quotas                       │
│  - Tiered limits (free/paid/enterprise)  │
│  - Database-backed persistence           │
└─────────────────────────────────────────┘
```

## Current Implementation

### Hard-Coded Limits (v1)

Currently uses environment variables with defaults:

| Limit | Default | Env Var | Applied To |
|-------|---------|---------|------------|
| Max Replicas per App | 3 | `MAX_REPLICAS_PER_APP` | `scale_user_app()` |
| Max Apps per Environment | 10 | `MAX_APPS_PER_ENVIRONMENT` | Future: `deploy_user_application()` |
| Max Environments per User | 5 | `MAX_ENVIRONMENTS_PER_USER` | Future: `deploy_cyoda_environment()` |
| Max CPU per App | 2 cores | `MAX_CPU_PER_APP` | Future |
| Max Memory per App | 4Gi | `MAX_MEMORY_PER_APP` | Future |

### Usage Example

```python
from application.services.resource_limit_service import get_resource_limit_service

# Get singleton instance
limit_service = get_resource_limit_service()

# Check replica limit
result = limit_service.check_replica_limit(
    user_id="user123",
    env_name="dev",
    app_name="my-calculator",
    requested_replicas=5
)

if not result.allowed:
    # Operation denied
    error_msg = limit_service.format_limit_error(result)
    return {"error": result.reason, "message": error_msg}

# Proceed with operation
...
```

## Integration Points

### Currently Integrated
- ✅ `scale_user_app()` - Checks replica limit before scaling

### Future Integration
- ⏳ `deploy_user_application()` - Check app count limit
- ⏳ `deploy_cyoda_environment()` - Check environment count limit
- ⏳ Resource requests - Check CPU/memory limits

## Future Extension: User Quota Service

### Phase 2: API Integration

```python
class ResourceLimitService:
    def __init__(self, quota_service_url: Optional[str] = None):
        self.quota_service_url = quota_service_url
        if quota_service_url:
            self.use_quota_service = True
        else:
            self.use_quota_service = False
            self.limits = self._load_limits()

    async def check_replica_limit(self, user_id: str, ...) -> QuotaCheckResult:
        if self.use_quota_service:
            # Call user quota service API
            limits = await self._fetch_user_limits(user_id)
        else:
            # Use hard-coded limits
            limits = self.limits

        # Check against limits
        ...
```

### Phase 3: Database-Backed Quotas

```python
# Store quotas in database
quotas_table:
  - user_id
  - tier (free, paid, enterprise)
  - max_replicas
  - max_apps
  - max_environments
  - custom_limits (JSON)

# Query on each operation
user_limits = await db.get_user_quotas(user_id)
```

### Phase 4: Dynamic Quota Adjustments

```python
# Adjust quotas based on:
- Usage patterns
- Subscription tier changes
- Promotional offers
- Admin overrides
- Time-based limits (trial periods)
```

## Configuration

### Environment Variables

```bash
# Set custom limits
export MAX_REPLICAS_PER_APP=5
export MAX_APPS_PER_ENVIRONMENT=20
export MAX_ENVIRONMENTS_PER_USER=10
export MAX_CPU_PER_APP="4"
export MAX_MEMORY_PER_APP="8Gi"
```

### Programmatic Configuration

```python
# For testing or custom setups
from application.services.resource_limit_service import ResourceLimitService, ResourceLimits

custom_limits = ResourceLimits(
    max_replicas=10,
    max_apps_per_environment=50,
    max_environments=20
)

service = ResourceLimitService()
service.limits = custom_limits
```

## Error Handling

### QuotaCheckResult

```python
@dataclass
class QuotaCheckResult:
    allowed: bool              # Operation allowed?
    reason: Optional[str]      # Why denied?
    limit_value: Optional[int] # What's the limit?
    current_value: Optional[int] # What was requested?
```

### Error Response Format

```json
{
  "error": "Replica count exceeds maximum limit of 3",
  "limit": 3,
  "requested": 10,
  "message": "❌ Replica count exceeds maximum limit of 3\n   Requested: 10\n   Limit: 3"
}
```

## Testing

### Unit Tests

```python
def test_replica_limit_within_bounds():
    service = get_resource_limit_service()
    result = service.check_replica_limit("user123", "dev", "app", 2)
    assert result.allowed == True

def test_replica_limit_exceeded():
    service = get_resource_limit_service()
    result = service.check_replica_limit("user123", "dev", "app", 10)
    assert result.allowed == False
    assert result.limit_value == 3
```

### Integration Tests

```bash
# Test via agent prompts
"Scale my-calculator to 3 replicas"  # Should succeed
"Scale my-calculator to 10 replicas" # Should fail with limit error
```

## Logging

The service logs:
- Limit checks (debug level)
- Limit violations (warning level)
- Configuration loading (info level)

```python
logger.warning(
    f"Replica limit exceeded for user={user_id}, env={env_name}, "
    f"app={app_name}: requested={requested_replicas}, limit={max_replicas}"
)
```

## Design Principles

1. **Single Responsibility**: Service only checks limits, doesn't enforce operations
2. **Open for Extension**: Easy to add new limit types
3. **Closed for Modification**: Existing limit checks don't change when adding new ones
4. **Clean Integration**: Minimal changes to calling code
5. **Future-Proof**: Designed for quota service integration from day one

## Migration Path

### Current (v1)
```
Environment Variables → ResourceLimitService → Operations
```

### Future (v2)
```
User Quota Service API → ResourceLimitService → Operations
                     ↓
            Database Storage
```

### Transition Strategy
1. Keep env var support for defaults
2. Add quota service URL configuration
3. Check quota service first, fall back to env vars
4. Gradual rollout per user tier
5. Eventually deprecate env vars for production
