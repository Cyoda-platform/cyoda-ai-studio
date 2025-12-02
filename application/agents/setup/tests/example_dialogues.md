# Setup Agent - Example Dialogues

## Overview
The Setup Agent is a Cyoda setup and configuration specialist, expert in project initialization, environment setup, and getting started with Cyoda development.

## Available Tools
- `validate_environment` - Check environment variables
- `check_project_structure` - Validate project directory structure
- `validate_workflow_file` - Validate workflow JSON files
- `get_build_id_from_context` - Retrieve build ID from context
- `get_env_deploy_status` - Check environment deployment status
- `get_user_info` - Get current user information
- `ui_function_issue_technical_user` - Issue technical user credentials
- `list_directory_files` - List files in a directory
- `read_file` - Read file contents
- `add_application_resource` - Add resources to application
- `finish_discussion` - Complete setup workflow

---

## Example Dialogue 1: Environment Variable Validation

**User:** Check if CYODA_HOST and CYODA_PORT environment variables are set

**Agent:** I'll check those environment variables for you.

*[Calls: validate_environment(required_vars=["CYODA_HOST", "CYODA_PORT"])]*

**Agent:** ✅ Environment validation complete!

**Results:**
- `CYODA_HOST`: ✅ Set to `https://api.cyoda.com`
- `CYODA_PORT`: ✅ Set to `8080`

Your Cyoda connection environment variables are properly configured. You're ready to connect to the Cyoda platform!

---

## Example Dialogue 2: Missing Environment Variables

**User:** Verify that GOOGLE_MODEL is configured

**Agent:** I'll validate the GOOGLE_MODEL environment variable.

*[Calls: validate_environment(required_vars=["GOOGLE_MODEL"])]*

**Agent:** ⚠️ Environment validation found issues:

**Missing Variables:**
- `GOOGLE_MODEL`: ❌ Not set

**How to Fix:**
Add this to your `.env` file:
```bash
GOOGLE_MODEL=gemini-2.0-flash-exp
```

Or set it in your shell:
```bash
export GOOGLE_MODEL=gemini-2.0-flash-exp
```

**Recommended Models:**
- `gemini-2.0-flash-exp` - Fast, cost-effective
- `gemini-1.5-pro` - More capable, higher quality
- `openai/gpt-4o-mini` - OpenAI alternative

Would you like help setting up your complete environment configuration?

---

## Example Dialogue 3: Project Structure Validation

**User:** Can you check if my project structure is correct?

**Agent:** I'll validate your project structure.

*[Calls: check_project_structure()]*

**Agent:** 📁 Project structure validation complete!

**✅ Found Required Directories:**
- `application/` - Main application code
- `application/entity/` - Entity definitions
- `application/workflow/` - Workflow definitions
- `application/routes/` - API routes
- `common/` - Shared utilities
- `tests/` - Test files

**✅ Found Configuration Files:**
- `requirements.txt` - Python dependencies
- `.env` - Environment variables
- `README.md` - Project documentation

**Recommendations:**
1. Consider adding `application/processors/` for business logic
2. Add `application/criteria/` for search criteria
3. Create `tests/unit/` and `tests/integration/` subdirectories

Your project structure follows Cyoda best practices! 🎉

---

## Example Dialogue 4: Workflow File Validation

**User:** I created a workflow file. Can you validate it?

**Agent:** I'll validate your workflow file. What's the file path?

**User:** application/workflow/customer/version_1/customerworkflow.json

**Agent:** Let me check that workflow file.

*[Calls: validate_workflow_file(file_path="application/workflow/customer/version_1/customerworkflow.json")]*

**Agent:** ✅ Workflow validation successful!

**Workflow Details:**
- **Name**: customer
- **Version**: version_1
- **States**: 4 states defined
  - DRAFT
  - SUBMITTED
  - APPROVED
  - REJECTED
- **Transitions**: 3 transitions defined
  - submit (DRAFT → SUBMITTED)
  - approve (SUBMITTED → APPROVED)
  - reject (SUBMITTED → REJECTED)

**Validation Checks Passed:**
- ✅ Valid JSON structure
- ✅ All required fields present
- ✅ State names are valid
- ✅ Transitions reference existing states
- ✅ No circular dependencies

Your workflow is ready to use!

---

## Example Dialogue 5: Invalid Workflow File

**User:** Validate my workflow at application/workflow/order/version_1/orderworkflow.json

**Agent:** Let me validate that workflow file.

*[Calls: validate_workflow_file(file_path="application/workflow/order/version_1/orderworkflow.json")]*

**Agent:** ❌ Workflow validation failed!

**Errors Found:**

1. **Invalid JSON Syntax** (Line 15)
   - Missing comma after "PENDING" state definition
   
2. **Missing Required Field**
   - Field `transitions` is required but not found

3. **Invalid State Reference**
   - Transition "ship" references state "SHIPPED" which doesn't exist
   - Available states: DRAFT, PENDING, CONFIRMED

**How to Fix:**

```json
{
  "name": "order",
  "states": [
    {"name": "DRAFT"},
    {"name": "PENDING"},
    {"name": "CONFIRMED"},
    {"name": "SHIPPED"}  // Add this state
  ],
  "transitions": [  // Add this section
    {
      "name": "submit",
      "from": "DRAFT",
      "to": "PENDING"
    },
    {
      "name": "confirm",
      "from": "PENDING",
      "to": "CONFIRMED"
    },
    {
      "name": "ship",
      "from": "CONFIRMED",
      "to": "SHIPPED"
    }
  ]
}
```

Would you like me to help you fix these issues?

---

## Example Dialogue 6: Getting User Information

**User:** What's my current user information?

**Agent:** Let me retrieve your user information.

