# Cyoda API Usage Analysis Report
**Date:** 2026-01-09
**Scope:** `/home/kseniia/IdeaProjects/cyoda-ai-studio/application/`
**Focus:** All `find_all()` and `search()` calls to entity service

---

## Executive Summary

This document traces all usages of `entity_service.find_all()` and `entity_service.search()` in the application directory to identify potential performance issues related to data loading.

### Key Findings:
- **3 `find_all()` calls** - 🔴 ALL ARE PROBLEMATIC (no pagination)
- **7 `search()` calls** - ✅ Most have limits, 1 issue found
- **Critical Issues:** 2 high-severity issues requiring immediate attention

---

## 1. `find_all()` Usage (3 occurrences)

### 🔴 CRITICAL #1: Agent Tool - Find All Entities
**File:** `application/agents/cyoda_data_agent/tools.py:142`
**Function:** `find_all_entities()`

```python
async def find_all_entities(
    tool_context: ToolContext,
    client_id: str,
    client_secret: str,
    cyoda_host: str,
    entity_model: str,
) -> dict[str, Any]:
    """Find all entities of a type in user's Cyoda environment."""
    container = UserServiceContainer(...)
    entity_service = container.get_entity_service()
    results = await entity_service.find_all(entity_model, entity_version="1")
    return {"success": True, "data": results}
```

**Analysis:**
- **Exposure:** Google ADK agent tool (exposed to LLM)
- **Limit:** ❌ None
- **Cyoda API:** `GET /entity/{entity_model}/1` (loads ALL entities)
- **Risk:** HIGH - LLM can trigger this on large datasets
- **Impact:** If entity has 100k records, loads all 100k into memory
- **Recommendation:** Add limit parameter (default 100, max 10000)

---

### 🔴 CRITICAL #2: Agent Tool - Find All Entities (Subagent)
**File:** `application/agents/cyoda_data_agent/subagents/entity_management/tool_definitions/search/tools/find_all_entities_tool.py:40`
**Function:** `find_all_entities()`

```python
@handle_entity_errors
async def find_all_entities(
    tool_context: ToolContext,
    client_id: str,
    client_secret: str,
    cyoda_host: str,
    entity_model: str,
) -> dict[str, Any]:
    """Find all entities of a type in user's Cyoda environment."""
    container = get_user_service_container(client_id, client_secret, cyoda_host)
    entity_service = container.get_entity_service()
    results = await entity_service.find_all(entity_model, entity_version="1")
    return format_entity_success(results)
```

**Analysis:**
- **Exposure:** Entity management subagent tool
- **Limit:** ❌ None
- **Cyoda API:** `GET /entity/{entity_model}/1`
- **Risk:** HIGH - Same as above, different tool implementation
- **Impact:** Duplicate implementation with same issue
- **Recommendation:** Consolidate with above, add limits

---

### 🔴 CRITICAL #3: Conversation Repository - Superuser List All
**File:** `application/repositories/conversation_repository.py:119`
**Function:** `search()` method

```python
async def search(
    self,
    user_id: Optional[str] = None,
    limit: int = 100,
    point_in_time: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Search conversations with optional filters."""
    if user_id:
        search_condition = (
            SearchConditionRequest.builder()
            .equals("user_id", user_id)
            .limit(limit)
            .build()
        )
        response_list = await self.entity_service.search(...)
    else:
        # 🔴 PROBLEM: When user_id is None (superuser mode)
        response_list = await self.entity_service.find_all(
            entity_class=Conversation.ENTITY_NAME,
            entity_version=str(Conversation.ENTITY_VERSION),
        )
    return response_list if isinstance(response_list, list) else []
```

**Analysis:**
- **Exposure:** Internal conversation repository
- **Triggered When:** `user_id=None` (superuser listing all conversations)
- **Limit:** ❌ None
- **Cyoda API:** `GET /entity/conversation/1`
- **Risk:** HIGH - Admin operations can load all conversations from all users
- **Impact:** With 1000 users × 10 conversations = 10,000 entities loaded
- **Used By:**
  - Superuser/admin conversation listing
  - System operations
- **Recommendation:** Replace with `search()` that includes limit parameter

**Fix:**
```python
else:
    # Use search with limit even for superuser
    search_condition = SearchConditionRequest.builder().limit(limit).build()
    response_list = await self.entity_service.search(
        entity_class=Conversation.ENTITY_NAME,
        condition=search_condition,
        entity_version=str(Conversation.ENTITY_VERSION),
    )
```

---

## 2. `search()` Usage (7 occurrences)

### ✅ GOOD #1: Conversation List Operations
**File:** `application/services/chat/service/core/list_operations.py:65`
**Function:** `list_conversations()`

