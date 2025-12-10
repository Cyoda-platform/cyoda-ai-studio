# Environment Agent Prompt Improvements

Based on analysis of troubleshooting dialogue feedback, the following improvements have been made to optimize agent behavior and reduce hallucinations.

## Changes Made

### 1. Implicit Confirmation Rules (Lines 17-21)
**Problem:** Agent was asking for redundant confirmations even when user implicitly agreed.

**Solution:** Added explicit rules:
- If user says "deploy to production" → env_name = "production" (confirmed)
- If user provides app_name next → proceed without re-confirming env_name
- Only re-confirm for: destructive actions, first mention, or ambiguous input

**Impact:** Reduces conversation friction, makes agent feel more intelligent.

---

### 2. Mandatory Hook Usage for Options (Lines 73-76)
**Problem:** Agent listed options as text instead of showing clickable buttons.

**Solution:**
- ❌ NEVER list options as text: "1) option A, 2) option B"
- ✅ ALWAYS call `show_deployment_options()` to show clickable UI
- Exception: Only free-form input (repo URLs, custom names)

**Impact:** Better UX, prevents user from having to type option choices.

---

### 3. Context-Aware Hook Descriptions (Lines 78-81)
**Problem:** Generic descriptions like "Check current build progress" without specifics.

**Solution:** Always include context:
- ❌ Generic: "Check current build progress"
- ✅ Specific: "Check build progress for build_id: f8fdad4a in production"
- Required elements: build_id, env_name, app_name, timestamps, status

**Impact:** User knows exactly what they're clicking on, better transparency.

---

### 4. Tool Capability Constraints (Lines 146-170)
**Problem:** Agent suggested kubectl commands it cannot execute.

**Solution:** Clear capability boundaries:
- ✅ CAN: View logs, check status, restart apps, redeploy, issue credentials
- ❌ CANNOT: Execute kubectl, patch secrets, SSH to pods, modify YAML

**Troubleshooting Rules:**
- When logs show credential errors → Suggest ONLY tool-based solutions
- ❌ Don't suggest: "Run kubectl patch secret..."
- ✅ Do suggest: "🔐 Issue new credentials - I'll create and redeploy"

**Impact:** Prevents agent from hallucinating capabilities, sets correct expectations.

---

### 5. Proactive Hook Presentation (Lines 301-337)
**Problem:** Agent waited for user to ask "what next?" instead of proactively showing options.

**Solution:** ALWAYS show hooks at these moments:
1. **After deployment starts** → Show "View build status", "Issue credentials", etc.
2. **After finding errors in logs** → Show "Issue new credentials", "Redeploy", "View logs"
3. **After user provides credentials** → Show "🚀 Redeploy now (Recommended)" immediately
4. **When asking for confirmation** → Show options: "production", "dev", "staging", "custom"

**Impact:** Smoother conversation flow, less back-and-forth, better guidance.

---

### 6. Credential Handling Workflow (Line 168-170)
**Problem:** Agent explained what to do instead of immediately offering to do it.

**Solution:**
- When user provides credentials → Immediately call `show_deployment_options` with "Redeploy now" option
- Don't wait for user to ask "can you redeploy"
- Don't explain manual kubectl steps

**Impact:** Faster resolution, more proactive assistance.

---

### 7. Concise Summary Rules (Lines 350-359)
**Problem:** Long prompt led to inconsistent behavior and hallucinations.

**Solution:** Added 8-point summary of critical rules at the end:
1. Hooks (tools create them)
2. No re-confirmation (implicit agreement)
3. Context in hooks (build_id, env_name, etc.)
4. Troubleshooting (only tool-based solutions)
5. Proactive hooks (show immediately)
6. Credentials (immediate redeploy option)
7. Status checks (always call check_environment_exists)
8. Monitoring (direct to Tasks window)

**Impact:** LLM can quickly reference key constraints, reduces hallucinations.

---

### 8. Deployment-Aware Log Collection (Lines 280-343, NEW)
**Problem:** Agent used fixed time ranges (15m, 1h) for log queries after redeployment, retrieving stale logs from previous deployment.

**Solution:** Added deployment-aware log collection logic:

**Rule 1: Track deployment timestamps**
- Store deployment start time when calling `deploy_user_application()`
- Format: ISO 8601 timestamp (e.g., "2025-12-10T14:30:00Z")

