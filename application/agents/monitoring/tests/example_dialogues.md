# Monitoring Agent - Example Dialogues

## Overview
The Monitoring Agent is a specialized LoopAgent that continuously monitors Cyoda environment deployments, providing real-time status updates until deployment completes or fails.

## Architecture
The Monitoring Agent uses a LoopAgent pattern with two sub-agents:
- **deployment_status_checker** - Checks deployment status and decides whether to continue
- **deployment_status_waiter** - Waits 30 seconds between checks

## Available Tools
- `check_deployment_and_decide` - Check deployment status and determine next action
- `wait_before_next_check` - Wait 30 seconds before next status check
- `exit_loop` - Exit monitoring loop when deployment completes

---

## Example Dialogue 1: Successful Deployment Monitoring

**User:** Monitor build abc123

**Monitoring Agent (Checker):** I'll start monitoring your deployment.

*[Calls: check_deployment_and_decide(build_id="abc123")]*

**Response:** "CONTINUE: Deployment in progress. State: INITIALIZING, Status: Starting. Will check again in 30 seconds."

**Monitoring Agent (Checker):** 🔄 **Deployment Status Update**

Your deployment is currently **INITIALIZING**. Status: Starting.

I'll check again in 30 seconds.

---

**Monitoring Agent (Waiter):** Waiting before next check...

*[Calls: wait_before_next_check()]*

**Monitoring Agent (Waiter):** ⏳ Waited 30 seconds. Ready for next status check.

---

**Monitoring Agent (Checker):** Checking deployment status again...

*[Calls: check_deployment_and_decide(build_id="abc123")]*

**Response:** "CONTINUE: Deployment in progress. State: BUILDING, Status: Running tests (15/45 completed). Will check again in 30 seconds."

**Monitoring Agent (Checker):** 🔄 **Deployment Status Update**

Your deployment is now **BUILDING**. 

**Progress:** Running tests (15/45 completed)

I'll continue monitoring...

---

**Monitoring Agent (Waiter):** 

*[Calls: wait_before_next_check()]*

**Monitoring Agent (Waiter):** ⏳ Waited 30 seconds. Ready for next check.

---

**Monitoring Agent (Checker):**

*[Calls: check_deployment_and_decide(build_id="abc123")]*

**Response:** "CONTINUE: Deployment in progress. State: DEPLOYING, Status: Deploying services (3/5). Will check again in 30 seconds."

**Monitoring Agent (Checker):** 🔄 **Deployment Status Update**

Your deployment is now **DEPLOYING**.

**Progress:** Deploying services (3/5)

Almost there! Continuing to monitor...

---

**Monitoring Agent (Waiter):**

*[Calls: wait_before_next_check()]*

**Monitoring Agent (Waiter):** ⏳ Waited 30 seconds. Ready for next check.

---

**Monitoring Agent (Checker):**

*[Calls: check_deployment_and_decide(build_id="abc123")]*

**Response:** "ESCALATE: Deployment completed successfully! State: COMPLETE, Status: SUCCESS"

**Monitoring Agent (Checker):** 

*[Calls: exit_loop()]*

🎉 **Great news! Your deployment has completed successfully!**

**Final Status:**
- **Build ID**: abc123
- **State**: COMPLETE
- **Status**: SUCCESS

Your application is now live and ready to use!

---

## Example Dialogue 2: Failed Deployment Monitoring

**User:** Monitor deployment build_fail_456

**Monitoring Agent (Checker):** Starting deployment monitoring...

*[Calls: check_deployment_and_decide(build_id="build_fail_456")]*

**Response:** "CONTINUE: Deployment in progress. State: BUILDING, Status: Running tests. Will check again in 30 seconds."

**Monitoring Agent (Checker):** 🔄 **Deployment Status**

State: **BUILDING**
Status: Running tests

Monitoring continues...

---

**Monitoring Agent (Waiter):**

*[Calls: wait_before_next_check()]*

**Monitoring Agent (Waiter):** ⏳ Waiting 30 seconds...

---

**Monitoring Agent (Checker):**

*[Calls: check_deployment_and_decide(build_id="build_fail_456")]*

**Response:** "ESCALATE: Deployment failed! State: FAILED, Status: Tests failed (5 failures). Error: Test suite execution failed."

**Monitoring Agent (Checker):**

*[Calls: exit_loop()]*

❌ **Deployment Failed**

**Build ID**: build_fail_456
**State**: FAILED
**Status**: Tests failed (5 failures)
**Error**: Test suite execution failed

