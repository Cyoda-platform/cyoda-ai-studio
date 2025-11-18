# GitHub Agent Test Prompts - 100% Business Logic Coverage

## 📋 How to Read This Document

Each test case follows this format:

**Single Prompt Tests**:
- **Prompt**: What the user says (single message)
- **Expected Result**: What the agent should do (tool calls, responses, state changes)

**Multi-Step Conversation Tests**:
- **Conversation**: Full back-and-forth dialogue
- **User**: User's message
- **Agent**: Agent's response and actions
- **Expected Result**: Final outcome verification

**Key Principles**:
- ✅ If user provides all info in prompt, agent should NOT ask for it again
- ✅ If user is missing info, agent should ask specific questions
- ✅ Agent should detect keywords and context intelligently
- ✅ Async operations (builds, code gen) return immediately with task ID
- ✅ User can continue chatting during background operations

---

## Test Environment Setup
- **Prerequisites**: Clean conversation state, no existing branch configuration
- **Test User**: test.user@cyoda.com
- **Expected Response Time**: <2 seconds for tool calls, immediate return for async operations
- **Background Task Timeout**: 1800s (30 min) for builds, 3600s (60 min) for code generation

---

## 1. REPOSITORY CONFIGURATION TESTS

### 1.1 Public Repository Setup - Python (All Info Provided)
**Prompt**: "I want to work with a public repository for Python"

**Expected Result**:
- Agent detects "public" and "Python" keywords
- Agent calls `set_repository_config(repository_type="public")`
- Agent calls `generate_branch_uuid()` → returns UUID (e.g., "a1b2c3d4-...")
- Agent calls `clone_repository(language="python", branch_name="a1b2c3d4-...")`
- Success message: "✅ Repository configured! Branch: a1b2c3d4-... | Repository: https://github.com/Cyoda-platform/mcp-cyoda-quart-app"
- Conversation state updated with repository info

### 1.2 Public Repository Setup - Java (All Info Provided)
**Prompt**: "I want to build a Java application using public templates"

**Expected Result**:
- Agent detects "Java" and "public templates" keywords
- Agent calls `set_repository_config(repository_type="public")`
- Agent calls `generate_branch_uuid()` → returns UUID
- Agent calls `clone_repository(language="java", branch_name="<uuid>")`
- Success message with branch name and repository URL
- Conversation state updated with repository info

### 1.3 Public Repository Setup - Missing Language
**Prompt**: "I want to work with a public repository"

**Expected Result**:
- Agent detects "public" but no language specified
- Agent asks: "What programming language? (python or java)"
- User responds: "python"
- Agent calls `set_repository_config(repository_type="public")`
- Agent calls `generate_branch_uuid()` → returns UUID
- Agent calls `clone_repository(language="python", branch_name="<uuid>")`
- Success message with branch name and repository URL

### 1.4 Public Repository Setup - Missing Repository Type
**Prompt**: "I want to build a Python application"

**Expected Result**:
- Agent detects "Python" but no repository type specified
- Agent asks: "Do you want to work with a **public** or **private** repository?"
- User responds: "public"
- Agent calls `set_repository_config(repository_type="public")`
- Agent calls `generate_branch_uuid()` → returns UUID
- Agent calls `clone_repository(language="python", branch_name="<uuid>")`
- Success message with branch name and repository URL

### 1.5 Private Repository Setup - Complete Info
**Prompt**: "I want to use my private GitHub repository https://github.com/myorg/myrepo on branch feature/my-branch"

**Expected Result**:
- Agent detects "private", repository URL, and branch name
- Agent provides GitHub App installation instructions (if not already installed)
- Agent calls `set_repository_config(repository_type="private", repository_url="https://github.com/myorg/myrepo")`
- Agent calls `clone_repository(language="<auto-detected>", branch_name="feature/my-branch")`
- Success message with clone confirmation

### 1.6 Private Repository Setup - Missing Info
**Prompt**: "I want to use my private GitHub repository"

**Expected Result**:
- Agent provides GitHub App installation instructions
- Agent asks: "What's your repository URL?"
- User provides: "https://github.com/myorg/myrepo"
- Agent asks: "What branch do you want to work on?"
- User provides: "feature/my-branch"
- Agent calls `set_repository_config(repository_type="private", repository_url="https://github.com/myorg/myrepo")`
- Agent calls `clone_repository(language="<detected>", branch_name="feature/my-branch")`
- Success message with clone confirmation

### 1.7 Check Existing Branch Configuration
**Prompt**: "What branch am I working on?"

**Expected Result**:
- Agent calls `check_existing_branch_configuration()`
- If configured: Returns "You're working on branch 'feature/xyz' in repository 'https://github.com/org/repo'"
- If not configured: Returns "No branch configured yet. Would you like to set up a repository?"

### 1.8 Protected Branch Rejection
**Prompt**: "Clone the main branch"

**Expected Result**:
- Agent detects "main" is a protected branch
- Agent rejects with error message: "❌ Cannot use protected branch 'main'. Protected branches: main, master, develop, development, production, prod"
- Agent suggests: "Please use a feature branch instead, like 'feature/my-feature'"
- No clone operation performed

### 1.9 Existing Branch Setup - Public Repository (All Info Provided)
**Prompt**: "Please use my existing branch feature/customer-portal in the public Python repository"

**Expected Result**:
- Agent detects "existing branch" keyword
- Agent detects "public" and "Python" keywords
- Agent detects branch name "feature/customer-portal"
- Agent calls `set_repository_config(repository_type="public")`
- Agent calls `clone_repository(language="python", branch_name="feature/customer-portal", use_existing_branch=True)`
- Tool clones repository, fetches branches, checks out existing branch, pulls latest changes
- Success message: "✅ Repository configured! Branch: feature/customer-portal (existing branch) | Repository: https://github.com/Cyoda-platform/mcp-cyoda-quart-app"
- Conversation state updated with repository info

### 1.10 Existing Branch Setup - Public Repository (Step-by-Step)
**Conversation**:

**User**: "Please use my existing branch in this chat"

**Agent**:
- Detects "existing branch" keyword
- Asks: "Is this a **public** or **private** repository?"

**User**: "Public"

**Agent**:
- Asks: "What programming language is your project? (python or java)"

**User**: "Python"

