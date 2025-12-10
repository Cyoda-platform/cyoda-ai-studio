# Missing UI Hooks Issue - Critical UX Problem

## Problem Identified

In the latest dialogue, the AI agent missed **3 critical opportunities** to present UI hooks, instead listing options as plain text. This forces users to type their choices instead of clicking buttons, creating poor UX and increased friction.

## Specific Failures

### ❌ Failure 1: After Deployment Starts (14:22)

**What AI said:**
```
Deployment started.
Build ID: f13322b2...
Great — deployment is running (estimated 3–5 minutes).
Would you like me to show build status now?
```

**What AI should have done:**
```python
# After returning build info, IMMEDIATELY call:
show_deployment_options(
    question=f"Build {build_id} started (3-5 min). What would you like to do?",
    options=[
        {"value": "view_status", "label": "🚀 View build status",
         "description": f"Check progress for build {build_id}"},
        {"value": "issue_creds", "label": "🔐 Issue credentials",
         "description": "Create M2M credentials for this environment"},
        {"value": "list_apps", "label": "📦 List apps",
         "description": "Show all apps in production"},
        {"value": "open_cloud", "label": "☁️ Open cloud panel",
         "description": "View environment in cloud panel"}
    ]
)
```

**Impact:** User had to type "yes" instead of clicking a button.

---

### ❌ Failure 2: After Build Completes (14:22)

**What AI said:**
```
Build f13322b2... finished — SUCCESS.

Your app should be available in the production environment.
Would you like me to:
- show application details,
- list app pods,
- fetch recent logs,
- or provide the app URL?
```

**What AI should have done:**
```python
# IMMEDIATELY call:
show_deployment_options(
    question=f"Build {build_id} finished - SUCCESS. Next step?",
    options=[
        {"value": "show_details", "label": "📋 Show app details",
         "description": "View deployment details for my-app-v1"},
        {"value": "list_pods", "label": "🗂️ List pods",
         "description": "Show pod status in production"},
        {"value": "fetch_logs", "label": "📄 Fetch recent logs",
         "description": "View last 15 minutes of logs"},
        {"value": "get_url", "label": "🔗 Get app URL",
         "description": "Get the application endpoint URL"}
    ]
)
```

**Impact:** User had to type "there are errors in the app" instead of clicking "Fetch recent logs" button.

---

### ❌ Failure 3: After Finding Log Errors (14:24)

**What AI said:**
```
Logs show repeated auth failures: "invalid_client: M2M client ... not found".
Pod is Running.

Next steps I can take for you (select one):
- Issue new M2M credentials and redeploy the app with them (recommended)
- Redeploy app with the same credentials (may fail)
- Show more logs
- List app pods

Which would you like? (I'll act as soon as you choose.)
```

**What AI should have done:**
```python
# IMMEDIATELY call:
show_deployment_options(
    question="Found auth error: invalid_client with ID ICxGbi. How should I proceed?",
    options=[
        {"value": "issue_redeploy", "label": "🔐 Issue new credentials & redeploy (Recommended)",
         "description": "Create new M2M credentials and redeploy my-app-v1"},
        {"value": "redeploy_same", "label": "🔄 Redeploy with same credentials",
         "description": "Retry deployment (may fail if creds are wrong)"},
        {"value": "show_more_logs", "label": "🔍 View detailed logs",
         "description": "Show more log entries with full error details"},
        {"value": "list_pods", "label": "📦 List app pods",
         "description": "Check pod status and resource usage"}
    ]
)
```

**Impact:** User had to type full response "Issue new M2M credentials and redeploy the app with them (recommended)" instead of clicking a button.

---

## Root Cause Analysis

### Why the AI is not using hooks:

1. **Prompt not explicit enough** - The agent doesn't recognize these as "predefined options"
2. **Natural language default** - The LLM defaults to conversational text instead of tool calls
3. **Missing trigger patterns** - Agent doesn't have clear "if-then" rules for when to call the tool
4. **Examples needed** - Prompt needs concrete code examples showing EXACTLY when to call show_deployment_options

## Solution Implemented

### 1. Added Mandatory Hook Triggers (Lines 80-85)

```markdown
**Mandatory hook triggers:**
- "Would you like me to..." → STOP, call show_deployment_options
- "Next steps: A, B, C" → STOP, call show_deployment_options
- "Choose one: X, Y, Z" → STOP, call show_deployment_options
- After deployment completes → IMMEDIATELY call show_deployment_options
- After finding errors in logs → IMMEDIATELY call show_deployment_options
```

### 2. Added Explicit Examples (Lines 362-415)

Provided **5 complete code examples** showing exactly when and how to call `show_deployment_options`:
1. After deployment starts
2. After build completes
3. After finding errors in logs
4. After user provides credentials
5. When asking "Would you like..."

### 3. Strengthened Rule #2 (Lines 73-85)

Added explicit prohibitions:
- ❌ NEVER ask: "Would you like me to X or Y?" without a hook
- ❌ NEVER say: "Which would you like?" followed by text list
- ✅ ALWAYS call show_deployment_options for ANY question with 2+ predefined answers

### 4. Updated Summary Rules

Added Rule #2: **NEVER TEXT OPTIONS**
```
If you're about to type "Would you like..." or "Choose one:"
→ STOP and call show_deployment_options instead.
```

---

## Expected Behavior After Fix

### Scenario: Successful Deployment

```
User: "my-app-v1"

AI: [calls deploy_user_application()]
AI: "Deployment started. Build ID: f13322b2..."
AI: [IMMEDIATELY calls show_deployment_options with 4 options]
User: [CLICKS "🚀 View build status" button]

AI: "Build finished - SUCCESS"
AI: [IMMEDIATELY calls show_deployment_options with 4 options]
User: [CLICKS "📄 Fetch recent logs" button]

AI: "Found auth error: invalid_client"
AI: [IMMEDIATELY calls show_deployment_options with 4 options]
User: [CLICKS "🔐 Issue new credentials & redeploy (Recommended)" button]
```

**No typing required from the user except for free-form input like app names or credentials.**

---

## Testing Checklist

- [ ] Deploy an app → Verify hook appears after "deployment started" message
- [ ] Wait for build to complete → Verify hook appears after "build finished - SUCCESS"
- [ ] Trigger an error (wrong creds) → Verify hook appears after "found error in logs"
- [ ] Provide credentials → Verify hook appears with "Redeploy now (Recommended)"
- [ ] At NO point should the agent ask "Would you like..." or "Choose one:" in plain text

---

## Impact

**Before fix:**
- 3 missed hook opportunities per deployment flow
- User must type responses for every decision point
- Slower interaction, more typing, higher friction
- Poor UX compared to clickable buttons

**After fix:**
- Hook presented at EVERY decision point
- User clicks buttons instead of typing
- Faster interaction, better engagement
- Modern UX with interactive elements

---

## Related Files

- `environment_agent.template` - Lines 73-85, 356-415, 448
- `PROMPT_IMPROVEMENTS.md` - Full documentation
- `show_deployment_options` tool in `tools.py` - Already implemented correctly

---

## Key Insight

**The problem is not the tool** - `show_deployment_options` works perfectly.

**The problem is the agent not calling it** - The LLM defaults to natural language responses instead of tool calls.

**The solution is explicit triggers** - The prompt must say "when you see X, immediately call Y" with concrete examples.