**Rule 2: Use context-aware time ranges**
- ❌ DON'T use fixed "15m" or "1h" for newly deployed apps
- ✅ DO use:
  - Just deployed (< 5 min ago) → `time_range="3m"` or `since_timestamp=deployment_start`
  - After redeployment → `since_timestamp=new_deployment_start` to avoid old logs
  - General troubleshooting → `time_range="15m"`

**Rule 3: Example**
```
14:30 - Deployment starts (build_id: abc123)
14:33 - User: "check logs"
AI: search_logs(env_name, app_name, since_timestamp="2025-12-10T14:30:00Z")
→ Gets only logs from NEW deployment, not old ones ✅
```

**Tool Enhancement:**
- Added `since_timestamp` parameter to `search_logs()` function
- `since_timestamp` takes precedence over `time_range`
- Elasticsearch query uses absolute timestamp: `"gte": since_timestamp`

**Impact:** Prevents confusion from stale logs, provides accurate troubleshooting data.

---

## Testing Recommendations

### Test Case 1: Deployment with Implicit Confirmation
```
User: "deploy to production"
Agent: [shows hook asking for app_name - no re-confirmation of "production"]
User: "name = my-app"
Agent: [deploys immediately without asking "confirm production?"]
```

### Test Case 2: No Manual kubectl Suggestions
```
User: "my app is not running"
Agent: [checks logs, finds credential error]
Agent: [shows hook with ONLY tool-based solutions:]
  - 🔐 Issue new credentials
  - 🚀 Redeploy with your credentials
  - 🔍 View detailed logs
  - 📚 Ask QA agent
[MUST NOT suggest: "run kubectl patch secret..."]
```

### Test Case 3: Proactive Hook After Credentials
```
User: "use these creds: CLIENT_ID=abc, CLIENT_SECRET=xyz"
Agent: [immediately shows hook:]
  - 🚀 Redeploy now (Recommended)
  - 🔐 Use platform credentials instead
  - ❌ Cancel
[MUST NOT wait for user to ask "can you redeploy"]
```

### Test Case 4: Context-Aware Hook Descriptions
```
After deployment starts:
Hook description: "Check build progress for build_id: f8fdad4a in production"
NOT: "Check current build progress"
```

### Test Case 5: Deployment-Aware Log Collection
```
Scenario:
14:30 - Old deployment with wrong credentials (client_id: ICxGbi)
14:35 - User provides new credentials (client_id: Sh3mdO)
14:36 - New deployment starts (build_id: baeba58e, timestamp: 2025-12-10T14:36:00Z)
14:39 - User: "what is the logs status now"

Expected AI behavior:
AI: [calls search_logs(env_name="prod", app_name="my-app", since_timestamp="2025-12-10T14:36:00Z")]
Result: Returns only logs from NEW deployment (14:36 onwards)
AI: "Logs from the last 3 minutes show no errors. App is healthy."

MUST NOT:
AI: [calls search_logs(time_range="15m")] ❌
Result: Returns logs from 14:24-14:39, includes OLD deployment errors
AI: "Logs still show auth errors with client_id ICxGbi" ❌ WRONG!
```

---

## Files Modified

1. **environment_agent.template** (Lines 17-21, 66-87, 140-170, 280-343, 396-406)
   - Added implicit confirmation rules
   - Strengthened hook usage requirements
   - Added troubleshooting capability constraints
   - Added proactive hook presentation rules
   - Added deployment-aware log collection rules (NEW)
   - Added concise summary section

2. **coordinator.template** (No changes needed)
   - Already properly delegates to environment agent
   - Already has correct transfer rules

3. **tools.py** (Lines 2451-2491, 2533-2569, 2626-2627)
   - `show_deployment_options` already supports all required patterns
   - **Updated `search_logs` function** to support `since_timestamp` parameter
   - Added logic to prioritize `since_timestamp` over `time_range`
   - Returns `since_timestamp` in result summary

---

## Prompt Optimization Notes

**Why these changes reduce hallucinations:**

1. **Explicit constraints** - Clear ✅/❌ examples prevent agent from inventing capabilities
2. **Structured rules** - Numbered lists and bullet points are easier for LLMs to parse
3. **Concise summary** - 8-point summary at end reinforces key behaviors
4. **Context requirements** - Forcing specific details (build_id, env_name) prevents generic responses
5. **Proactive triggers** - "ALWAYS show hooks at these moments" prevents waiting/asking

**Token efficiency:**
- Removed redundant explanations
- Used tables and bullets instead of paragraphs
- Added summary section to reinforce without repetition
- Total prompt remains under 3000 tokens (optimized for context window)