```python
async def list_conversations(
    conversation_repo: ConversationRepository,
    cache_manager: ChatCacheManager,
    user_id: Optional[str] = None,
    limit: int = CHAT_LIST_DEFAULT_LIMIT,  # 100
    before: Optional[str] = None,
    use_cache: bool = True,
) -> Dict:
    """List conversations with pagination and caching."""
    # Fetch from repository
    response_list = await conversation_repo.search(
        user_id=user_id, limit=limit + 1, point_in_time=before
    )
```

**Analysis:**
- **Limit:** ✅ Yes - defaults to 100 (CHAT_LIST_DEFAULT_LIMIT)
- **Pagination:** ✅ Yes - cursor-based via `point_in_time`
- **Caching:** ✅ Yes
- **Risk:** LOW
- **Status:** GOOD - properly implemented

---

### ⚠️ ISSUE #2: Guest Chat Transfer
**File:** `application/services/chat/service/core/conversation_operations.py:191`
**Function:** `transfer_guest_chats_to_authenticated_user()`

```python
async def transfer_guest_chats_to_authenticated_user(
    conversation_repo: ConversationRepository,
    cache_manager: ChatCacheManager,
    guest_user_id: str,
    authenticated_user_id: str,
) -> int:
    """Transfer all guest user chats to authenticated user."""
    # Find all guest chats
    guest_chats = await conversation_repo.search(user_id=guest_user_id)

    transferred_count = 0
    for chat_response in guest_chats:
        # ... transfer logic
```

**Analysis:**
- **Limit:** ⚠️ Implicit default (100) from repository
- **Issue:** If guest has >100 chats, only first 100 transferred!
- **Risk:** MEDIUM - Silent data loss
- **Impact:** Partial chat transfer for power users
- **Recommendation:** Add explicit high limit or pagination loop

**Fix:**
```python
# Option 1: High limit
guest_chats = await conversation_repo.search(
    user_id=guest_user_id,
    limit=10000  # Explicit high limit
)

# Option 2: Pagination loop (better)
all_chats = []
cursor = None
while True:
    batch = await conversation_repo.search(
        user_id=guest_user_id,
        limit=100,
        point_in_time=cursor
    )
    if not batch:
        break
    all_chats.extend(batch)
    if len(batch) < 100:
        break
    cursor = batch[-1].date
```

---

### ✅ GOOD #3: Agent Tool - Search Entities
**File:** `application/agents/cyoda_data_agent/tools.py:104`
**Function:** `search_entities()`

```python
async def search_entities(
    tool_context: ToolContext,
    client_id: str,
    client_secret: str,
    cyoda_host: str,
    entity_model: str,
    search_conditions: dict[str, Any],
) -> dict[str, Any]:
    """Search entities in user's Cyoda environment."""
    conditions = [
        SearchCondition(field=k, operator=CyodaOperator.EQUALS, value=v)
        for k, v in search_conditions.items()
    ]
    search_request = SearchConditionRequest(conditions=conditions)

    results = await entity_service.search(
        entity_model, search_request, entity_version="1"
    )
```

**Analysis:**
- **Limit:** ⚠️ No explicit limit in this tool
- **Note:** Relies on SearchConditionRequest default behavior
- **Cyoda API:** `POST /search/{entity_model}/1` (default limit 1000)
- **Risk:** MEDIUM - Could load up to 1000 records
- **Recommendation:** Add limit parameter to tool interface

---

### ✅ GOOD #4: Entity Management Subagent - Search Entities
**File:** `application/agents/cyoda_data_agent/subagents/entity_management/tool_definitions/search/tools/search_entities_tool.py:53`
**Function:** `search_entities()`

```python
async def search_entities(
    tool_context: ToolContext,
    client_id: str,
    client_secret: str,
    cyoda_host: str,
    entity_model: str,
    search_conditions: dict[str, Any],
) -> dict[str, Any]:
    """Search entities in user's Cyoda environment."""
    conditions = [
        SearchCondition(field=k, operator=CyodaOperator.EQUALS, value=v)
        for k, v in search_conditions.items()
    ]
    search_request = SearchConditionRequest(conditions=conditions)

    results = await entity_service.search(
        entity_model, search_request, entity_version="1"
    )
```

**Analysis:**
- **Limit:** ⚠️ Same as above - no explicit limit
- **Note:** Duplicate implementation
- **Risk:** MEDIUM
- **Status:** Same issue as #3

---

### ✅ GOOD #5: Session Service - List Sessions
**File:** `application/services/cyoda_session_service.py:215`
**Function:** `list_sessions()`

