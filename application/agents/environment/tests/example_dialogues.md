# Environment Agent - Example Dialogues

## Overview
The Environment Agent is a Cyoda environment management specialist that handles environment provisioning, application deployment, build monitoring, troubleshooting, and credential management.

## Available Tools
- `check_environment_exists` - Check if an environment exists
- `deploy_cyoda_environment` - Deploy a new Cyoda environment
- `deploy_user_application` - Deploy user application to environment
- `get_deployment_status` - Get current deployment status
- `get_build_logs` - Retrieve build and deployment logs
- `ui_function_issue_technical_user` - Issue technical user credentials
- `transfer_to_agent` - Transfer to monitoring agent for long-running deployments

---

## Example Dialogue 1: Checking Environment Existence

**User:** Does my environment exist?

**Agent:** Let me check if your environment exists.

*[Calls: check_environment_exists()]*

**Agent:** ✅ **Environment Found!**

**Environment Details:**
- **Environment ID**: `env_prod_001`
- **Name**: Production Environment
- **Status**: Active
- **Region**: US-East
- **Created**: 2024-01-10
- **Last Updated**: 2024-01-15

**Resources:**
- API Endpoint: `https://api.cyoda.com/prod`
- Database: PostgreSQL 14
- Storage: 100GB allocated

Your environment is ready for deployments!

---

## Example Dialogue 2: Environment Not Found

**User:** Check if environment "dev-test" exists

**Agent:** Let me check for that environment.

*[Calls: check_environment_exists(environment_name="dev-test")]*

**Agent:** ❌ **Environment Not Found**

The environment "dev-test" does not exist in your organization.

**Would you like to:**
1. Create a new environment named "dev-test"
2. List all available environments
3. Deploy to an existing environment

I can help you create a new environment if needed!

---

## Example Dialogue 3: Deploying a New Environment

**User:** I need to create a new development environment

**Agent:** I'll help you deploy a new Cyoda environment. Let me gather the necessary information.

**User:** Name it "dev-environment" in the US-West region

**Agent:** Perfect! I'll deploy a new environment with those specifications.

*[Calls: deploy_cyoda_environment(environment_name="dev-environment", region="us-west")]*

**Agent:** 🚀 **Environment Deployment Started!**

**Deployment Details:**
- **Environment Name**: dev-environment
- **Region**: US-West
- **Build ID**: `build_xyz789`
- **Status**: INITIALIZING

**Deployment Steps:**
1. ✅ Provisioning infrastructure
2. 🔄 Setting up database
3. ⏳ Configuring networking
4. ⏳ Installing Cyoda platform
5. ⏳ Running health checks

**Estimated Time**: 10-15 minutes

I'll monitor this deployment for you. You can check the status anytime by asking "What's the deployment status?"

*[Transfers to monitoring agent for continuous status updates]*

---

## Example Dialogue 4: Deploying User Application

**User:** Deploy my application to the production environment

**Agent:** I'll deploy your application to production. Let me start the deployment process.

*[Calls: deploy_user_application(environment_id="env_prod_001")]*

**Agent:** 🚀 **Application Deployment Started!**

**Deployment Information:**
- **Environment**: Production (env_prod_001)
- **Build ID**: `build_app_456`
- **Application Version**: 1.2.3
- **Status**: BUILDING

**Components Being Deployed:**
- 📦 Entity definitions (5 entities)
- 🔄 Workflow configurations (3 workflows)
- 🌐 API routes (12 endpoints)
- 🗄️ Database migrations (3 pending)
- 📝 Configuration updates

**Build Progress:**
1. ✅ Code validation
2. 🔄 Running tests
3. ⏳ Building artifacts
4. ⏳ Database migration
5. ⏳ Deploying services
6. ⏳ Health checks

I'm monitoring the deployment. This typically takes 5-10 minutes.

---

## Example Dialogue 5: Checking Deployment Status

**User:** What's the deployment status?

**Agent:** Let me check the current deployment status.

