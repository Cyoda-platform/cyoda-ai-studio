# Test Scenarios for GitHub Agent Build Workflow Enhancement

## Test Scenario 1: Public Repository - Basic Flow

### User Input:
```
User: "I want to build a customer management application"
```

### Expected Agent Behavior:

**Step 1: Repository Type Question**
```
Agent: "I'll help you build a customer management application! First, let me set up the repository.

Do you want to work with a **public** or **private** repository?

**Public Repository**: Use Cyoda's template repositories (mcp-cyoda-quart-app, java-client-template)
**Private Repository**: Use your own GitHub repository"
```

**Step 2: Language Question**
```
User: "Public"
Agent: "Great! What programming language? (python or java)"
```

**Step 3: Clone and Wait for Confirmation**
```
User: "Python"
Agent: [Calls generate_branch_uuid, set_repository_config, clone_repository]
Agent: "✅ Repository configured successfully!

📦 **Repository:** Cyoda-platform/mcp-cyoda-quart-app
🌿 **Branch:** 68f71074-c15f-11f0-89a7-40c2ba0ac9eb
🔗 **GitHub URL:** https://github.com/Cyoda-platform/mcp-cyoda-quart-app/tree/68f71074-c15f-11f0-89a7-40c2ba0ac9eb

📎 **Before we start building:**
- You can attach files (specs, diagrams, requirements docs) to help guide the build
- You can provide additional details about your customer management system

💡 **Pro Tip:** Use the Canvas feature to visually design your requirements, entities, and workflows before building!
Canvas provides an interactive editor where you can:
- Define functional requirements with a visual interface
- Design entity structures and relationships
- Create workflow diagrams
- The AI will use these as blueprints for your application

📊 **Monitor Progress:** Once the build starts, you can track it in the Entities window (BackgroundTask entity)

✨ **Ready to build?** Just let me know when you're ready, or attach any files/details first!"
```

**Step 4: User Confirms Ready**
```
User: "I'm ready to start"
Agent: [Calls check_user_environment_status]
Agent: "🌍 **Environment Deployment**

Your Cyoda environment is not yet deployed. Would you like to deploy it now?

**Deploying the environment:**
- Takes 5-10 minutes
- Runs in parallel with your application build
- Required to run your application after build completes

**Options:**
- "Yes, deploy it" → I'll deploy environment and start building
- "No, just build" → I'll only build the application (you can deploy later)"
```

**Step 5: User Confirms Deployment**
```
User: "Yes, deploy it"
Agent: [Calls deploy_cyoda_environment, then generate_application]
Agent: "🚀 Application build started!

📋 **Task ID:** abc-123-def-456
🌿 **Branch:** 68f71074-c15f-11f0-89a7-40c2ba0ac9eb
💻 **Language:** python
🌍 **Environment:** Deploying (Build ID: env-xyz-789)

⏳ The build is running in the background (typically 10-30 minutes).
🌍 Environment deployment is also in progress (5-10 minutes).
📊 Monitor progress in the **Entities window** → BackgroundTask entity

You can continue chatting while the build runs. I'll update you when it completes!"
```

### Verification Points:
- ✅ Agent asks for repository type
- ✅ Agent asks for language
- ✅ Agent clones repository
- ✅ Agent shows repository URL with owner/repo/branch
- ✅ Agent mentions Canvas feature
- ✅ Agent mentions Entities window for monitoring
- ✅ Agent WAITS for user confirmation
- ✅ Agent checks environment status BEFORE building
- ✅ Agent asks about environment deployment if not deployed
- ✅ Agent deploys environment if user confirms
- ✅ Agent only calls generate_application AFTER environment check
- ✅ Agent provides task ID and monitoring info
- ✅ Agent mentions both build and deployment status

---

## Test Scenario 2: Private Repository - With File Attachment

### User Input:
```
User: "Build an inventory management system in my private repo"
```

### Expected Agent Behavior:

