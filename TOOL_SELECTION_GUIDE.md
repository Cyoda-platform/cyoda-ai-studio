# Cyoda Data Agent - Tool Selection Guide

## Quick Decision Tree

```
What does the user want?

├─ Get ONE specific entity by ID?
│  └─ Use: get_entity()
│     Example: "Get cat with ID abc123"
│
├─ Get ALL entities of a type (no filtering)?
│  └─ Use: find_all_entities() ⭐
│     Example: "Show me all cats"
│     Example: "List all products"
│     Example: "Get all users"
│
├─ FILTER/SEARCH by conditions?
│  └─ Use: search_entities()
│     Example: "Find black cats"
│     Example: "Search where color=orange"
│     Example: "All cats where age > 3"
│
└─ CREATE a new entity?
   └─ Use: create_entity()
      Example: "Create a new cat named Whiskers"
```

---

## Tool Comparison

| Tool | Purpose | When to Use | Example |
|------|---------|-------------|---------|
| `get_entity()` | Get ONE by ID | User has specific ID | "Get cat ID abc123" |
| `find_all_entities()` | Get ALL (no filter) | User wants everything | "Show all cats" |
| `search_entities()` | Filter by conditions | User wants specific matches | "Find black cats" |
| `create_entity()` | Create new | User wants to add | "Create cat Whiskers" |

---

## Common Mistakes

❌ **WRONG**: User says "Show all cats" → Use `search_entities()` with empty conditions
✅ **RIGHT**: User says "Show all cats" → Use `find_all_entities()`

❌ **WRONG**: User says "Find black cats" → Use `find_all_entities()`
✅ **RIGHT**: User says "Find black cats" → Use `search_entities()` with conditions

❌ **WRONG**: User says "Get cat abc123" → Use `search_entities()` with ID
✅ **RIGHT**: User says "Get cat abc123" → Use `get_entity()` with entity_id

---

## Key Differences

### find_all_entities() vs search_entities()

**find_all_entities():**
- Returns EVERYTHING of a type
- No filtering
- Faster for small datasets
- Use when user says: "all", "list", "show me everything"

**search_entities():**
- Returns FILTERED results
- Requires conditions (field=value)
- Better for large datasets with filtering
- Use when user says: "where", "find", "filter", "search"

---

## Examples

### ✅ Use find_all_entities()
```
"Show me all cats"
"List all products"
"Get all users"
"What cats do I have?"
"Display all entities"
```

### ✅ Use search_entities()
```
"Find all black cats"
"Search for cats where color is orange"
"Show me cats with age > 3"
"Find products where price < 100"
"Filter users by role=admin"
```

### ✅ Use get_entity()
```
"Get the cat with ID abc123"
"Retrieve entity 550e8400-e29b-41d4-a716-446655440000"
"Show me details of that cat"
```

### ✅ Use create_entity()
```
"Create a new cat named Whiskers"
"Add a product called Laptop"
"Insert a new user"
```

---

## Agent Behavior

The agent will:
1. ✅ Use `find_all_entities()` when user asks for "all" or "show all"
2. ✅ Use `search_entities()` when user specifies conditions
3. ✅ Use `get_entity()` when user provides a specific ID
4. ✅ Use `create_entity()` when user wants to add something new
5. ✅ Reuse credentials from session (no need to repeat)
6. ✅ Mention which environment is being used