*[Calls: get_deployment_status(build_id="build_app_456")]*

**Agent:** 📊 **Deployment Status Update**

**Build ID**: build_app_456
**Status**: 🔄 **IN PROGRESS**
**State**: DEPLOYING
**Progress**: 65%

**Completed Steps:**
- ✅ Code validation
- ✅ Tests passed (45/45)
- ✅ Artifacts built
- ✅ Database migration completed
- 🔄 Deploying services (3/5 services deployed)

**Current Activity:**
- Deploying API service
- Starting health checks

**Estimated Completion**: 3-5 minutes

I'll continue monitoring and notify you when deployment completes.

---

## Example Dialogue 6: Successful Deployment

**User:** Is my deployment done?

**Agent:** Let me check the latest status.

*[Calls: get_deployment_status(build_id="build_app_456")]*

**Agent:** 🎉 **Deployment Successful!**

**Build ID**: build_app_456
**Status**: ✅ **COMPLETE**
**Final State**: SUCCESS
**Completed**: 2024-01-15 11:30:00 UTC
**Duration**: 8 minutes 32 seconds

**Deployment Summary:**
- ✅ All tests passed (45/45)
- ✅ 5 entities deployed
- ✅ 3 workflows configured
- ✅ 12 API endpoints active
- ✅ Database migrations applied (3)
- ✅ Health checks passed

**Your Application is Live!**
- **API Endpoint**: `https://api.cyoda.com/prod/v1`
- **Health Status**: Healthy
- **Response Time**: 45ms average

**Next Steps:**
1. Test your API endpoints
2. Monitor application logs
3. Set up alerts and monitoring

Would you like me to show you the deployment logs?

---

## Example Dialogue 7: Failed Deployment

**User:** Check deployment status for build_fail_123

**Agent:** Let me check that deployment.

*[Calls: get_deployment_status(build_id="build_fail_123")]*

**Agent:** ❌ **Deployment Failed**

**Build ID**: build_fail_123
**Status**: FAILED
**State**: ERROR
**Failed At**: 2024-01-15 10:45:00 UTC

**Error Summary:**
- **Error Type**: Database Migration Error
- **Error Message**: "Migration script 003_add_customer_index.sql failed"
- **Failed Step**: Database Migration (Step 4 of 6)

**What Went Wrong:**
```
ERROR: relation "customers" does not exist
LINE 1: CREATE INDEX idx_customer_email ON customers(email);
```

**Recommended Actions:**
1. Check that the "customers" table exists
2. Verify migration scripts are in correct order
3. Review database schema

Would you like me to retrieve the full build logs for more details?

---

## Example Dialogue 8: Retrieving Build Logs

**User:** Show me the build logs for the failed deployment

**Agent:** I'll retrieve the build logs for you.

*[Calls: get_build_logs(build_id="build_fail_123")]*

**Agent:** 📋 **Build Logs for build_fail_123**

```
[2024-01-15 10:40:00] INFO: Starting deployment
[2024-01-15 10:40:05] INFO: Validating code... OK
[2024-01-15 10:40:15] INFO: Running tests...
[2024-01-15 10:41:00] INFO: Tests passed: 45/45
[2024-01-15 10:41:05] INFO: Building artifacts... OK
[2024-01-15 10:42:00] INFO: Starting database migration
[2024-01-15 10:42:10] INFO: Running migration 001_create_tables.sql... OK
[2024-01-15 10:42:20] INFO: Running migration 002_add_indexes.sql... OK
[2024-01-15 10:42:30] ERROR: Running migration 003_add_customer_index.sql... FAILED
[2024-01-15 10:42:30] ERROR: relation "customers" does not exist
[2024-01-15 10:42:30] ERROR: Migration failed at line 1
[2024-01-15 10:42:30] ERROR: CREATE INDEX idx_customer_email ON customers(email);
[2024-01-15 10:42:35] ERROR: Deployment aborted
[2024-01-15 10:42:40] INFO: Rolling back changes...
[2024-01-15 10:43:00] INFO: Rollback complete
```