**Agent**:
- Asks: "Perfect! What is the branch name you want to use?"

**User**: "feature/customer-portal"

**Agent Actions**:
- Calls `set_repository_config(repository_type="public")`
- Calls `clone_repository(language="python", branch_name="feature/customer-portal", use_existing_branch=True)`
- Responds: "✅ Repository configured successfully! Branch: feature/customer-portal (existing branch) | Your existing branch is now configured for this conversation."

**Expected Result**:
- Repository cloned to /tmp/cyoda_builds/feature/customer-portal
- Existing branch checked out with latest changes
- No new branch created
- No push to remote (since branch already exists)
- Conversation state updated

### 1.11 Existing Branch Setup - Private Repository (All Info Provided)
**Prompt**: "Configure my existing branch develop from my private repo https://github.com/acme/inventory-system, Java, installation ID 87654321"

**Expected Result**:
- Agent detects "existing branch" keyword
- Agent detects "private" repository
- Agent detects all required info: installation_id, repository_url, language, branch name
- Agent calls `set_repository_config(repository_type="private", installation_id="87654321", repository_url="https://github.com/acme/inventory-system")`
- Agent calls `clone_repository(language="java", branch_name="develop", use_existing_branch=True)`
- Tool clones repository with authentication, checks out existing branch
- Success message: "✅ Repository configured! Branch: develop (existing branch) | Repository: https://github.com/acme/inventory-system"
- Conversation state updated

### 1.12 Existing Branch Setup - Private Repository (Step-by-Step)
**Conversation**:

**User**: "Configure my existing branch from my private repo"

**Agent**:
- Detects "existing branch" and "private" keywords
- Provides GitHub App installation instructions
- Asks for: installation_id, repository_url, language, branch_name

**User**: "Installation ID is 87654321, repo is https://github.com/acme/inventory-system, Java, branch is develop"

**Agent Actions**:
- Calls `set_repository_config(repository_type="private", installation_id="87654321", repository_url="https://github.com/acme/inventory-system")`
- Calls `clone_repository(language="java", branch_name="develop", use_existing_branch=True)`
- Responds: "✅ Repository configured successfully! Branch: develop (existing branch) | Repository: acme/inventory-system"

**Expected Result**:
- Repository cloned with authentication
- Existing branch checked out
- Latest changes pulled from remote
- No new branch created
- Conversation state updated

### 1.13 Existing Branch - Branch Does Not Exist Error
**Prompt**: "Use my existing branch nonexistent-branch in the public Python repository"

**Expected Result**:
- Agent calls `set_repository_config(repository_type="public")`
- Agent calls `clone_repository(language="python", branch_name="nonexistent-branch", use_existing_branch=True)`
- Tool attempts to checkout branch but fails
- Tool returns error: "ERROR: Branch 'nonexistent-branch' does not exist in the repository. Please verify the branch name."
- Agent informs user: "❌ The branch 'nonexistent-branch' does not exist in the repository. Please check the branch name and try again."
- No repository configuration saved

---

## 2. MODE 1: BUILD COMPLETE APPLICATION TESTS

### 2.1 Build Python Application from Scratch (Repository Already Configured)
**Prompt**: "Build a complete customer management system with CRUD operations for customers, orders, and products"

**Expected Result**:
- Agent detects "build complete" scenario (keywords: "build", "complete", "system")
- Repository already configured from previous conversation
- Agent calls `generate_application(requirements="Build a complete customer management system with CRUD operations for customers, orders, and products", language="python")`
- Tool returns IMMEDIATELY (<1 second) with BackgroundTask ID
- Agent responds: "🏗️ Application build started! Task ID: task-abc123. This takes 10-30 minutes. I'll update you when complete. You can continue chatting."
- BackgroundTask entity created with:
  - status="running"
  - progress=0
  - task_type="build_app"
  - conversation_id linked
- Background monitoring process started
- User can send another message immediately (agent is not blocked)

### 2.2 Build Java Application from Scratch (No Repository Yet)
**Prompt**: "Generate a new Java application for inventory tracking with real-time stock updates and alerts"

**Expected Result**:
- Agent detects "generate new" + "Java" keywords
- No repository configured yet
- Agent asks: "Do you want to work with a **public** or **private** repository?"
- User responds: "public"
- Agent calls `set_repository_config(repository_type="public")`
- Agent calls `generate_branch_uuid()` → returns UUID
- Agent calls `clone_repository(language="java", branch_name="<uuid>")`
- Agent calls `generate_application(requirements="inventory tracking with real-time stock updates and alerts", language="java")`
- Tool returns IMMEDIATELY with BackgroundTask ID
- Agent responds with task ID and estimated time (10-30 minutes)
- BackgroundTask entity created
- Background monitoring started

### 2.3 Build with Minimal Requirements
**Prompt**: "Create a simple task management app"

**Expected Result**:
- Agent detects "create" + "app" keywords (MODE 1 scenario)
- If no language specified, agent asks: "What programming language? (python or java)"
- User responds: "python"
- Agent calls `generate_application(requirements="simple task management app", language="python")`
- Tool returns immediately with task ID
- BackgroundTask created
- Agent responds: "🏗️ Build started! Task ID: task-xyz789. Estimated time: 10-30 minutes."

### 2.4 Build Status Check During Build
**Prompt**: "What's the status of my build?"

**Expected Result**:
- Agent retrieves BackgroundTask ID from conversation.background_task_ids
- Agent queries BackgroundTask entity
- Agent responds with current status:
  - If running: "🔄 Build in progress: 45% complete, 12 minutes elapsed"
  - If completed: "✅ Build completed! Generated 47 files in 18 minutes"
  - If failed: "❌ Build failed: <error message>"
- Shows detailed metadata if available

### 2.5 Build Timeout Handling (Automated Test)
**Scenario**: Build runs for more than 30 minutes (1800 seconds)

**Expected Result**:
- Background monitor detects timeout after 1800 seconds
- Process killed gracefully using `process.kill()`
- BackgroundTask updated to:
  - status="failed"
  - progress=0
  - message="Build timeout after 1800 seconds"
  - metadata={"error": "timeout", "elapsed_time": 1800}
- No zombie processes left running

---

## 3. MODE 2: INCREMENTAL CODE GENERATION TESTS