*[Calls: get_user_info()]*

**Agent:** 👤 **Your User Information:**

- **User ID**: `user_12345`
- **Email**: `developer@company.com`
- **Organization**: `Acme Corporation`
- **Role**: `Developer`
- **Permissions**: 
  - Entity Management
  - Workflow Configuration
  - Deployment Access

**Active Environment:**
- **Environment ID**: `env_prod_001`
- **Status**: Active
- **Region**: US-East

Is there anything specific you'd like to configure for your user account?

---

## Example Dialogue 7: Checking Deployment Status

**User:** What's the status of my environment deployment?

**Agent:** Let me check your environment deployment status.

*[Calls: get_build_id_from_context()]*
*[Calls: get_env_deploy_status(build_id="build_abc123")]*

**Agent:** 🚀 **Deployment Status:**

- **Build ID**: `build_abc123`
- **Status**: ✅ **COMPLETE**
- **State**: SUCCESS
- **Started**: 2024-01-15 10:30:00 UTC
- **Completed**: 2024-01-15 10:45:00 UTC
- **Duration**: 15 minutes

**Deployment Details:**
- Environment: Production
- Version: 1.2.3
- Components Deployed:
  - ✅ Entity definitions (5 entities)
  - ✅ Workflow configurations (3 workflows)
  - ✅ API routes (12 endpoints)
  - ✅ Database migrations

**Next Steps:**
Your environment is ready! You can now:
1. Access your API at `https://api.cyoda.com/your-app`
2. Test your endpoints
3. Monitor logs and metrics

---

## Example Dialogue 8: Listing Project Files

**User:** Show me what's in my entity directory

**Agent:** I'll list the files in your entity directory.

*[Calls: list_directory_files(directory_path="application/entity")]*

**Agent:** 📂 **Contents of `application/entity/`:**

```
application/entity/
├── customer/
│   ├── version_1/
│   │   └── customer.json
│   └── version_2/
│       └── customer.json
├── order/
│   └── version_1/
│       └── order.json
├── product/
│   └── version_1/
│       └── product.json
└── invoice/
    └── version_1/
        └── invoice.json
```

**Summary:**
- **Total Entities**: 4 (customer, order, product, invoice)
- **Total Versions**: 5 entity versions
- **Latest Versions**: 
  - customer: version_2
  - order: version_1
  - product: version_1
  - invoice: version_1

Would you like me to read any of these entity files?

---

## Example Dialogue 9: Reading a File

**User:** Can you show me the customer entity definition?

**Agent:** I'll read the customer entity file for you.

*[Calls: read_file(file_path="application/entity/customer/version_1/customer.json")]*

**Agent:** 📄 **Customer Entity Definition (version_1):**

```json
{
  "name": "customer",
  "version": "version_1",
  "fields": [
    {
      "name": "customer_id",
      "type": "string",
      "required": true,
      "description": "Unique customer identifier"
    },
    {
      "name": "email",
      "type": "string",
      "required": true,
      "description": "Customer email address"
    },
    {
      "name": "name",
      "type": "string",
      "required": true,
      "description": "Customer full name"
    },
    {
      "name": "age",
      "type": "integer",
      "required": false,
      "description": "Customer age"
    },
    {
      "name": "vip_status",
      "type": "boolean",
      "required": false,
      "default": false,
      "description": "VIP customer flag"
    }
  ]
}
```

**Analysis:**
- **Required Fields**: customer_id, email, name
- **Optional Fields**: age, vip_status
- **Field Types**: string (3), integer (1), boolean (1)

Would you like me to help you create a workflow for this entity?

---

## Example Dialogue 10: Complete Setup Workflow

**User:** I'm starting a new Cyoda project. Can you help me set it up?

**Agent:** Absolutely! I'll guide you through the complete setup process. Let me start by checking your environment.

*[Calls: validate_environment(required_vars=["CYODA_HOST", "CYODA_PORT", "CYODA_CLIENT_ID"])]*

**Agent:** ✅ Environment variables are configured correctly!

Now let me check your project structure.

*[Calls: check_project_structure()]*

**Agent:** ✅ Project structure looks good!

**Setup Checklist:**

**1. Environment Configuration** ✅
- CYODA_HOST configured
- CYODA_PORT configured
- CYODA_CLIENT_ID configured

**2. Project Structure** ✅
- All required directories present
- Configuration files in place

**3. Next Steps:**
- [ ] Create your first entity definition
- [ ] Define a workflow for your entity
- [ ] Set up API routes
- [ ] Write tests
- [ ] Deploy to environment

**User:** How do I create my first entity?

**Agent:** Great question! Here's how to create your first entity:

**Step 1: Create the directory structure**
```bash
mkdir -p application/entity/myentity/version_1
```

**Step 2: Create the entity JSON file**
Create `application/entity/myentity/version_1/myentity.json`:

```json
{
  "name": "myentity",
  "version": "version_1",
  "fields": [
    {
      "name": "id",
      "type": "string",
      "required": true
    },
    {
      "name": "name",
      "type": "string",
      "required": true
    }
  ]
}
```

**Step 3: Validate the entity**
I can validate it for you once you create it!

Would you like me to help you create a workflow for this entity next?

*[Calls: finish_discussion()]*

**Agent:** Setup guidance complete! You're all set to start building your Cyoda application. Feel free to ask if you need help with any specific step!

---

## Tips for Interacting with Setup Agent

1. **Environment Setup**: Ask about environment variables and configuration
2. **Project Structure**: Request validation of your project organization
3. **File Validation**: Get help validating entity and workflow files
4. **Deployment Status**: Check on your environment deployments
5. **File Operations**: List directories and read configuration files
6. **Step-by-Step Guidance**: Request guided setup for new projects