**What Happened:**
Your deployment failed during the testing phase. 5 tests did not pass.

**Recommended Actions:**
1. Review the build logs for detailed error messages
2. Fix the failing tests
3. Re-run the deployment

Would you like me to retrieve the build logs for more details?

---

## Example Dialogue 3: Long-Running Deployment

**User:** Monitor build long_123

**Monitoring Agent (Checker):**

*[Calls: check_deployment_and_decide(build_id="long_123")]*

**Response:** "CONTINUE: Deployment in progress. State: INITIALIZING, Status: Provisioning infrastructure. Will check again in 30 seconds."

**Monitoring Agent (Checker):** 🔄 Deployment **INITIALIZING** - Provisioning infrastructure

---

**Monitoring Agent (Waiter):**

*[Calls: wait_before_next_check()]*

---

*[This pattern repeats every 30 seconds...]*

**Check 2:** State: BUILDING, Status: Installing dependencies
**Check 3:** State: BUILDING, Status: Running tests (10/45)
**Check 4:** State: BUILDING, Status: Running tests (25/45)
**Check 5:** State: BUILDING, Status: Running tests (40/45)
**Check 6:** State: BUILDING, Status: All tests passed
**Check 7:** State: BUILDING, Status: Building artifacts
**Check 8:** State: DEPLOYING, Status: Running database migrations
**Check 9:** State: DEPLOYING, Status: Deploying services (1/5)
**Check 10:** State: DEPLOYING, Status: Deploying services (3/5)
**Check 11:** State: DEPLOYING, Status: Deploying services (5/5)
**Check 12:** State: DEPLOYING, Status: Running health checks

---

**Check 13:**

*[Calls: check_deployment_and_decide(build_id="long_123")]*

**Response:** "ESCALATE: Deployment completed successfully! State: COMPLETE, Status: SUCCESS"

*[Calls: exit_loop()]*

🎉 **Deployment Complete!**

Your deployment took approximately 6.5 minutes and completed successfully!

---

## Example Dialogue 4: Deployment with Warnings

**User:** Monitor build warn_789

**Monitoring Agent (Checker):**

*[Calls: check_deployment_and_decide(build_id="warn_789")]*

**Response:** "CONTINUE: Deployment in progress. State: BUILDING, Status: Running tests. Will check again in 30 seconds."

**Monitoring Agent (Checker):** 🔄 Building - Running tests

---

*[30 seconds later]*

**Monitoring Agent (Checker):**

*[Calls: check_deployment_and_decide(build_id="warn_789")]*

**Response:** "CONTINUE: Deployment in progress. State: DEPLOYING, Status: Deploying with warnings. Warning: 3 deprecated API calls detected. Will check again in 30 seconds."

**Monitoring Agent (Checker):** ⚠️ **Deployment Status with Warnings**

State: **DEPLOYING**
Status: Deploying with warnings

**Warning:** 3 deprecated API calls detected

The deployment is continuing, but you may want to address these warnings in a future update.

---

*[30 seconds later]*

**Monitoring Agent (Checker):**

*[Calls: check_deployment_and_decide(build_id="warn_789")]*

**Response:** "ESCALATE: Deployment completed with warnings. State: COMPLETE, Status: SUCCESS_WITH_WARNINGS"

*[Calls: exit_loop()]*

✅ **Deployment Complete (with warnings)**

**Build ID**: warn_789
**State**: COMPLETE
**Status**: SUCCESS_WITH_WARNINGS

**Warnings:**
- 3 deprecated API calls detected

Your application is deployed and functional, but consider addressing the warnings in your next update.

---

## Example Dialogue 5: Timeout Scenario

**User:** Monitor build timeout_999

**Monitoring Agent (Checker):**

*[Calls: check_deployment_and_decide(build_id="timeout_999")]*

**Response:** "CONTINUE: Deployment in progress. State: BUILDING, Status: Running long-running tests. Will check again in 30 seconds."

**Monitoring Agent (Checker):** 🔄 Building - Running long-running tests

---

*[This continues for 60 iterations (30 minutes)]*

**Check 1-60:** Various states, all returning "CONTINUE"

---

**After 60 checks (max_iterations reached):**

**Monitoring Agent:** ⏱️ **Monitoring Timeout Reached**

I've been monitoring your deployment for 30 minutes (maximum monitoring duration).

**Last Known Status:**
- **Build ID**: timeout_999
- **State**: BUILDING
- **Status**: Still running tests

**What This Means:**
The deployment is taking longer than expected. This could be normal for complex deployments.