**Analysis:**
The migration script `003_add_customer_index.sql` is trying to create an index on a "customers" table that doesn't exist. 

**Possible Causes:**
1. Migration 001 might not have created the "customers" table
2. Table name might be different (e.g., "customer" instead of "customers")
3. Migration scripts might be out of order

**How to Fix:**
1. Check migration 001 to verify table creation
2. Ensure table name consistency
3. Re-run deployment after fixing the migration script

Would you like help reviewing your migration scripts?

---

## Example Dialogue 9: Issuing Technical User Credentials

**User:** I need credentials for API access

**Agent:** I'll issue technical user credentials for you.

*[Calls: ui_function_issue_technical_user()]*

**Agent:** 🔐 **Technical User Credentials Issued**

**Credentials:**
- **Client ID**: `cyoda_client_abc123xyz`
- **Client Secret**: `secret_def456uvw789` ⚠️ (Save this securely!)

**Important Security Notes:**
⚠️ **Save these credentials immediately!** The client secret will not be shown again.

**How to Use:**
Add these to your `.env` file:
```bash
CYODA_CLIENT_ID=cyoda_client_abc123xyz
CYODA_CLIENT_SECRET=secret_def456uvw789
```

**Permissions Granted:**
- ✅ Entity Management (Read/Write)
- ✅ Workflow Execution
- ✅ API Access
- ✅ Deployment Operations

**Authentication Example:**
```python
import os
from cyoda_client import CyodaClient

client = CyodaClient(
    client_id=os.getenv("CYODA_CLIENT_ID"),
    client_secret=os.getenv("CYODA_CLIENT_SECRET"),
    host=os.getenv("CYODA_HOST")
)
```

**Security Best Practices:**
1. Never commit credentials to version control
2. Use environment variables
3. Rotate credentials regularly
4. Use different credentials for dev/prod

Your credentials are ready to use!

---

## Example Dialogue 10: Multi-turn Deployment Workflow

**User:** I want to deploy my application

**Agent:** I'll help you deploy your application. First, let me check if your environment exists.

*[Calls: check_environment_exists()]*

**Agent:** ✅ Found your environment: **Production (env_prod_001)**

Before deploying, let me verify a few things:
1. Do you want to deploy to Production?
2. Have you tested your changes in a development environment?

**User:** Yes, I've tested everything. Deploy to production.

**Agent:** Perfect! Starting production deployment.

*[Calls: deploy_user_application(environment_id="env_prod_001")]*

**Agent:** 🚀 Deployment started! Build ID: `build_prod_789`

I'm transferring you to the monitoring agent who will provide real-time updates on your deployment progress.

*[Calls: transfer_to_agent("deployment_monitor")]*

**Monitoring Agent:** 👋 I'm now monitoring your deployment (build_prod_789).

**Status Update 1** (30 seconds later):
- ✅ Code validation complete
- 🔄 Running tests (15/45 completed)

**Status Update 2** (2 minutes later):
- ✅ All tests passed (45/45)
- 🔄 Building artifacts

**Status Update 3** (5 minutes later):
- ✅ Artifacts built
- 🔄 Running database migrations

**Status Update 4** (7 minutes later):
- ✅ Database migrations complete
- 🔄 Deploying services (2/5)

**Final Update** (10 minutes later):
🎉 **Deployment Complete!**

Your application is now live in production!
- API: `https://api.cyoda.com/prod/v1`
- Status: Healthy
- All services running

---

## Tips for Interacting with Environment Agent

1. **Environment Management**: Check, create, and manage environments
2. **Deployments**: Deploy applications and monitor progress
3. **Troubleshooting**: Get logs and diagnose deployment failures
4. **Credentials**: Request and manage API credentials
5. **Status Monitoring**: Check real-time deployment status
6. **Long Deployments**: Agent automatically transfers to monitoring agent for extended operations