**Step 1: GitHub App Installation Instructions**
```
Agent: "I'll help you build an inventory management system in your private repository!

To use your private repository, you need to install the Cyoda AI Assistant GitHub App:

📱 **Installation Steps:**
1. Go to: https://github.com/apps/cyoda-ai-assistant
2. Click 'Install' and select your repository
3. After installation, GitHub will show your Installation ID

📋 **What I need from you:**
- Installation ID (number shown after installation)
- Full repository URL (e.g., https://github.com/yourorg/yourrepo)
- Programming language (python or java)
- Branch name (or I can generate one)"
```

**Step 2: Collect Info and Clone**
```
User: "Installation ID is 12345678, repo is https://github.com/acme-corp/inventory-app, Python, generate a branch"
Agent: [Calls generate_branch_uuid, set_repository_config, clone_repository]
Agent: "✅ Repository configured successfully!

📦 **Repository:** acme-corp/inventory-app
🌿 **Branch:** a1b2c3d4-e5f6-7890-abcd-ef1234567890
🔗 **GitHub URL:** https://github.com/acme-corp/inventory-app/tree/a1b2c3d4-e5f6-7890-abcd-ef1234567890

📎 **Before we start building:**
- You can attach files (specs, diagrams, requirements docs) to help guide the build
- You can provide additional details or clarifications

💡 **Pro Tip:** Use the Canvas feature to visually design your requirements, entities, and workflows before building!
Canvas provides an interactive editor where you can:
- Define functional requirements with a visual interface
- Design entity structures and relationships
- Create workflow diagrams
- The AI will use these as blueprints for your application

📊 **Monitor Progress:** Once the build starts, you can track it in the Entities window (BackgroundTask entity)

✨ **Ready to build?** Just let me know when you're ready, or attach any files/details first!"
```

**Step 3: User Attaches Files**
```
User: [Attaches inventory_spec.pdf]
User: "I've attached the spec. Can you review it?"
Agent: [Reviews file]
Agent: "I've reviewed your inventory specification. It looks comprehensive! 
The spec includes:
- Product catalog management
- Stock tracking with real-time updates
- Low stock alerts
- Multi-warehouse support

This will be a great foundation for the build. Ready to start building?"
```

**Step 4: User Confirms**
```
User: "Yes, let's build it"
Agent: [Calls generate_application with requirements from spec]
Agent: "🚀 Application build started!

📋 **Task ID:** xyz-789-abc-123
🌿 **Branch:** a1b2c3d4-e5f6-7890-abcd-ef1234567890
💻 **Language:** python

⏳ The build is running in the background (typically 10-30 minutes).
📊 Monitor progress in the **Entities window** → BackgroundTask entity

You can continue chatting while the build runs. I'll update you when it completes!"
```

### Verification Points:
- ✅ Agent provides GitHub App installation instructions
- ✅ Agent extracts owner from private repo URL (acme-corp)
- ✅ Agent constructs correct GitHub URL with extracted owner
- ✅ Agent waits for user to attach files
- ✅ Agent reviews attached files before building
- ✅ Agent waits for explicit confirmation
- ✅ Agent uses file content in requirements

---

## Test Scenario 3: User Asks About Canvas

### User Input:
```
User: "Build a task management app"
[Agent sets up repo and shows post-clone message]
User: "What's Canvas? How do I use it?"
```

### Expected Agent Behavior:
```
Agent: "Canvas is Cyoda's visual design tool that helps you create application blueprints before building!

**What you can do in Canvas:**
- 📝 **Functional Requirements**: Write and organize your app requirements in a structured format
- 🏗️ **Entity Design**: Visually design your data models with fields, types, and relationships
- 🔄 **Workflow Creation**: Build state machines and business process flows with a drag-and-drop interface
- 🔗 **Relationship Mapping**: Define how entities connect and interact

**How to use it:**
1. Open the Canvas tab in the UI
2. Create a new requirement, entity, or workflow
3. Use the visual editor to design your components
4. Save your designs
5. When you're ready to build, I'll use these designs as blueprints for generating your application code

**Benefits:**
- Visual design is easier than writing JSON/code
- See the big picture of your application architecture
- Validate your design before building
- Collaborate with team members on the design

Would you like to design your task management app in Canvas first, or shall we proceed with building based on your description?"
```

