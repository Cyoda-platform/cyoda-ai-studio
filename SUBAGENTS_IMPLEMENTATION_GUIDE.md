# Subagents Implementation Guide for Cyoda Data Agent

## 🎯 Architecture Overview

Transform the current single-agent architecture into a multi-subagent system that reflects Cyoda's API structure.

---

## 📐 Proposed Subagent Structure

### 1. **Entity Management Subagent**
**Purpose**: Handle entity CRUD operations

**Tools**:
- `create_entity()` - Create new entities
- `update_entity()` - Update existing entities (NEW)
- `delete_entity()` - Delete entities (NEW)
- `get_entity_stats()` - Get entity statistics (NEW)

**Prompt Focus**: Entity lifecycle management, validation, batch operations

### 2. **Entity Search Subagent**
**Purpose**: Handle all search and retrieval operations

**Tools**:
- `find_all_entities()` - Get all entities
- `search_entities()` - Search with conditions
- `get_entity()` - Get single entity by ID
- `snapshot_search()` - Async distributed search (NEW)

**Prompt Focus**: Search strategies, filtering, pagination, performance

### 3. **Entity Model Subagent**
**Purpose**: Manage entity models and schemas

**Tools**:
- `list_models()` - List available models (NEW)
- `get_model()` - Get model details (NEW)
- `import_model()` - Import model definition (NEW)
- `export_model()` - Export model definition (NEW)
- `lock_model()` - Lock model for use (NEW)
- `unlock_model()` - Unlock model (NEW)

**Prompt Focus**: Model lifecycle, versioning, change control

### 4. **SQL Schema Subagent**
**Purpose**: Manage SQL schemas and database views

**Tools**:
- `generate_schema()` - Generate SQL from model (NEW)
- `list_tables()` - List database tables (NEW)
- `get_table_info()` - Get table details (NEW)
- `configure_view()` - Configure database view (NEW)

**Prompt Focus**: Schema design, SQL operations, view management

### 5. **Edge Messaging Subagent** (Optional)
**Purpose**: Handle edge message communication

**Tools**:
- `send_message()` - Send edge message (NEW)
- `get_message()` - Retrieve message (NEW)
- `list_messages()` - List messages (NEW)

**Prompt Focus**: Message routing, event handling

---

## 🔄 Orchestration Pattern

### Option A: ParallelAgent (Recommended for Independent Operations)
```python
root_agent = ParallelAgent(
    name="cyoda_data_agent",
    config=ParallelAgentConfig(
        agents=[
            entity_management_agent,
            entity_search_agent,
            entity_model_agent,
            sql_schema_agent,
        ]
    )
)
```
**When to use**: User asks for multiple independent operations

### Option B: SequentialAgent (For Dependent Operations)
```python
root_agent = SequentialAgent(
    name="cyoda_data_agent",
    config=SequentialAgentConfig(
        agents=[
            entity_model_agent,      # Validate model exists
            entity_management_agent, # Create entity
            entity_search_agent,     # Verify creation
        ]
    )
)
```
**When to use**: Operations depend on previous results

### Option C: Hybrid (Recommended)
Use a parent LlmAgent that routes to appropriate subagents based on user request:
```python
root_agent = LlmAgent(
    name="cyoda_data_agent",
    tools=[
        AgentTool(entity_management_agent),
        AgentTool(entity_search_agent),
        AgentTool(entity_model_agent),
        AgentTool(sql_schema_agent),
    ]
)
```

---

## 📝 Implementation Steps

### Step 1: Create Subagent Modules
```
application/agents/cyoda_data_agent/
├── subagents/
│   ├── __init__.py
│   ├── entity_management_agent.py
│   ├── entity_search_agent.py
│   ├── entity_model_agent.py
│   ├── sql_schema_agent.py
│   └── edge_messaging_agent.py
├── tools/
│   ├── entity_tools.py
│   ├── search_tools.py
│   ├── model_tools.py
│   ├── schema_tools.py
│   └── messaging_tools.py
└── prompts/
    ├── entity_management.template
    ├── entity_search.template
    ├── entity_model.template
    ├── sql_schema.template
    └── root_agent.template
```

### Step 2: Implement Tools
- Extend existing tools (create_entity, search_entities, etc.)
- Add new tools for model management
- Add new tools for schema operations
- Add new tools for messaging

### Step 3: Create Subagent Prompts
- Entity Management: Focus on CRUD operations
- Entity Search: Focus on query optimization
- Entity Model: Focus on model lifecycle
- SQL Schema: Focus on database operations

### Step 4: Create Root Agent
- Use LlmAgent with AgentTool references
- Route user requests to appropriate subagents
- Maintain credential reuse across subagents

### Step 5: Test Integration
- Test each subagent independently
- Test subagent communication
- Test credential passing
- Test error handling

---

## 🔐 Credential Management

**Key Principle**: Credentials are stored in session and passed to all subagents

```python
# Root agent stores credentials in context
context.session_state["cyoda_credentials"] = {
    "client_id": "...",
    "client_secret": "...",
    "cyoda_host": "...",
}

# Subagents retrieve from context
credentials = context.session_state["cyoda_credentials"]
```

---

## 📊 Benefits Summary

| Aspect | Current | With Subagents |
|--------|---------|-----------------|
| Tools | 4 | 20+ |
| Capabilities | Basic CRUD | Full API coverage |
| Scalability | Limited | Highly scalable |
| Maintainability | Single file | Modular |
| Testing | Monolithic | Isolated |
| Performance | Sequential | Parallel |

---

## ⚠️ Considerations

1. **Complexity**: More files and structure to maintain
2. **Context Passing**: Ensure credentials flow to all subagents
3. **Error Handling**: Handle failures in individual subagents
4. **Testing**: Need tests for each subagent + integration tests
5. **Documentation**: Update guides for new capabilities

---

## 🚀 Recommended Approach

**Start with Phase 2 (Subagent Architecture)**:
1. Create 3 core subagents (Management, Search, Model)
2. Keep SQL Schema as future enhancement
3. Use hybrid orchestration (LlmAgent + AgentTools)
4. Maintain backward compatibility with existing tools
5. Add new tools incrementally

This provides immediate value while keeping implementation manageable.

