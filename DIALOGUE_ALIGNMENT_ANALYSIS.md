# Dialogue Flow Alignment Analysis: build_app.md vs GitHub Agent Prompt

## Summary
The `build_app.md` dialogue flow and `github_agent.template` prompt are **MISALIGNED** in several critical areas. The dialogue is high-level and incomplete, while the prompt is detailed and specific.

## Key Misalignments

### 1. **Existing Branch Handling - PARTIAL ALIGNMENT**

**build_app.md says:**
- "If the user has an existing branch, setup the repository with the identified branch"
- "Then ask if the user wants to add any additional requirements, or attach files, or generate together requirements/entities/workflows"
- "Once the user confirms their requirement is complete, asks the user if the user wants to proceed building in editing mode (generate_application) or full new application mode, as their branch is not new. (generate_code_with_cli)"

**github_agent.template says (section 4.2):**
- **Mode 1 (Full New App):** `generate_application` - "build a solution that enables..."
- **Mode 2 (Incremental Change):** `generate_code_with_cli` - "Non-trivial, multiple files/logic: processors, criteria, dtos, classes"
- **Mode 3 (Simple File Write):** `save_file_to_repository` + `commit_and_push_changes` - "One-off, known content"
- **Mode 4 (Repo Analysis):** `analyze_repository_structure` / `execute_unix_command` - "Read-only operations"

**Issue:** The dialogue mentions asking users to choose between modes, but the GitHub agent prompt uses **automatic mode detection** based on user intent, not explicit user choice. The prompt decides which mode based on what the user asks for, not by asking the user which mode they want.

### 2. **New Branch Handling - INCOMPLETE**

**build_app.md says:**
- "If the user has no branch, first setup repository with a new branch"
- "Then explain the user how to use Canvas to work on entities/workflows/requirements"
- "Tell them you can generate requirements/entities/workflows and save them to the repository together"
- "Once the user identified the requirement as complete start building immediately"

**github_agent.template says:**
- After cloning new branch: "Return `create_open_canvas_tab_hook()` to open Canvas"
- "Inform user repo is ready" with paths
- "Provide GitHub URL"
- **Missing:** Explicit explanation of Canvas usage and how to work with entities/workflows/requirements

**Issue:** The prompt doesn't explicitly explain Canvas workflow as the dialogue suggests.

### 3. **Deployment Handling - PARTIAL ALIGNMENT**

**build_app.md says:**
- "start building immediately, offering the user to start deployment in the background"
- "suggest calling setup assistant once they see in the tasks panel that app building is complete"

**github_agent.template says:**
- "Then ask: 'Would you like to deploy the Cyoda environment in parallel with the build?'"
- **Missing:** Mention of suggesting calling setup assistant after build completes

**Issue:** The prompt asks about deployment but doesn't mention the setup assistant handoff.

### 4. **File Handling - MISSING FROM DIALOGUE**

**build_app.md says:**
- "If the user gives you any requirement in the forma or a file or textually - save to their branch immediately and return open canvas panel hook"
- "Also inform the user where in the current repository they can push their requirements files if they want to do it manually (provide a path)"

**github_agent.template says:**
- Doesn't explicitly mention handling file uploads or manual pushes
- Focuses on tool-based operations

**Issue:** The dialogue mentions file handling that isn't detailed in the prompt.
Agent must provide information about the repository structure, how it is structured (or refer to README file), where to put code, where to put requirement files.

## Coordinator-GitHub Agent Alignment

### CRITICAL ISSUE: Existing Branch Routing - RESOLVED

**Coordinator says (line 220):**
- "If user mentions existing branch name → **IMMEDIATELY** call transfer_to_agent("setup_agent") (NOT GitHub Agent!)"

**GitHub Agent says (section 4.3):**
- Handles existing branches directly: "Public + Existing Branch: ... ask user 'What is the branch name you want to use?' → Call `clone_repository(..., use_existing_branch=True)`"

**Setup Agent says (line 34-39):**
- "When transferring from GitHub Agent: GitHub Agent stores `language` and `branch_name` in `tool_context.state`"
- Setup Agent is for **AFTER** build completes, not for initial branch setup

**RESOLUTION:**
- **Coordinator routing is CORRECT**: Existing branch name → setup_agent (for editing existing apps)
- **GitHub Agent routing is CORRECT**: New branch → github_agent (for building new apps)
- **The distinction**:
  - User says "I'm working on branch X" → **github_agent** (clone repo and make incremental changes)
  - User says "build a solution that enables..." → **github_agent** (build new app)
  - User asks to "call setup assistant" or "how to run/launch the app" → **setup_agent** (guidance with launching the app)

### ALIGNMENT ISSUE: Build Mode Selection - AUTOMATIC vs EXPLICIT

**build_app.md says:**
- "asks the user if the user wants to proceed building in editing mode (generate_application) or full new application mode, as their branch is not new. (generate_code_with_cli)"
- Suggests **EXPLICIT user choice** between modes

