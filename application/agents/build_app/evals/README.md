# Build Agent Evaluation Tests

This directory contains evaluation tests for the Build Agent to ensure it handles various scenarios correctly.

## Eval Files

### 1. `pet_store_app.test.json`
**Scenario**: Building a pet store application with a private repository  
**Key Features**:
- Private repository setup with installation ID
- Full build lifecycle from request to completion
- Progress monitoring with multiple updates
- Transfer to post_build_setup agent after completion

**Expected Behavior**:
- User requests to build app → Agent asks public/private
- User chooses private → Agent provides setup instructions
- User provides credentials → Agent configures repository
- User says "Start building" → Agent executes build sequence
- Build completes → Agent transfers to setup agent

### 2. `error_handling.test.json`
**Scenario**: Testing error handling and context preservation  
**Key Features**:
- Tests explicit parameter passing when context might be lost
- Validates that tools can be called with explicit parameters
- Tests step-by-step progression with user confirmations

**Expected Behavior**:
- Agent handles missing context gracefully
- Tools accept explicit parameters (language, repository_path, branch_name)
- User can control progression with "Done, next ➡️" confirmations

### 3. `protected_branch.test.json`
**Scenario**: Testing protected branch validation  
**Key Features**:
- Ensures agent never uses protected branches (main, master, develop, etc.)
- Validates branch name generation using UUIDs
- Tests error handling for protected branch attempts

**Expected Behavior**:
- Agent always calls `generate_branch_uuid()` for branch names
- Agent rejects any attempt to use protected branches
- Clear error messages when protected branches are attempted

### 4. `data_ingestion_app.test.json` ⭐ NEW
**Scenario**: Building a data ingestion app with automatic build start  
**Key Features**:
- **Auto-start build**: Once sufficient information is gathered, build starts automatically
- No explicit "start building" command required from user
- Public repository setup (simpler flow)

**Expected Behavior**:
- User: "build a data ingestion app" → Agent: "public or private?"
- User: "python" → Agent: "public or private?" (clarifies if not answered)
- User: "public" → Agent: **Automatically starts build** (no waiting for "start building")
  - Calls `set_repository_config(repository_type="public")`
  - Calls `generate_branch_uuid()`
  - Calls `clone_repository()`
  - Calls `check_user_environment_status()`
  - Calls `generate_application()`
- Build progress updates → Agent acknowledges
- Build completes → Agent transfers to setup agent

**Key Difference from Other Evals**:
- ❌ OLD: User must explicitly say "start building" after repository setup
- ✅ NEW: Build starts automatically once language and repository type are known

## Required Changes to Build Agent

To support the auto-start behavior in `data_ingestion_app.test.json`, the following changes are needed in `application/agents/prompts/build_agent.template`:

### Current Behavior (Lines 86-121)
```markdown
### Step 3: Capture Private Repository Credentials (if private chosen)
...
- Wait for user to explicitly say to start building (e.g., "start building", "next", "proceed")

### Step 4: Clone Repository and Create Branch
When user confirms repository setup (says "start", "proceed", "next", etc.):
...

### Step 5: Wait for Build Command
Wait for user to explicitly say something like:
- "Start building the application"
- "Start building"
- "Begin the build"
- "I'm ready"
- "Build it"

**ONLY THEN proceed to Step 6**
```

### Proposed New Behavior
```markdown
### Step 3: Capture Repository Configuration

**If user chooses "public":**
- Call `set_repository_config(repository_type="public")`
- **Immediately proceed to Step 4** (auto-start build)

**If user chooses "private":**
- Provide setup instructions
- Wait for credentials
- Call `set_repository_config(repository_type="private", installation_id="...", repository_url="...")`
- **Immediately proceed to Step 4** (auto-start build)

### Step 4: Auto-Start Build Sequence
**Once repository configuration is complete, automatically start the build:**

**Step 4.1: Generate Branch UUID and Clone Repository**
- Call `generate_branch_uuid()` ONCE
- Call `clone_repository(language="python" or "java", branch_name=<branch_uuid>)` ONCE
- Show message: "Your [language] application to [requirements] is being set up using [public templates / your private repository]. 🚀"

**Step 4.2: Check Environment and Start Build**
- Call `check_user_environment_status()` ONCE
- Based on response, handle environment deployment if needed
- Call `generate_application(requirements=<user_requirements>, ...)` ONCE
- Show message: "✅ Your Cyoda environment deployment has started, and your application build is underway in the background. Stay tuned for updates! 🔔"

**CRITICAL CHANGE:**
- ❌ REMOVE: "Wait for user to say 'start building'"
- ✅ ADD: "Automatically start build once repository configuration is complete"
```

### Summary of Changes

1. **Remove Step 5** ("Wait for Build Command") entirely
2. **Modify Step 3** to immediately proceed to build after repository configuration
3. **Rename Step 4** to "Auto-Start Build Sequence"
4. **Update Step 6** references to Step 5 (renumber)
5. **Update all instructions** that mention "wait for user to say start building"

### Benefits of Auto-Start

1. **Fewer user interactions**: Reduces friction in the build process
2. **Faster time-to-build**: No waiting for explicit confirmation
3. **Better UX**: More natural conversation flow
4. **Consistent with user expectations**: When user provides all info, they expect action

### Backward Compatibility

The change is backward compatible because:
- Users who say "start building" will still work (build already started)
- The agent will acknowledge their message naturally
- No breaking changes to tool signatures or responses

## Running Evals

To run these evaluations:

```bash
# Run all build agent evals
python -m pytest application/agents/build_app/evals/

# Run specific eval
python -m pytest application/agents/build_app/evals/data_ingestion_app.test.json

# Run with verbose output
python -m pytest application/agents/build_app/evals/ -v
```

## Eval Configuration

See `test_config.json` for evaluation criteria:
- `tool_trajectory_avg_score`: Minimum average score for tool call accuracy (0.66)

## Adding New Evals

To add a new evaluation:

1. Create a new `.test.json` file following the structure of existing evals
2. Define the conversation flow with expected tool calls
3. Document the scenario in this README
4. Run the eval to ensure it passes

## Notes

- All evals use the same format: conversation turns with expected tool calls
- `intermediate_data.tool_uses` defines expected tool calls for each turn
- `final_response.parts[0].text` defines expected response patterns (partial match)
- Empty `tool_uses` array means no tools should be called in that turn