### 3.1 Add Entity to Existing App
**Prompt**: "Add a Customer entity with id, name, email, and phone fields"

**Expected Result**:
- Agent detects incremental change scenario
- Agent calls `generate_code_with_cli(user_request="Add a Customer entity with id, name, email, and phone fields")`
- Tool returns IMMEDIATELY with BackgroundTask ID
- Agent responds: "🔧 Code generation started! Task ID: <task_id>. I'll update you when complete. You can continue chatting."
- BackgroundTask entity created
- Background monitoring started (30s-5min timeout)

### 3.2 Create Workflow for Entity
**Prompt**: "Create a workflow for Order entity with create, update, and cancel transitions"

**Expected Result**:
- Agent calls `generate_code_with_cli(user_request="Create a workflow for Order entity with create, update, and cancel transitions")`
- Tool returns immediately
- BackgroundTask created
- Workflow schema validation mentioned in response

### 3.3 Add Processor/Criteria
**Prompt**: "Add a processor to validate email format in Customer entity"

**Expected Result**:
- Agent calls `generate_code_with_cli(user_request="Add a processor to validate email format in Customer entity")`
- Tool returns immediately
- BackgroundTask created

### 3.4 Create REST Endpoints
**Prompt**: "Create REST endpoints for Product entity with GET, POST, PUT, DELETE operations"

**Expected Result**:
- Agent calls `generate_code_with_cli(user_request="Create REST endpoints for Product entity with GET, POST, PUT, DELETE operations")`
- Tool returns immediately
- BackgroundTask created

### 3.5 Modify Existing Code
**Prompt**: "Update the Customer entity to add an address field"

**Expected Result**:
- Agent calls `generate_code_with_cli(user_request="Update the Customer entity to add an address field")`
- Tool returns immediately
- BackgroundTask created

### 3.6 Code Generation Status Check
**Prompt**: "Is my code generation complete?"

**Expected Result**:
- Agent retrieves BackgroundTask from conversation state
- Shows progress (e.g., "85% complete, 2 minutes elapsed")
- If completed: shows changed files list

---

## 4. AGENTIC REPOSITORY ANALYSIS TESTS

### 4.1 Analyze Repository Structure
**Prompt**: "Analyze my repository structure"

**Expected Result**:
- Agent calls `analyze_repository_structure_agentic()`
- Uses Unix commands to explore repository
- Returns structured analysis with entities, workflows, requirements
- Shows file counts and organization

### 4.2 Find Specific Files
**Prompt**: "Find all workflow JSON files in my repository"

**Expected Result**:
- Agent calls `execute_unix_command("find . -path '*/workflow*' -name '*.json' | sort")`
- Returns list of workflow files with paths
- Explains what was found

### 4.3 Search for Patterns
**Prompt**: "Search for all entities that have a 'status' field"

**Expected Result**:
- Agent calls `execute_unix_command("grep -r 'status' --include='*.json' . | grep entity")`
- Returns matching files
- Explains the pattern found

### 4.4 Count Lines of Code
**Prompt**: "How many lines of Python code are in my repository?"

**Expected Result**:
- Agent calls `execute_unix_command("find . -name '*.py' -exec wc -l {} \\; | awk '{sum+=$1} END {print sum}'")`
- Returns total line count
- Shows breakdown by directory if requested

### 4.5 List Recently Modified Files
**Prompt**: "Show me files modified in the last 7 days"

**Expected Result**:
- Agent calls `execute_unix_command("find . -name '*.json' -mtime -7 -exec ls -lt {} \\;")`
- Returns list of recently modified files
- Shows modification timestamps

---

## 5. FILE OPERATIONS TESTS

### 5.1 Save Entity File
**Prompt**: "Save this Customer entity to my repository: {json content}"

**Expected Result**:
- Agent calls `get_entity_path(entity_name="Customer", version="1", project_type="python")`
- Agent calls `save_file_to_repository(file_path="<path>", content="{json}", commit_message="Add Customer entity")`
- File saved to correct path
- Auto-commit performed
- Success message with file path

### 5.2 Save Workflow File
**Prompt**: "Save this workflow for Order entity: {json content}"

**Expected Result**:
- Agent FIRST calls `execute_unix_command("cat <schema_path>")` to read workflow schema
- Agent validates workflow structure against schema
- Agent calls `get_workflow_path(entity_name="Order", project_type="python")`
- Agent calls `save_file_to_repository(file_path="<path>", content="{json}", commit_message="Add Order workflow")`
- File saved with schema validation
- Auto-commit performed

### 5.3 Save Functional Requirements
**Prompt**: "Save these requirements to my repository: {text content}"

**Expected Result**:
- Agent calls `get_requirements_path(project_type="python")`
- Agent calls `save_file_to_repository(file_path="<path>", content="{text}", commit_message="Add functional requirements")`
- File saved to requirements directory
- Auto-commit performed

### 5.4 Save Multiple Files
**Prompt**: "Save these 3 entity files: Customer, Order, Product"

**Expected Result**:
- Agent calls `save_file_to_repository()` 3 times
- Each file saved to correct entity path
- Single commit with all changes
- Success message listing all files

### 5.5 Save File with Custom Path
**Prompt**: "Save this config file to application/config/settings.json"

**Expected Result**:
- Agent calls `save_file_to_repository(file_path="application/config/settings.json", content="{json}")`
- File saved to exact path specified
- Auto-commit performed

---

## 6. GIT OPERATIONS TESTS

### 6.1 Commit and Push Changes
**Prompt**: "Commit my changes with message 'Added Customer entity'"

**Expected Result**:
- Agent calls `commit_and_push_changes(commit_message="Added Customer entity")`
- All staged changes committed
- Changes pushed to remote branch
- Success message with commit hash

### 6.2 Pull Latest Changes
**Prompt**: "Pull the latest changes from my branch"

**Expected Result**:
- Agent calls `pull_repository_changes()`
- Latest changes pulled from remote
- Merge conflicts reported if any
- Success message with updated files

### 6.3 Show Diff of Uncommitted Changes
**Prompt**: "Show me what files I've changed"

**Expected Result**:
- Agent calls `get_repository_diff()`
- Returns JSON with modified, added, untracked files
- Shows file paths and change types
- Formatted as readable list

