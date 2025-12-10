# Log Collection Fix - Deployment-Aware Time Ranges

## Problem Identified

In `troubleshooting_v2.md` dialogue (lines 105-174), the AI agent made a critical error when collecting logs after a redeployment:

### Timeline of the Issue:
1. **14:30** - New deployment starts (build_id: `baeba58e`)
2. **14:33** - User asks: "what is the logs status now"
3. **AI ERROR** - Queries logs from "last 15 minutes" → Gets logs from 14:18-14:33
4. **Problem** - 15 minutes includes the OLD deployment with old credentials
5. **Result** - AI reports errors from OLD deployment, confusing the user
6. **User correction** - "you take logs for 1h, but we need last 5 minutes"

## Root Cause

The agent used **fixed time ranges** (15m, 1h) without considering:
- When the NEW deployment started
- That logs from before the deployment are irrelevant
- Context: user just redeployed to fix credential issues

## Solution Implemented

### 1. Prompt Updates (environment_agent.template)

Added deployment-aware log collection rules (lines 280-343):

```markdown
**CRITICAL: Deployment-Aware Log Collection**

**Rule 1: Track deployment timestamps**
- Store deployment start time: ISO 8601 format (e.g., "2025-12-10T14:30:00Z")

**Rule 2: Use context-aware time ranges**
- Just deployed (< 5 min ago) → time_range="3m" OR since_timestamp=deployment_start
- After redeployment → since_timestamp=new_deployment_start
- General troubleshooting → time_range="15m"
- Historical analysis → time_range="1h"

**Rule 3: Decision logic**
When user asks "check logs" after deployment:
- Calculate: time_since_deployment = now - deployment_start
- If < 5 minutes → Use since_timestamp=deployment_start
- Else → Use time_range="15m"
```

### 2. Tool Enhancement (tools.py)

Updated `search_logs()` function (lines 2451-2633):

**New parameter:**
```python
since_timestamp: Optional[str] = None
# ISO 8601 timestamp (e.g., "2025-12-10T14:30:00Z")
# Gets logs ONLY after this timestamp
```

**Query logic:**
```python
if since_timestamp:
    # Use absolute timestamp - takes precedence over time_range
    es_query["query"]["bool"]["filter"].append({
        "range": {
            "@timestamp": {
                "gte": since_timestamp,
                "lte": "now"
            }
        }
    })
elif time_range:
    # Use relative time range
    es_query["query"]["bool"]["filter"].append({
        "range": {
            "@timestamp": {
                "gte": f"now-{time_range}",
                "lte": "now"
            }
        }
    })
```

**Result includes:**
```json
{
  "since_timestamp": "2025-12-10T14:30:00Z",
  "time_range": null,
  "logs": [...]
}
```

### 3. Summary Rule Added

Rule #9 in CRITICAL summary section:
```
9. Log Time Ranges: After deployment, use time_range="3m" or since_timestamp=deployment_start.
   DON'T use "15m" for new deployments.
```

## Expected Behavior After Fix

### Scenario: Redeployment with New Credentials

```
14:30 - Old deployment (client_id: ICxGbi) - AUTH ERRORS
14:35 - User provides new credentials (client_id: Sh3mdO)
14:36 - Redeployment starts (build_id: baeba58e)
14:39 - User: "what is the logs status now"

✅ CORRECT (After Fix):
AI tracks deployment_start = "2025-12-10T14:36:00Z"
AI calls: search_logs(env_name, app_name, since_timestamp="2025-12-10T14:36:00Z")
Returns: 35 logs from 14:36-14:39, all INFO, no errors
AI: "Logs from the last 3 minutes show no errors. App is healthy."

❌ WRONG (Before Fix):
AI calls: search_logs(env_name, app_name, time_range="15m")
Returns: 500 logs from 14:24-14:39, includes OLD deployment errors
AI: "Logs still show auth errors with client_id ICxGbi" ← STALE DATA!
```

## Testing Checklist

- [ ] Deploy app with wrong credentials → See errors in logs
- [ ] Provide correct credentials and redeploy
- [ ] Immediately ask "check logs" (within 3 minutes of deployment)
- [ ] Verify: Agent uses `since_timestamp=deployment_start_time`
- [ ] Verify: Only NEW deployment logs are returned
- [ ] Verify: Agent does NOT report errors from old deployment
- [ ] Test with 5+ minute delay: Agent should still use appropriate time range

## Benefits

1. **Accuracy** - Users get relevant logs from current deployment only
2. **Faster troubleshooting** - No confusion from stale error messages
3. **Better UX** - Agent appears more intelligent and context-aware
4. **Prevents false negatives** - Won't incorrectly report "still broken" when actually fixed
5. **Prevents false positives** - Won't incorrectly report "healthy" by ignoring recent errors

## Related Files

- `environment_agent.template` - Prompt rules
- `tools.py` - `search_logs()` function implementation
- `PROMPT_IMPROVEMENTS.md` - Full documentation of all improvements
- `troubleshooting_v2.md` - Original dialogue showing the issue