**GitHub Agent says (section 4.2):**
- "If the user asks to build an application from scratch, use `generate_application()`. Otherwise, proceed to Step 4.4 (Incremental Changes)"
- Uses **AUTOMATIC mode detection** based on user intent:
  - "build a solution that enables..." → `generate_application` (Mode 1)
  - "Non-trivial, multiple files/logic" → `generate_code_with_cli` (Mode 2)
  - "One-off, known content" → `save_file_to_repository` (Mode 3)
  - "Read-only operations" → `analyze_repository_structure` (Mode 4)

**DIFFERENCE:**
- `build_app.md` expects agent to **ask user** which mode they want
- `github_agent.template` expects agent to **automatically detect** mode from user's request
- **This is a design difference, not a bug** - automatic detection is more user-friendly if the agent can reliably understand user intent
- **Status:** ACCEPTABLE - GitHub agent's automatic detection approach is valid

## Detailed Findings

### 1. Canvas Workflow - MISSING FROM GITHUB AGENT PROMPT

**build_app.md says:**
- "Then explain the user how to use Canvas to work on entities/workflows/requirements"
- "Tell them you can generate requirements/entities/workflows and save them to the repository together"

**github_agent.template says:**
- "Return `create_open_canvas_tab_hook()` to open Canvas"
- Missing: Explanation of Canvas workflow and how to use it

**Action:** Add Canvas explanation to GitHub agent prompt section 4.3 step 6

### 2. Setup Assistant Notification - MISSING FROM GITHUB AGENT PROMPT

**build_app.md says:**
- "Agent MUST let the user know - once the app is built they can call setup assistant"
- This is a MANDATORY notification, not optional

**github_agent.template says:**
- "Then ask: 'Would you like to deploy the Cyoda environment in parallel with the build?'"
- Missing: Mandatory notification about calling setup assistant after build completes

**Action:** Add mandatory setup assistant notification to GitHub agent prompt section 4.2 step 5
- Agent must inform user that once build is complete, they can call setup assistant for local development guidance

### 3. File Upload Handling - WRONG IMPLEMENTATION

**build_app.md says:**
- "If the user gives you any requirement in the forma or a file or textually - **save to their branch immediately** and return open canvas panel hook"
- "Also inform the user where in the current repository they can push their requirements files if they want to do it manually (provide a path)"

**Current Implementation (WRONG):**
- ❌ Files are saved INSIDE `generate_application()` via `retrieve_and_save_conversation_files()`
- ❌ This delays file saving until build starts
- ❌ Agent doesn't immediately save files when user provides them

**Correct Implementation Should Be:**
- ✅ Agent should IMMEDIATELY save files to repository when user provides them
- ✅ Files should be saved to functional requirements directory:
  - Python: `application/resources/functional_requirements/`
  - Java: `src/main/resources/functional_requirements/`
- ✅ Agent should return canvas hook after saving
- ✅ Agent should inform user about the requirements directory path
- ✅ Agent should explain where to manually push files if needed

**Action:** Update GitHub agent prompt to handle file uploads immediately
- Add logic to detect and save attached files immediately (not in generate_application)
- Use `retrieve_and_save_conversation_files()` when files are provided
- Return canvas hook after saving
- Inform user about functional requirements directory path

## Recommendations

### Priority 1: Update build_app.md (Dialogue Flow)
1. **Update coordinator routing section** - Clarify that "I'm working on branch X" routes to github_agent (not setup_agent)
   - setup_agent is only for "call setup assistant" or "how to launch/run the app"
2. **Update mode selection section** - Document that GitHub agent automatically detects mode based on user intent
   - Remove expectation of explicit user choice between modes
   - Update text to reflect automatic mode detection (generate_application, generate_code_with_cli, save_file, analyze)

### Priority 2: Update github_agent.template (Implementation)
1. **Add Canvas workflow explanation** - Explain how to use Canvas for entities/workflows/requirements
2. **Add mandatory setup assistant notification** - Agent MUST inform user that once build is complete, they can call setup assistant
3. **CRITICAL: Fix file upload handling** - Save files IMMEDIATELY when user provides them
   - ❌ **WRONG:** Currently saves files inside `generate_application()` (too late)
   - ✅ **CORRECT:** Should save files immediately when user provides them
   - **Implementation:**
     - Detect when user provides files (check Conversation.file_blob_ids)
     - Call `retrieve_and_save_conversation_files()` immediately
     - Return canvas hook after saving
     - Inform user about functional requirements directory path:
       - Python: `application/resources/functional_requirements/`
       - Java: `src/main/resources/functional_requirements/`
     - Explain where to manually push files if needed
4. **Clarify mode detection logic** - Add explicit decision tree for when each mode is used

### Priority 3: Alignment Verification
1. ✅ Coordinator routing is CORRECT - github_agent handles both new and existing branches
2. ✅ Setup agent receives correct context from GitHub agent
3. Test end-to-end flow: Coordinator → GitHub Agent → Setup Agent (when user asks for setup help)