```python
async def list_sessions(
    self, app_name: str, user_id: Optional[str] = None
) -> ListSessionsResponse:
    """List sessions from Cyoda."""
    builder = SearchConditionRequest.builder()
    builder.add_condition("app_name", CyodaOperator.EQUALS, app_name)
    if user_id:
        builder.add_condition("user_id", CyodaOperator.EQUALS, user_id)

    responses = await self.entity_service.search(
        entity_class=self.ENTITY_NAME,
        condition=builder.build(),
        entity_version=self.ENTITY_VERSION,
    )
```

**Analysis:**
- **Limit:** ⚠️ No explicit limit
- **Filters:** app_name + optional user_id (should limit results naturally)
- **Risk:** LOW-MEDIUM - Depends on session count per app/user
- **Recommendation:** Add explicit limit for safety

---

### ✅ GOOD #6: Session Retrieval - Find by Session ID
**File:** `application/services/session_service/retrieval.py:109`
**Function:** `find_session_by_search()`

```python
async def find_session_by_search(
    entity_service: EntityService,
    app_name: str,
    user_id: str,
    session_id: str,
    entity_name: str,
    entity_version: str,
) -> Optional[AdkSession]:
    """Find session by session_id using search."""
    builder = SearchConditionRequest.builder()
    builder.add_condition("session_id", CyodaOperator.EQUALS, session_id)

    responses = await entity_service.search(
        entity_class=entity_name,
        condition=builder.build(),
        entity_version=entity_version,
    )

    if not responses:
        return None

    # Get the first matching session
    response = responses[0]
```

**Analysis:**
- **Limit:** ✅ Implicit - searching by unique session_id (should return 1)
- **Risk:** NONE - Single record expected
- **Status:** GOOD - appropriate use case

---

### ✅ GOOD #7: Conversation Repository - User Search
**File:** `application/repositories/conversation_repository.py:113`
**Function:** `search()` when `user_id` is provided

```python
if user_id:
    search_condition = (
        SearchConditionRequest.builder()
        .equals("user_id", user_id)
        .limit(limit)
        .build()
    )
    response_list = await self.entity_service.search(
        entity_class=Conversation.ENTITY_NAME,
        condition=search_condition,
        entity_version=str(Conversation.ENTITY_VERSION),
    )
```

**Analysis:**
- **Limit:** ✅ Yes - explicit limit parameter (default 100)
- **Pagination:** ✅ Supports point_in_time for cursor-based
- **Risk:** NONE
- **Status:** GOOD - properly implemented

---

## 3. Summary Table

| # | File | Function | Method | Limit | Risk | Status |
|---|------|----------|--------|-------|------|--------|
| 1 | `agents/cyoda_data_agent/tools.py` | `find_all_entities()` | `find_all()` | ❌ None | 🔴 HIGH | CRITICAL |
| 2 | `agents/.../find_all_entities_tool.py` | `find_all_entities()` | `find_all()` | ❌ None | 🔴 HIGH | CRITICAL |
| 3 | `repositories/conversation_repository.py` | `search()` (no user_id) | `find_all()` | ❌ None | 🔴 HIGH | CRITICAL |
| 4 | `services/chat/.../list_operations.py` | `list_conversations()` | `search()` | ✅ 100 | 🟢 LOW | GOOD |
| 5 | `services/chat/.../conversation_operations.py` | `transfer_guest_chats()` | `search()` | ⚠️ 100 | 🟡 MEDIUM | ISSUE |
| 6 | `agents/cyoda_data_agent/tools.py` | `search_entities()` | `search()` | ⚠️ Default | 🟡 MEDIUM | WARNING |
| 7 | `agents/.../search_entities_tool.py` | `search_entities()` | `search()` | ⚠️ Default | 🟡 MEDIUM | WARNING |
| 8 | `services/cyoda_session_service.py` | `list_sessions()` | `search()` | ⚠️ Default | 🟡 MEDIUM | WARNING |
| 9 | `services/session_service/retrieval.py` | `find_session_by_search()` | `search()` | ✅ Implicit (1) | 🟢 NONE | GOOD |
| 10 | `repositories/conversation_repository.py` | `search()` (with user_id) | `search()` | ✅ 100 | 🟢 NONE | GOOD |

---

## 4. Cyoda API Endpoints Used

### GET /entity/{entity_model}/{entity_version}
**Used by:** `find_all()`
**Characteristics:**
- Returns ALL entities of that type
- No pagination
- No limit parameter
- Response is full list in memory

**Files using this:**
- `agents/cyoda_data_agent/tools.py:142`
- `agents/.../find_all_entities_tool.py:40`
- `repositories/conversation_repository.py:119`