### 6.4 Show Diff After Code Generation
**Prompt**: (After code generation completes) "What files were generated?"

**Expected Result**:
- Agent calls `get_repository_diff()`
- Shows all files created/modified by CLI
- Categorizes by type (entities, workflows, processors, etc.)
- Shows file count

---

## 7. PATH HELPER TESTS

### 7.1 Get Entity Path - Python
**Prompt**: "Where should I save the Customer entity in a Python project?"

**Expected Result**:
- Agent calls `get_entity_path(entity_name="Customer", version="1", project_type="python")`
- Returns: `application/entity/customer/version_1/customer.json`
- Explains the path structure

### 7.2 Get Entity Path - Java
**Prompt**: "Where should I save the Order entity in a Java project?"

**Expected Result**:
- Agent calls `get_entity_path(entity_name="Order", version="1", project_type="java")`
- Returns: `src/main/resources/example/config/entity/order/version_1/order.json`
- Explains the path structure

### 7.3 Get Workflow Path - Python
**Prompt**: "Where do workflows go in Python projects?"

**Expected Result**:
- Agent calls `get_workflow_path(entity_name="Customer", project_type="python")`
- Returns: `application/resources/workflow/Customer.json`
- Notes case-sensitivity requirement

### 7.4 Get Requirements Path
**Prompt**: "Where should I save functional requirements?"

**Expected Result**:
- Agent calls `get_requirements_path(project_type="python")`
- Returns: `application/resources/functional_requirements/`
- Explains this is where requirements documents go

---

## 8. CANVAS INTERACTION TESTS

### 8.1 Request Canvas Refresh
**Prompt**: "Refresh the canvas to show my latest changes"

**Expected Result**:
- Agent adds UI function: `{"function": "refresh_canvas"}`
- UI receives function and refreshes canvas
- User sees updated repository structure

### 8.2 Show Entity in Canvas
**Prompt**: "Show the Customer entity in the canvas"

**Expected Result**:
- Agent calls `execute_unix_command("cat <entity_path>")`
- Returns entity JSON content
- Agent adds UI function: `{"function": "show_entity", "entity_name": "Customer"}`
- Canvas highlights the entity

### 8.3 Show Workflow in Canvas
**Prompt**: "Display the Order workflow in the canvas"

**Expected Result**:
- Agent calls `execute_unix_command("cat <workflow_path>")`
- Returns workflow JSON content
- Agent adds UI function: `{"function": "show_workflow", "entity_name": "Order"}`
- Canvas shows workflow diagram

### 8.4 Show Diff in Canvas
**Prompt**: "Show my uncommitted changes in the canvas"

**Expected Result**:
- Agent calls `get_repository_diff()`
- Agent adds UI function: `{"function": "show_diff", "diff_data": {...}}`
- Canvas shows visual diff

### 8.5 Navigate to File in Canvas
**Prompt**: "Open application/entity/customer/version_1/customer.json in the canvas"

**Expected Result**:
- Agent adds UI function: `{"function": "navigate_to_file", "file_path": "application/entity/customer/version_1/customer.json"}`
- Canvas navigates to and highlights the file

---

## 9. CANVAS-TO-CHAT INTEGRATION TESTS

### 9.1 User Clicks Entity in Canvas
**Scenario**: User clicks on "Customer" entity in canvas file tree

**Canvas Action**: Sends message to chat: "Show me the Customer entity"

**Expected Result**:
- Agent receives message from canvas
- Agent calls `execute_unix_command("cat application/entity/customer/version_1/customer.json")`
- Agent responds with entity JSON content
- Agent explains entity structure (fields, types, validation)
- Canvas highlights the entity file

### 9.2 User Clicks Workflow in Canvas
**Scenario**: User clicks on "Order" workflow in canvas

**Canvas Action**: Sends message to chat: "Show me the Order workflow"

**Expected Result**:
- Agent receives message from canvas
- Agent calls `execute_unix_command("cat application/resources/workflow/Order.json")`
- Agent responds with workflow JSON content
- Agent explains workflow states and transitions
- Agent adds UI function: `{"function": "show_workflow", "entity_name": "Order"}`
- Canvas displays workflow diagram

### 9.3 User Clicks "Edit Entity" in Canvas
**Scenario**: User right-clicks Customer entity and selects "Edit"

**Canvas Action**: Sends message to chat: "I want to edit the Customer entity"

**Expected Result**:
- Agent responds: "What changes would you like to make to the Customer entity?"
- User responds: "Add an 'address' field"
- Agent calls `generate_code_with_cli(user_request="Add an address field to the Customer entity")`
- Agent responds: "🔧 Code generation started! Task ID: task-xyz. I'll update you when complete."
- When complete, canvas refreshes to show updated entity

### 9.4 User Clicks "Create Workflow" in Canvas
**Scenario**: User right-clicks Customer entity and selects "Create Workflow"

**Canvas Action**: Sends message to chat: "Create a workflow for Customer entity"

**Expected Result**:
- Agent calls `generate_code_with_cli(user_request="Create a workflow for Customer entity")`
- Agent responds: "🔧 Creating workflow for Customer entity. Task ID: task-abc."
- When complete, canvas shows new workflow file
- Agent adds UI function: `{"function": "show_workflow", "entity_name": "Customer"}`

### 9.5 User Clicks "View Diff" in Canvas
**Scenario**: User clicks "View Changes" button in canvas toolbar

**Canvas Action**: Sends message to chat: "Show me my uncommitted changes"

**Expected Result**:
- Agent calls `get_repository_diff()`
- Agent responds with list of changed files
- Agent adds UI function: `{"function": "show_diff", "diff_data": {...}}`
- Canvas displays visual diff with highlighted changes

### 9.6 User Clicks "Commit Changes" in Canvas
**Scenario**: User clicks "Commit" button in canvas toolbar

**Canvas Action**: Sends message to chat: "Commit my changes"

**Expected Result**:
- Agent asks: "What commit message would you like to use?"
- User responds: "Added Customer entity and workflow"
- Agent calls `commit_and_push_changes(commit_message="Added Customer entity and workflow")`
- Agent responds: "✅ Changes committed and pushed! Commit hash: abc123def"
- Canvas updates to show clean state (no uncommitted changes)

### 9.7 User Clicks File in Canvas File Tree
**Scenario**: User clicks on "customer_routes.py" in canvas file tree

