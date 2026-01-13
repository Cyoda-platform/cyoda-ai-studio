# Dialogue Scenarios

## Scenario 1: Build Application from Scratch

### Agents Involved
- **Cyoda AI Assistant** (Main)
- **GitHub Agent** (Sub-agent)
- **Environment Agent** (Sub-agent)
- **Setup Assistant Agent** (Sub-agent)

### Tools Flow
1. `generate_application()` → GitHub Agent.generate_code_with_cli()
2. `deploy_cyoda_environment()` → Environment Agent.deploy_environment() → Cloud Manager API
3. `launch_setup_assistant()` → Setup Assistant Agent.initialize_setup_flow()

### Dialogue
```
U: Build a solution that enables customers to order products online.

A: [Cyoda AI Assistant → generate_application() → GitHub Agent]
   Got it! I will build an application for you...

U: Yes, please deploy the environment.

A: [Cyoda AI Assistant → deploy_cyoda_environment() → Environment Agent]
   Sure! I will deploy your Cyoda environment...

U: Launch the setup assistant.

A: [Cyoda AI Assistant → launch_setup_assistant() → Setup Assistant Agent]
   Sure! I will launch the setup assistant...
```

---

## Scenario 2: Build Requirements and Then Generate Application

### Agents Involved
- **Cyoda AI Assistant** (Main)
- **Cyoda Data Agent** (Sub-agent for entity/workflow management)
- **GitHub Agent** (Sub-agent for code generation)

### Tools Flow
1. `add_entity()` → Cyoda Data Agent.create_entity()
2. `add_workflow()` → Cyoda Data Agent.create_workflow()
3. `generate_application()` → GitHub Agent.generate_code_with_cli()

### Dialogue
```
U: Let's build requirements first. Add an entity for Product.

A: [Cyoda AI Assistant → add_entity() → Cyoda Data Agent]
   I'll create a Product entity for you...

U: Now add a workflow for Order Processing.

A: [Cyoda AI Assistant → add_workflow() → Cyoda Data Agent]
   I'll create the Order Processing workflow...

U: Now build the application from these requirements.

A: [Cyoda AI Assistant → generate_application() → GitHub Agent]
   I'll generate the application code...
```

---

## Scenario 3: Modify Existing Application

### Agents Involved
- **Cyoda AI Assistant** (Main)
- **GitHub Agent** (Sub-agent for code changes)
- **Cyoda Data Agent** (Sub-agent for entity/workflow updates)

### Tools Flow
1. `fetch_repository_content()` → GitHub Agent.get_file_content()
2. `update_entity()` → Cyoda Data Agent.modify_entity()
3. `generate_code_with_cli()` → GitHub Agent.generate_code_with_cli()

### Dialogue
```
U: Add a new entity to the existing application based on the attached branch.

A: [Cyoda AI Assistant → GitHub Agent.fetch_repository_content()]
   I'll fetch the current application structure...

A: [Cyoda AI Assistant → update_entity() → Cyoda Data Agent]
   I'll add the new entity...

A: [Cyoda AI Assistant → GitHub Agent.generate_code_with_cli()]
   I'll generate the updated code...
```

---

## Scenario 4: Answer Questions About Cyoda

### Agents Involved
- **Cyoda AI Assistant** (Main)
- **Knowledge Base Agent** (Sub-agent for documentation)

### Tools Flow
1. `search_knowledge_base()` → Knowledge Base Agent.search_documentation()
2. `answer_question()` → Direct response from Cyoda AI Assistant

### Dialogue
```
U: What is Cyoda?

A: [Cyoda AI Assistant → search_knowledge_base()]
   Cyoda is an event-driven application platform that...
```