### Verification Points:
- ✅ Agent explains Canvas clearly
- ✅ Agent doesn't push Canvas too hard
- ✅ Agent gives user choice to use Canvas or proceed
- ✅ Agent remains helpful and informative

---

## Test Scenario 4: Verify Repository Owner Extraction

### Test Cases:

**Case 1: HTTPS URL**
```
Input: "https://github.com/myorg/myrepo"
Expected: owner="myorg", repo="myrepo"
```

**Case 2: HTTPS URL with .git**
```
Input: "https://github.com/acme-corp/inventory-app.git"
Expected: owner="acme-corp", repo="inventory-app"
```

**Case 3: SSH URL**
```
Input: "git@github.com:myorg/myrepo.git"
Expected: owner="myorg", repo="myrepo"
```

**Case 4: Public Repository (Python)**
```
Input: repository_type="public", language="python"
Expected: owner="Cyoda-platform", repo="mcp-cyoda-quart-app"
```

**Case 5: Public Repository (Java)**
```
Input: repository_type="public", language="java"
Expected: owner="Cyoda-platform", repo="java-client-template"
```

### Verification:
- ✅ Regex pattern correctly extracts owner and repo
- ✅ GitHub URL is constructed correctly
- ✅ Context variables are set properly

---

## Test Scenario 5: Negative Test - Agent Doesn't Skip Steps

### User Input:
```
User: "Build a CRM system, Python, public repo, start building now"
```

### Expected Agent Behavior:
```
Agent: [Calls generate_branch_uuid, set_repository_config, clone_repository]
Agent: "✅ Repository configured successfully!

📦 **Repository:** Cyoda-platform/mcp-cyoda-quart-app
🌿 **Branch:** [uuid]
🔗 **GitHub URL:** https://github.com/Cyoda-platform/mcp-cyoda-quart-app/tree/[uuid]

📎 **Before we start building:**
[... full post-clone message ...]

✨ **Ready to build?** Just let me know when you're ready, or attach any files/details first!"
```

**Agent MUST NOT:**
- ❌ Skip the post-clone information message
- ❌ Immediately call generate_application
- ❌ Assume user is ready without confirmation

**Agent MUST:**
- ✅ Show full post-clone message
- ✅ Wait for explicit confirmation
- ✅ Give user opportunity to attach files or ask questions

### Verification Points:
- ✅ Agent follows workflow even when user seems eager
- ✅ Agent doesn't skip mandatory steps
- ✅ Agent waits for confirmation

---

## Manual Testing Checklist

### Pre-Test Setup:
- [ ] Ensure GitHub agent is loaded
- [ ] Ensure .env has correct REPOSITORY_OWNER
- [ ] Ensure GitHub App is installed (for private repo tests)

### Test Execution:
- [ ] Run Test Scenario 1 (Public Repo - Basic)
- [ ] Run Test Scenario 2 (Private Repo - With Files)
- [ ] Run Test Scenario 3 (Canvas Questions)
- [ ] Run Test Scenario 4 (Owner Extraction)
- [ ] Run Test Scenario 5 (Negative Test)

### Post-Test Verification:
- [ ] Check BackgroundTask entity is created
- [ ] Verify GitHub URL is correct
- [ ] Verify branch is created on GitHub
- [ ] Verify repository owner is extracted correctly
- [ ] Verify agent waits for confirmation in all cases

---

## Expected Outcomes

### Success Criteria:
1. ✅ Agent ALWAYS shows post-clone information
2. ✅ Agent ALWAYS mentions Canvas (brief, helpful)
3. ✅ Agent ALWAYS mentions Entities window for monitoring
4. ✅ Agent ALWAYS waits for user confirmation
5. ✅ Agent NEVER calls generate_application immediately after clone
6. ✅ Repository owner is correctly extracted for private repos
7. ✅ GitHub URLs are correctly constructed
8. ✅ User has opportunity to attach files before building

### Failure Indicators:
- ❌ Agent skips post-clone message
- ❌ Agent calls generate_application without confirmation
- ❌ Agent doesn't mention Canvas or Entities window
- ❌ GitHub URL is incorrect or missing owner
- ❌ Agent is pushy about Canvas (should be a "Pro Tip")
- ❌ User feels rushed into building