**Canvas Action**: Sends message to chat: "Show me application/routes/customer_routes.py"

**Expected Result**:
- Agent calls `execute_unix_command("cat application/routes/customer_routes.py")`
- Agent responds with file content
- Agent explains what the file does (e.g., "This file defines REST endpoints for Customer entity")
- Canvas opens file in editor pane

### 9.8 User Drags File to Chat
**Scenario**: User drags "requirements.txt" from canvas to chat input

**Canvas Action**: Attaches file to conversation and sends message: "I've attached requirements.txt"

**Expected Result**:
- Agent acknowledges: "I see you've attached requirements.txt. Would you like me to save it to the repository?"
- User responds: "Yes, save it"
- Agent calls `save_file_to_repository(file_path="requirements.txt", content="<file_content>")`
- Agent responds: "✅ File saved to repository and committed"
- Canvas refreshes to show new file

### 9.9 User Selects Multiple Files in Canvas
**Scenario**: User selects 3 entity files in canvas and clicks "Analyze"

**Canvas Action**: Sends message to chat: "Analyze these entities: Customer, Order, Product"

**Expected Result**:
- Agent calls `execute_unix_command("cat <entity_path>")` for each entity
- Agent analyzes all 3 entities
- Agent responds with comparison:
  - Common fields across entities
  - Relationships between entities
  - Suggestions for improvements
- Canvas highlights the selected entities

### 9.10 User Clicks "Build App" in Canvas
**Scenario**: User clicks "Build Application" button in canvas (new conversation, no repo yet)

**Canvas Action**: Sends message to chat: "Build a new application"

**Expected Result**:
- Agent asks: "What type of application would you like to build?"
- User responds: "A customer management system"
- Agent asks: "Do you want to work with a **public** or **private** repository?"
- User responds: "public"
- Agent asks: "What programming language? (python or java)"
- User responds: "python"
- Agent configures repository and starts build
- Canvas shows progress indicator

### 9.11 User Clicks "Refresh" in Canvas
**Scenario**: User clicks refresh button in canvas toolbar

**Canvas Action**: Sends message to chat: "Refresh the canvas"

**Expected Result**:
- Agent calls `get_repository_diff()` to check for changes
- Agent responds: "✅ Canvas refreshed. Repository is up to date."
- Agent adds UI function: `{"function": "refresh_canvas"}`
- Canvas reloads file tree and shows latest state

### 9.12 User Right-Clicks Folder in Canvas
**Scenario**: User right-clicks "entity" folder and selects "Create New Entity"

**Canvas Action**: Sends message to chat: "Create a new entity"

**Expected Result**:
- Agent asks: "What should the entity be called and what fields should it have?"
- User responds: "Invoice entity with id, customerId, amount, date"
- Agent calls `generate_code_with_cli(user_request="Create Invoice entity with id, customerId, amount, date")`
- Agent responds: "🔧 Creating Invoice entity. Task ID: task-inv1."
- When complete, canvas shows new entity in folder

### 9.13 User Clicks "Deploy" in Canvas
**Scenario**: User clicks "Deploy to Environment" button in canvas

**Canvas Action**: Sends message to chat: "Deploy my application to Cyoda environment"

**Expected Result**:
- Agent recognizes deployment request
- Coordinator transfers to Environment Agent (seamless handoff)
- Environment Agent handles deployment
- Canvas shows deployment progress
- When complete, canvas shows deployment status

### 9.14 User Clicks Error in Canvas
**Scenario**: Canvas shows validation error on Customer.json, user clicks it

**Canvas Action**: Sends message to chat: "Fix the validation error in Customer entity: missing required field 'id'"

**Expected Result**:
- Agent understands the error context
- Agent calls `generate_code_with_cli(user_request="Fix Customer entity by adding required 'id' field")`
- Agent responds: "🔧 Fixing validation error in Customer entity. Task ID: task-fix1."
- When complete, canvas re-validates and shows no errors

### 9.15 User Clicks "Run Tests" in Canvas
**Scenario**: User clicks "Run Tests" button in canvas

**Canvas Action**: Sends message to chat: "Run the tests for my application"

**Expected Result**:
- Agent calls `execute_unix_command("pytest tests/ -v")` (for Python) or equivalent
- Agent responds with test results
- Agent shows: passed tests, failed tests, coverage percentage
- Canvas displays test results with pass/fail indicators

---

## 10. ERROR HANDLING TESTS

### 10.1 No Repository Configured
**Prompt**: "Show me my entities"

**Expected Result**:
- Agent detects no repository configured
- Agent responds: "You haven't configured a repository yet. Would you like to work with a public or private repository?"
- Guides user through setup

### 9.2 Invalid Branch Name
**Prompt**: "Clone branch 'main'"

**Expected Result**:
- Agent detects protected branch
- Agent responds: "ERROR: Cannot use protected branch 'main'. Please use a feature branch."
- No clone operation performed

### 9.3 File Not Found
**Prompt**: "Show me the NonExistent entity"

**Expected Result**:
- Agent calls `execute_unix_command("cat <path>")`
- Command returns error
- Agent responds: "File not found: <path>"
- Suggests checking repository structure

### 9.4 Git Operation Failure
**Prompt**: "Commit my changes"

**Expected Result** (if no changes):
- Agent calls `commit_and_push_changes()`
- Git returns "nothing to commit"
- Agent responds: "No changes to commit"

### 9.5 CLI Failure
**Prompt**: "Add an invalid entity"

**Expected Result**:
- Agent calls `generate_code_with_cli()`
- Background process fails
- BackgroundTask updated to status="failed"
- Error message with stderr output

---

## 11. WORKFLOW SCHEMA VALIDATION TESTS

### 11.1 Create Workflow Without Schema Check (Should Fail)
**Prompt**: "Save this workflow: {invalid json without reading schema}"

**Expected Result**:
- Agent MUST call `execute_unix_command("cat <schema_path>")` FIRST
- Agent validates structure
- If invalid: Agent responds with validation errors
- If valid: Agent saves file

### 10.2 Create Workflow With Schema Check (Should Succeed)
**Prompt**: "Create a workflow for Customer entity"

