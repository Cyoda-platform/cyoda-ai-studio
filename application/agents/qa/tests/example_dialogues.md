# QA Agent - Example Dialogues

## Overview
The QA Agent is a Cyoda platform expert that answers questions about architecture, concepts, entity management, workflows, and troubleshooting.

## Available Tools
- `search_cyoda_concepts` - Search for Cyoda platform concepts and documentation
- `explain_cyoda_pattern` - Get detailed explanations of Cyoda design patterns
- `load_web_page` - Load and analyze web documentation

---

## Example Dialogue 1: Understanding Technical IDs

**User:** What is a technical ID in Cyoda?

**Agent:** Let me search for information about technical IDs in Cyoda.

*[Calls: search_cyoda_concepts(query="technical id")]*

**Agent:** A technical ID in Cyoda is a UUID (Universally Unique Identifier) that uniquely identifies an entity instance. Here are the key points:

- **System-generated**: Technical IDs are automatically created by the Cyoda platform
- **Immutable**: Once assigned, a technical ID never changes
- **Unique**: Each entity instance has a unique technical ID across the entire system
- **Format**: Typically a UUID like `550e8400-e29b-41d4-a716-446655440000`

Technical IDs are used internally by Cyoda for entity management, relationships, and API operations.

---

## Example Dialogue 2: Entity Concepts

**User:** Explain what an entity is in Cyoda

**Agent:** I'll look up the entity concept for you.

*[Calls: search_cyoda_concepts(query="entity")]*

**Agent:** In Cyoda, an **entity** is a fundamental business object with the following characteristics:

1. **Versioned Schema**: Entities have a defined structure that can evolve over time with version control
2. **Lifecycle State**: Each entity instance has a state (e.g., DRAFT, VALIDATED, ARCHIVED)
3. **Workflow Management**: Entities can transition between states through defined workflows
4. **Data Storage**: Entity data is stored in JSON format with strong typing
5. **API Access**: Entities can be created, read, updated, and deleted via REST APIs

Examples of entities might include Customer, Order, Product, or any domain-specific business object in your application.

---

## Example Dialogue 3: Workflow Mechanics

**User:** How do workflows work in Cyoda?

**Agent:** Let me explain Cyoda workflows.

*[Calls: search_cyoda_concepts(query="workflow")]*

**Agent:** Workflows in Cyoda define how entities move through their lifecycle. Here's how they work:

**Structure:**
- Workflows are defined in JSON files
- Each workflow contains states and transitions
- States represent different stages in an entity's lifecycle

**Key Components:**
1. **States**: Define the possible lifecycle stages (e.g., DRAFT, SUBMITTED, APPROVED)
2. **Transitions**: Define allowed movements between states
3. **Manual Transitions**: State changes are triggered explicitly through API calls
4. **Validation**: Workflows can enforce business rules during transitions

**Example Flow:**
```
DRAFT → (submit) → SUBMITTED → (approve) → APPROVED
                              ↓ (reject)
                           REJECTED
```

Workflows ensure data integrity and enforce business processes throughout the entity lifecycle.

---

## Example Dialogue 4: Entity Service Pattern

**User:** What is the EntityService pattern in Cyoda?

**Agent:** Let me explain the EntityService pattern.

*[Calls: explain_cyoda_pattern(pattern_name="EntityService")]*

**Agent:** The **EntityService** is a core pattern in Cyoda applications that provides a standardized interface for entity operations:

**Purpose:**
- Centralized entity management
- Consistent CRUD operations
- Lifecycle and workflow management

**Key Methods:**
- `create(entity_data)` - Create new entity instances
- `find_by_id(technical_id)` - Retrieve entity by technical ID
- `find_all(search_conditions)` - Search for entities
- `update(technical_id, entity_data)` - Update existing entities
- `delete(technical_id)` - Delete entities
- `transition(technical_id, transition_name)` - Execute workflow transitions

**Best Practices:**
- Use EntityService in your business logic, not direct database access
- Keep route handlers thin - delegate to EntityService
- EntityService handles validation, state management, and persistence

---

## Example Dialogue 5: Repository Pattern

**User:** How should I structure my Cyoda repository?

