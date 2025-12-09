# Tool Selection Fix - Cyoda Data Agent

## Problem

When user asked: **"Show me all cat entities in my environment"**

The agent incorrectly used `search_entities()` instead of `find_all_entities()`.

### Why This Was Wrong

- `search_entities()` is for FILTERING by conditions (e.g., "find black cats")
- `find_all_entities()` is for getting ALL entities without filtering
- User said "show me ALL" → should use `find_all_entities()`

---

## Solution

Updated the agent prompt with:

### 1. **Critical Decision Tree** (NEW)
Added a clear decision tree at the top of the prompt:

```
1. User wants a SINGLE entity by ID?
   → Use get_entity()

2. User wants ALL entities (no filtering)?
   → Use find_all_entities() ⭐

3. User wants to FILTER/SEARCH by conditions?
   → Use search_entities()

4. User wants to CREATE a new entity?
   → Use create_entity()
```

### 2. **Clearer Tool Descriptions**
- Marked `find_all_entities()` with ⭐ and "USE THIS FOR SHOW ALL"
- Marked `search_entities()` with "USE THIS FOR FILTERING"
- Added explicit examples for each

### 3. **Tool Comparison Table**
Created documentation showing when to use each tool

---

## Files Updated

- `application/agents/cyoda_data_agent/prompts/cyoda_data_agent.template`
  - Added decision tree section
  - Reordered tools (find_all before search)
  - Added clear "when to use" guidance
  - Added ⭐ markers for clarity

- `TOOL_SELECTION_GUIDE.md` (NEW)
  - Quick reference for tool selection
  - Common mistakes section
  - Examples for each tool

---

## Expected Behavior After Fix

**User**: "Show me all cat entities in my environment"

**Agent**: 
- ✅ Recognizes "show me all" = no filtering
- ✅ Uses `find_all_entities()` (not search_entities)
- ✅ Returns all cat entities
- ✅ Reuses credentials from session

---

## Test Case

```
User 1: "Show me all cats"
Agent: Uses find_all_entities() ✅

User 2: "Find black cats"
Agent: Uses search_entities() ✅

User 3: "Get cat with ID abc123"
Agent: Uses get_entity() ✅

User 4: "Create a new cat named Whiskers"
Agent: Uses create_entity() ✅
```

---

## Key Takeaway

The agent now has a **clear decision tree** to select the right tool:
- **ALL entities** → `find_all_entities()`
- **FILTERED entities** → `search_entities()`
- **SINGLE entity by ID** → `get_entity()`
- **NEW entity** → `create_entity()`