**Expected Result**:
- Agent calls `execute_unix_command("cat <schema_path>")` FIRST
- Agent reads schema structure
- Agent calls `generate_code_with_cli()` with schema context
- Workflow generated following schema

### 10.3 Validate Existing Workflow
**Prompt**: "Check if my Order workflow follows the schema"

**Expected Result**:
- Agent calls `execute_unix_command("cat <schema_path>")`
- Agent calls `execute_unix_command("cat <workflow_path>")`
- Agent compares structure
- Reports validation result

---

## 12. MULTI-STEP CONVERSATION TESTS

### 12.1 Complete Build Flow (Realistic)
**Conversation**:

**User**: "I want to build a new Python application for customer management"

**Agent**:
- Detects: "build new" + "Python" + "customer management"
- Asks: "Do you want to work with a **public** or **private** repository?"

**User**: "public"

**Agent**:
- Calls `set_repository_config(repository_type="public")`
- Calls `generate_branch_uuid()` → "a1b2c3d4-..."
- Calls `clone_repository(language="python", branch_name="a1b2c3d4-...")`
- Responds: "✅ Repository configured! Branch: a1b2c3d4-..."
- Asks: "Great! Can you provide more details about your customer management system requirements?"

**User**: "I need CRUD operations for customers, orders, and products with REST APIs"

**Agent**:
- Calls `generate_application(requirements="CRUD operations for customers, orders, and products with REST APIs", language="python")`
- Responds: "🏗️ Application build started! Task ID: task-abc123. This takes 10-30 minutes. You can continue chatting."

**User**: "What's the status?"

**Agent**:
- Queries BackgroundTask entity
- Responds: "🔄 Build in progress: 35% complete, 8 minutes elapsed"

**User**: (After 20 minutes) "Is it done yet?"

**Agent**:
- Queries BackgroundTask entity
- Responds: "✅ Build completed! Generated 47 files in 18 minutes. Files include: entities (Customer, Order, Product), workflows, processors, routes, and tests."

**User**: "Show me what was generated"

**Agent**:
- Calls `get_repository_diff()`
- Responds with list of all generated files categorized by type

**Expected Result**:
- ✅ Repository configured correctly
- ✅ Branch cloned successfully
- ✅ Application build started and completed
- ✅ Status checks work throughout
- ✅ Final diff shows all generated files
- ✅ User can chat during build

### 11.2 Incremental Development Flow (Realistic)
**Conversation**:

**User**: "Add a Customer entity with id, name, email, phone fields"

**Agent**:
- Detects incremental change (MODE 2)
- Calls `generate_code_with_cli(user_request="Add a Customer entity with id, name, email, phone fields")`
- Responds: "🔧 Code generation started! Task ID: task-xyz1. I'll update you when complete."

**User**: "Also create a workflow for Customer with create, update, delete transitions"

**Agent**:
- Calls `generate_code_with_cli(user_request="Create a workflow for Customer with create, update, delete transitions")`
- Responds: "🔧 Code generation started! Task ID: task-xyz2."

**User**: "Add a processor to validate email format in Customer entity"

**Agent**:
- Calls `generate_code_with_cli(user_request="Add a processor to validate email format in Customer entity")`
- Responds: "🔧 Code generation started! Task ID: task-xyz3."

**User**: "Show me all my changes"

**Agent**:
- Calls `get_repository_diff()`
- Responds: "📝 Changes:\n- Added: application/entity/customer/version_1/customer.json\n- Added: application/resources/workflow/Customer.json\n- Added: application/processors/customer_email_validator.py\n- Modified: application/routes/customer_routes.py"

**User**: "Commit everything with message 'Added Customer entity and workflow'"

**Agent**:
- Calls `commit_and_push_changes(commit_message="Added Customer entity and workflow")`
- Responds: "✅ Changes committed and pushed! Commit hash: abc123def"

**Expected Result**:
- ✅ Each code generation completes independently
- ✅ Multiple BackgroundTasks tracked
- ✅ Diff shows cumulative changes
- ✅ Single commit with all changes
- ✅ All files properly generated

### 11.3 Analysis and Modification Flow (Realistic)
**Conversation**:

**User**: "Analyze my repository structure"

**Agent**:
- Calls `analyze_repository_structure_agentic()`
- Uses Unix commands to explore
- Responds: "📊 Repository Analysis:\n- Language: Python\n- Entities: 3 (Customer, Order, Product)\n- Workflows: 3\n- Processors: 5\n- Routes: 4\n- Tests: 12"

**User**: "Find all entities"

**Agent**:
- Calls `execute_unix_command("find . -path '*/entity/*' -name '*.json' | sort")`
- Responds: "📁 Found 3 entities:\n- application/entity/customer/version_1/customer.json\n- application/entity/order/version_1/order.json\n- application/entity/product/version_1/product.json"

**User**: "Add a new Invoice entity with id, customerId, amount, date fields"

**Agent**:
- Detects incremental change
- Calls `generate_code_with_cli(user_request="Add a new Invoice entity with id, customerId, amount, date fields")`
- Responds: "🔧 Code generation started! Task ID: task-inv1."

**User**: (After 2 minutes) "Show the diff"

**Agent**:
- Calls `get_repository_diff()`
- Responds: "📝 Changes:\n- Added: application/entity/invoice/version_1/invoice.json\n- Added: application/routes/invoice_routes.py"

**Expected Result**:
- ✅ Repository analyzed correctly
- ✅ Entities listed accurately
- ✅ New entity generated
- ✅ Diff shows only new entity files
- ✅ No changes to existing entities

---

## 13. EDGE CASES AND BOUNDARY TESTS

### 12.1 Very Long Requirements
**Prompt**: "Build an application with {5000 character requirements}"

**Expected Result**:
- Agent accepts long requirements
- Passes to `generate_application()`
- Build starts successfully

### 12.2 Special Characters in File Names
**Prompt**: "Save entity with name 'Customer-Order_v2'"

**Expected Result**:
- Agent handles special characters
- File saved with sanitized name
- Success message

### 12.3 Concurrent Operations
**Prompts** (rapid fire):
1. "Add Customer entity"
2. "Add Order entity"
3. "Add Product entity"

**Expected Result**:
- Each operation creates separate BackgroundTask
- All tasks tracked in conversation
- No race conditions

### 12.4 Empty Repository
**Prompt**: "Analyze my repository" (on empty repo)