**Agent:** Let me search for repository structure best practices.

*[Calls: search_cyoda_concepts(query="repository structure")]*

**Agent:** A well-structured Cyoda repository typically follows this organization:

```
project-root/
├── application/
│   ├── entity/           # Entity definitions
│   │   └── customer/
│   │       └── version_1/
│   │           └── customer.json
│   ├── workflow/         # Workflow definitions
│   │   └── customer/
│   │       └── version_1/
│   │           └── customerworkflow.json
│   ├── routes/           # API route handlers
│   ├── processors/       # Business logic processors
│   └── criteria/         # Search criteria definitions
├── common/               # Shared utilities
├── tests/                # Test files
└── requirements.txt      # Python dependencies
```

**Key Principles:**
- Separate concerns (entities, workflows, routes, logic)
- Version your entities and workflows
- Keep business logic in processors, not routes
- Use the common module for shared code

---

## Example Dialogue 6: Troubleshooting Entity Creation

**User:** I'm getting an error when creating an entity. What could be wrong?

**Agent:** Let me help you troubleshoot entity creation issues.

*[Calls: search_cyoda_concepts(query="entity creation errors")]*

**Agent:** Common entity creation errors and solutions:

**1. Schema Validation Errors:**
- **Cause**: Entity data doesn't match the defined schema
- **Solution**: Verify all required fields are present and data types match

**2. Missing Technical ID:**
- **Cause**: Trying to create with an existing technical ID
- **Solution**: Let Cyoda generate the technical ID automatically

**3. Lifecycle State Issues:**
- **Cause**: Invalid initial state
- **Solution**: Ensure the initial state exists in your workflow definition

**4. Version Mismatch:**
- **Cause**: Using wrong entity version
- **Solution**: Check that entity_version matches your entity definition

**Debugging Steps:**
1. Check the error message for specific field issues
2. Validate your entity JSON against the schema
3. Verify the entity version is correct
4. Ensure required environment variables are set (CYODA_HOST, CYODA_PORT)

Would you like me to help with a specific error message?

---

## Example Dialogue 7: Multi-turn Conversation

**User:** What's the difference between technical ID and business ID?

**Agent:** Let me explain the difference between these two types of identifiers.

*[Calls: search_cyoda_concepts(query="technical id business id")]*

**Agent:** Great question! Here's the distinction:

**Technical ID:**
- System-generated UUID
- Immutable and unique across the system
- Used internally by Cyoda for entity management
- Example: `550e8400-e29b-41d4-a716-446655440000`

**Business ID:**
- User-defined identifier meaningful to your business
- Can be any format (customer number, order ID, etc.)
- Used for human-readable references
- Example: `CUST-12345` or `ORD-2024-001`

**User:** So when should I use each one?

**Agent:** Excellent follow-up! Here's when to use each:

**Use Technical ID when:**
- Making API calls to Cyoda (create, update, delete)
- Establishing relationships between entities
- Internal system operations

**Use Business ID when:**
- Displaying information to users
- Searching for entities in your UI
- Integrating with external systems
- Generating reports

**Best Practice:** Store both! Use technical ID for system operations and business ID for user-facing features. You can search by business ID but use technical ID for updates.

---

## Example Dialogue 8: Loading External Documentation

**User:** Can you show me the official Cyoda documentation about entity lifecycle?

**Agent:** I'll load the official documentation for you.

*[Calls: load_web_page(url="https://docs.cyoda.com/entity-lifecycle")]*

**Agent:** Based on the official Cyoda documentation, here's what you need to know about entity lifecycle:

[Agent provides summary of the loaded documentation]

The documentation covers:
- Lifecycle state definitions
- State transition rules
- Workflow configuration
- Best practices for lifecycle management

Would you like me to explain any specific aspect in more detail?

---

## Tips for Interacting with QA Agent

1. **Be Specific**: Ask about specific Cyoda concepts, patterns, or features
2. **Follow-up Questions**: Feel free to ask clarifying questions
3. **Error Messages**: Share specific error messages for better troubleshooting
4. **Context**: Provide context about what you're trying to accomplish
5. **Documentation**: Ask for links to official documentation when needed