**Options:**
1. Check deployment status manually
2. Review build logs for any issues
3. Contact support if deployment seems stuck

The deployment may still complete successfully - it's just taking longer than the monitoring window.

---

## Example Dialogue 6: Immediate Completion

**User:** Monitor build instant_complete

**Monitoring Agent (Checker):**

*[Calls: check_deployment_and_decide(build_id="instant_complete")]*

**Response:** "ESCALATE: Deployment already complete. State: COMPLETE, Status: SUCCESS"

*[Calls: exit_loop()]*

**Monitoring Agent (Checker):** ✅ **Deployment Already Complete!**

The deployment you asked me to monitor (build_instant_complete) has already finished.

**Status:**
- **State**: COMPLETE
- **Status**: SUCCESS

No monitoring needed - your deployment is done!

---

## Example Dialogue 7: Deployment Rollback

**User:** Monitor build rollback_111

**Monitoring Agent (Checker):**

*[Calls: check_deployment_and_decide(build_id="rollback_111")]*

**Response:** "CONTINUE: Deployment in progress. State: DEPLOYING, Status: Deploying services. Will check again in 30 seconds."

**Monitoring Agent (Checker):** 🔄 Deploying services...

---

*[30 seconds later]*

**Monitoring Agent (Checker):**

*[Calls: check_deployment_and_decide(build_id="rollback_111")]*

**Response:** "CONTINUE: Deployment in progress. State: ROLLING_BACK, Status: Health checks failed, initiating rollback. Will check again in 30 seconds."

**Monitoring Agent (Checker):** ⚠️ **Rollback Initiated**

State: **ROLLING_BACK**
Reason: Health checks failed

The system is automatically rolling back to the previous stable version.

---

*[30 seconds later]*

**Monitoring Agent (Checker):**

*[Calls: check_deployment_and_decide(build_id="rollback_111")]*

**Response:** "ESCALATE: Deployment failed and rolled back. State: ROLLED_BACK, Status: Rollback complete, previous version restored."

*[Calls: exit_loop()]*

**Monitoring Agent (Checker):** 🔄 **Deployment Rolled Back**

**Build ID**: rollback_111
**State**: ROLLED_BACK
**Status**: Rollback complete

**What Happened:**
The deployment failed health checks and was automatically rolled back to the previous stable version.

**Current Status:**
Your previous version is still running - no downtime occurred.

**Next Steps:**
1. Review build logs to identify the health check failure
2. Fix the issue in your code
3. Re-deploy when ready

---

## Example Dialogue 8: Multiple Deployments

**User:** Monitor build multi_1

**Monitoring Agent (Checker):** Starting monitoring for build multi_1...

*[Calls: check_deployment_and_decide(build_id="multi_1")]*

**Response:** "CONTINUE: Deployment in progress. State: BUILDING, Status: Running tests. Will check again in 30 seconds."

**Monitoring Agent (Checker):** 🔄 Monitoring build multi_1 - Building (Running tests)

---

*[Continues monitoring until completion]*

*[Calls: exit_loop()]*

✅ **Build multi_1 completed successfully!**

**Note:** If you need to monitor another deployment, just ask! Each monitoring session is independent.

---

## How the Monitoring Agent Works

### Loop Pattern
1. **Checker Agent** calls `check_deployment_and_decide(build_id)`
2. Response indicates either:
   - **CONTINUE:** Deployment still in progress → report status, continue loop
   - **ESCALATE:** Deployment finished (success/failure) → call `exit_loop()` to end monitoring
3. **Waiter Agent** calls `wait_before_next_check()` to wait 30 seconds
4. Loop repeats until deployment completes or max iterations (60) reached

### Max Iterations
- **Maximum**: 60 iterations
- **Duration**: 60 × 30 seconds = 30 minutes
- **After Max**: Monitoring stops, but deployment may still be running

### Status Updates
The agent provides clear, concise updates:
- Current state (INITIALIZING, BUILDING, DEPLOYING, COMPLETE, FAILED)
- Current status (specific activity)
- Progress indicators when available
- Warnings or errors if present

---

## Tips for Interacting with Monitoring Agent

1. **Automatic Transfer**: Usually transferred from Environment Agent automatically
2. **Build ID Required**: Monitoring needs a build_id to track
3. **Real-time Updates**: Updates every 30 seconds
4. **Hands-off**: No user interaction needed during monitoring
5. **Completion Notification**: Agent notifies when deployment finishes
6. **Error Handling**: Agent reports failures and suggests next steps
7. **Long Deployments**: Can monitor up to 30 minutes continuously