**Expected Result**:
- Agent detects empty repository
- Reports: "Repository is empty"
- Suggests building an application

### 12.5 Large File Operations
**Prompt**: "Save this 10MB JSON file"

**Expected Result**:
- Agent handles large file
- File saved successfully
- Commit may take longer but succeeds

---

## 14. LANGUAGE DETECTION TESTS

### 13.1 Auto-Detect Python
**Prompt**: "Add a Customer entity" (in Python repo)

**Expected Result**:
- Agent detects Python from repository structure
- Uses Python paths and conventions
- Code generated for Python

### 13.2 Auto-Detect Java
**Prompt**: "Create a workflow" (in Java repo)

**Expected Result**:
- Agent detects Java from repository structure
- Uses Java paths and conventions
- Code generated for Java

### 13.3 Explicit Language Override
**Prompt**: "Generate code for Java even though this is a Python repo"

**Expected Result**:
- Agent uses specified language
- Warns about mismatch if appropriate

---

## 15. BACKGROUND TASK MONITORING TESTS

### 14.1 Progress Updates
**Expected Behavior**:
- BackgroundTask updated every 30 seconds
- Progress percentage increases (0-95% during build, 100% on completion)
- Elapsed time tracked

### 14.2 Periodic Commits
**Expected Behavior**:
- Changes committed every 60 seconds during build
- Commit messages include progress info
- User can see incremental progress in GitHub

### 14.3 Final Commit
**Expected Behavior**:
- Final commit when build completes
- Commit message includes completion status
- All generated files included

### 14.4 Task Completion Notification
**Expected Behavior**:
- BackgroundTask status updated to "completed"
- Metadata includes: elapsed_time, changed_files, total_files
- User can query final status

---

## 16. INTEGRATION WITH OTHER AGENTS

### 15.1 Transfer to Environment Agent
**Prompt**: "Deploy my application to Cyoda environment"

**Expected Result**:
- GitHub agent recognizes deployment request
- Coordinator transfers to Environment Agent
- Environment Agent handles deployment

### 15.2 Transfer to Setup Agent
**Prompt**: "Configure my application settings"

**Expected Result**:
- GitHub agent recognizes setup request
- Coordinator transfers to Setup Agent
- Setup Agent handles configuration

### 15.3 Return from Other Agent
**Prompt**: (After deployment) "Show me my repository files"

**Expected Result**:
- Coordinator transfers back to GitHub Agent
- GitHub Agent shows repository structure
- Context preserved

---

## SUCCESS CRITERIA

✅ **All 26 test categories pass**
✅ **No errors in logs**
✅ **Response times < 2 seconds for synchronous operations**
✅ **Background tasks complete within expected timeframes**
✅ **All UI functions trigger correctly**
✅ **Canvas-to-chat integration works seamlessly**
✅ **Chat-to-canvas integration works seamlessly**
✅ **Repository state remains consistent**
✅ **No race conditions or deadlocks**
✅ **Proper error messages for all failure scenarios**
✅ **100% business logic coverage achieved**
✅ **Canvas interactions are intuitive and responsive**

---

---

## 17. USER FILE ATTACHMENT TESTS

### 16.1 Save Attached Files to Branch
**Prompt**: "Save these attached files to my repository" (with 3 files attached)

**Expected Result**:
- Agent calls `retrieve_and_save_conversation_files()`
- Files retrieved from conversation entity
- Files saved to functional_requirements directory
- All files committed and pushed
- Success message listing all saved files

### 16.2 Save Files Before Branch Exists
**Prompt**: (At conversation start with files attached) "Build an app"

**Expected Result**:
- Files stored temporarily (edge messages or artifacts)
- Branch created during build
- Agent calls `save_files_to_branch()` after branch exists
- Files saved to functional_requirements directory
- Files included in build context

### 16.3 Save Specific File Types
**Prompt**: "Save this requirements.txt file" (attached)

**Expected Result**:
- Agent detects file type
- Saves to appropriate directory
- Commits with descriptive message

---

## 18. REPOSITORY TYPE DETECTION TESTS

### 17.1 Detect Public Repository
**Prompt**: "What type of repository am I using?"

**Expected Result**:
- Agent checks conversation state
- Returns: "public" or "private"
- Shows repository URL and branch

### 17.2 Switch Repository Type
**Prompt**: "I want to switch to a private repository"

**Expected Result**:
- Agent warns about losing current work
- Asks for confirmation
- Reconfigures repository type
- Clones new repository

---

## 19. BRANCH MANAGEMENT TESTS

### 18.1 List Branches
**Prompt**: "Show me all branches in my repository"

**Expected Result**:
- Agent calls `execute_unix_command("git branch -a")`
- Lists all local and remote branches
- Highlights current branch

### 18.2 Switch Branch
**Prompt**: "Switch to branch 'feature/new-feature'"

**Expected Result**:
- Agent calls `execute_unix_command("git checkout feature/new-feature")`
- Branch switched
- Conversation state updated
- Success message

### 18.3 Create New Branch
**Prompt**: "Create a new branch called 'feature/customer-entity'"

**Expected Result**:
- Agent calls `execute_unix_command("git checkout -b feature/customer-entity")`
- New branch created
- Conversation state updated
- Success message

---

## 20. ADVANCED UNIX COMMAND TESTS

### 19.1 Complex Grep Pattern
**Prompt**: "Find all entities that have both 'email' and 'phone' fields"

**Expected Result**:
- Agent calls `execute_unix_command("grep -l 'email' --include='*.json' . | xargs grep -l 'phone'")`
- Returns matching entity files
- Explains the pattern

### 19.2 File Size Analysis
**Prompt**: "Show me the largest JSON files in my repository"

**Expected Result**:
- Agent calls `execute_unix_command("find . -name '*.json' -exec ls -lh {} \\; | sort -k5 -hr | head -10")`
- Returns top 10 largest files
- Shows file sizes

### 19.3 Dependency Analysis
**Prompt**: "Find all files that import the Customer entity"

**Expected Result**:
- Agent calls `execute_unix_command("grep -r 'Customer' --include='*.py' --include='*.java' .")`
- Returns files with imports
- Shows usage context

### 19.4 Code Statistics
**Prompt**: "Give me statistics about my codebase"