### POST /search/{entity_model}/{entity_version}
**Used by:** `search()`
**Characteristics:**
- Supports query conditions
- Supports `limit` query parameter (default 1000, max 10000)
- Supports `clientPointTime` for cursor-based pagination
- Returns filtered/paginated results

**Query Parameters:**
```
?limit={1-10000}&clientPointTime={ISO-timestamp}
```

**Files using this:** All 7 `search()` calls listed above

---

## 5. Priority Recommendations

### 🔴 CRITICAL (Immediate Action Required)

#### 1. Fix Agent Tools - Add Limits
**Files:**
- `application/agents/cyoda_data_agent/tools.py:142`
- `application/agents/cyoda_data_agent/subagents/entity_management/tool_definitions/search/tools/find_all_entities_tool.py:40`

**Action:**
```python
async def find_all_entities(
    tool_context: ToolContext,
    client_id: str,
    client_secret: str,
    cyoda_host: str,
    entity_model: str,
    limit: int = 100,  # ADD THIS
) -> dict[str, Any]:
    """Find all entities of a type in user's Cyoda environment.

    Args:
        limit: Maximum number of entities to return (default: 100, max: 10000)
    """
    search_condition = SearchConditionRequest.builder().limit(limit).build()
    results = await entity_service.search(  # CHANGE TO SEARCH
        entity_model, search_condition, entity_version="1"
    )
    return {"success": True, "data": results}
```

#### 2. Fix Conversation Repository - Superuser Mode
**File:** `application/repositories/conversation_repository.py:119`

**Action:**
```python
else:
    # Even for superuser, use search with limit
    search_condition = SearchConditionRequest.builder().limit(limit).build()
    response_list = await self.entity_service.search(
        entity_class=Conversation.ENTITY_NAME,
        condition=search_condition,
        entity_version=str(Conversation.ENTITY_VERSION),
    )
```

### 🟡 MEDIUM (Schedule for Next Sprint)

#### 3. Fix Guest Chat Transfer - Add Pagination
**File:** `application/services/chat/service/core/conversation_operations.py:191`

**Action:** Implement pagination loop or high explicit limit

#### 4. Add Explicit Limits to All Search Calls
**Files:**
- `application/agents/cyoda_data_agent/tools.py:104`
- `application/agents/cyoda_data_agent/subagents/entity_management/tool_definitions/search/tools/search_entities_tool.py:53`
- `application/services/cyoda_session_service.py:215`

**Action:** Add `limit` parameter to SearchConditionRequest builders

### 🟢 LOW (Technical Debt)

#### 5. Consolidate Duplicate Implementations
**Files:**
- `agents/cyoda_data_agent/tools.py` has duplicate tools with subagents

**Action:** Remove duplicates, use only subagent tools

#### 6. Add Monitoring/Logging
**Action:** Log warnings when:
- `find_all()` is called
- `search()` is called without explicit limit
- Result sets exceed 1000 records

---

## 6. Testing Recommendations

### Unit Tests Needed:
1. Test agent tools with large datasets (10k+ records)
2. Test superuser conversation listing with >1000 conversations
3. Test guest chat transfer with >100 chats
4. Test search operations with various limit values

### Load Tests Needed:
1. Benchmark `find_all()` vs `search()` with 1k, 10k, 100k records
2. Memory profiling of each operation
3. Response time measurements

---

## 7. Migration Path

### Phase 1: Critical Fixes (Week 1)
- [ ] Add limits to agent tools
- [ ] Fix conversation repository superuser mode
- [ ] Add logging for `find_all()` calls

### Phase 2: Medium Priority (Week 2)
- [ ] Fix guest chat transfer pagination
- [ ] Add explicit limits to all search calls
- [ ] Add unit tests

### Phase 3: Cleanup (Week 3)
- [ ] Remove duplicate implementations
- [ ] Add monitoring/alerting
- [ ] Performance testing
- [ ] Documentation updates

---

## Appendix: Code Locations Reference

### find_all() Calls:
```
1. application/agents/cyoda_data_agent/tools.py:142
2. application/agents/cyoda_data_agent/subagents/entity_management/tool_definitions/search/tools/find_all_entities_tool.py:40
3. application/repositories/conversation_repository.py:119
```

### search() Calls:
```
4. application/services/chat/service/core/list_operations.py:65
5. application/services/chat/service/core/conversation_operations.py:191
6. application/agents/cyoda_data_agent/tools.py:104
7. application/agents/cyoda_data_agent/subagents/entity_management/tool_definitions/search/tools/search_entities_tool.py:53
8. application/services/cyoda_session_service.py:215
9. application/services/session_service/retrieval.py:109
10. application/repositories/conversation_repository.py:113
```

---

**End of Report**