**Expected Result**:
- Agent runs multiple commands:
  - `find . -name '*.py' | wc -l` (Python files)
  - `find . -name '*.json' | wc -l` (JSON files)
  - `find . -name '*.py' -exec wc -l {} \\; | awk '{sum+=$1} END {print sum}'` (Total lines)
- Returns comprehensive statistics

---

## 21. PERFORMANCE AND STRESS TESTS

### 20.1 Large Repository Analysis
**Prompt**: "Analyze repository with 1000+ files"

**Expected Result**:
- Agent handles large repository
- Commands complete within reasonable time
- Results properly formatted

### 20.2 Multiple Concurrent Builds
**Prompt**: Start 3 builds simultaneously

**Expected Result**:
- Each build gets separate BackgroundTask
- All tasks tracked in conversation.background_task_ids
- No interference between builds
- All complete successfully

### 20.3 Rapid-Fire Commands
**Prompts** (sent within 5 seconds):
1. "Show diff"
2. "List entities"
3. "Commit changes"
4. "Pull updates"
5. "Show status"

**Expected Result**:
- All commands execute successfully
- No race conditions
- Responses in correct order

---

## 22. SECURITY AND VALIDATION TESTS

### 21.1 Path Traversal Prevention
**Prompt**: "Save file to ../../etc/passwd"

**Expected Result**:
- Agent detects path traversal attempt
- Rejects with security error
- No file saved outside repository

### 21.2 Command Injection Prevention
**Prompt**: "Run command: ls; rm -rf /"

**Expected Result**:
- Agent sanitizes command
- Only safe commands executed
- Dangerous commands blocked

### 21.3 Large File Upload Prevention
**Prompt**: "Save 100MB file"

**Expected Result**:
- Agent checks file size
- Warns if too large
- May reject or handle appropriately

---

## 23. CONVERSATION STATE PERSISTENCE TESTS

### 22.1 Resume After Disconnect
**Scenario**: User disconnects during build, reconnects later

**Expected Result**:
- Conversation state preserved
- BackgroundTask status retrievable
- User can check build progress
- No data loss

### 22.2 Multiple Conversations
**Scenario**: User has 3 conversations with different branches

**Expected Result**:
- Each conversation has separate state
- Repository info isolated per conversation
- No cross-contamination

### 22.3 State Recovery After Error
**Scenario**: Error occurs during operation

**Expected Result**:
- Conversation state remains consistent
- Partial changes rolled back if needed
- User can retry operation

---

## 24. CLI INTEGRATION TESTS

### 23.1 CLI Script Execution
**Expected Behavior**:
- Script located at `application/agents/build_app/augment_build.sh`
- Script executed with correct parameters
- Environment variables passed correctly
- Output captured and logged

### 23.2 CLI Prompt Loading
**Expected Behavior**:
- Python prompts loaded from `build_python_instructions.template`
- Java prompts loaded from `build_java_instructions.template`
- Prompts include codebase patterns
- Prompts passed to CLI

### 23.3 CLI Process Monitoring
**Expected Behavior**:
- Process PID tracked
- Output streamed to logs
- Progress updates every 10 seconds
- Timeout enforced (1800s for builds, 3600s for code gen)

---

## 25. GITHUB APP AUTHENTICATION TESTS

### 24.1 Public Repository Authentication
**Expected Behavior**:
- Uses GITHUB_PUBLIC_REPO_INSTALLATION_ID from .env
- Installation token retrieved
- Token used for git operations
- Token refreshed if expired

### 24.2 Private Repository Authentication
**Expected Behavior**:
- Uses user-provided installation ID
- Installation token retrieved
- Token used for git operations
- Proper error if installation not found

### 24.3 Token Expiration Handling
**Expected Behavior**:
- Detects expired token
- Automatically refreshes token
- Retries operation with new token
- No user intervention needed

---

## 26. CANVAS UI FUNCTION TESTS

### 25.1 Refresh Canvas Function
**Expected UI Function**:
```json
{
  "function": "refresh_canvas",
  "timestamp": "2025-11-17T10:30:00Z"
}
```

**UI Behavior**:
- Canvas reloads repository structure
- Shows latest files
- Updates file tree

### 25.2 Show Entity Function
**Expected UI Function**:
```json
{
  "function": "show_entity",
  "entity_name": "Customer",
  "file_path": "application/entity/customer/version_1/customer.json"
}
```

**UI Behavior**:
- Canvas navigates to entity file
- Highlights entity in tree
- Opens entity editor

### 25.3 Show Workflow Function
**Expected UI Function**:
```json
{
  "function": "show_workflow",
  "entity_name": "Order",
  "file_path": "application/resources/workflow/Order.json"
}
```

**UI Behavior**:
- Canvas shows workflow diagram
- Displays states and transitions
- Allows visual editing

### 25.4 Show Diff Function
**Expected UI Function**:
```json
{
  "function": "show_diff",
  "diff_data": {
    "modified": ["file1.py", "file2.json"],
    "added": ["file3.py"],
    "untracked": ["file4.json"]
  }
}
```

**UI Behavior**:
- Canvas shows visual diff
- Highlights changed files
- Shows line-by-line changes

### 25.5 Navigate to File Function
**Expected UI Function**:
```json
{
  "function": "navigate_to_file",
  "file_path": "application/entity/customer/version_1/customer.json"
}
```

**UI Behavior**:
- Canvas navigates to file
- Opens file in editor
- Scrolls to file in tree

### 25.6 Show Build Progress Function
**Expected UI Function**:
```json
{
  "function": "show_build_progress",
  "task_id": "task-123",
  "progress": 45,
  "status": "running",
  "elapsed_time": 720
}
```

**UI Behavior**:
- Shows progress bar
- Displays elapsed time
- Updates in real-time

---

## TESTING NOTES

- Run tests in isolated environment
- Use test repositories (not production)
- Monitor `app_log.log` for errors
- Verify BackgroundTask entities in Cyoda
- Check GitHub commits after each operation
- Test canvas UI functions manually
- Verify conversation state persistence
- Test with both Python and Java projects
- Verify all async operations return immediately
- Check background task monitoring works correctly
- Validate workflow schema enforcement
- Test error recovery mechanisms
- Verify security validations
- Test with various file sizes and types
- Verify concurrent operation handling

