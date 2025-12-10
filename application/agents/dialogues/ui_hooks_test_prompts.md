# UI Hooks Test Prompts - Dialogue Examples

## Overview

This document contains test prompts and expected dialogue flows for testing UI hooks functionality across all agents. These prompts demonstrate how agents use prompt-level hooks to create dynamic, interactive experiences.

## Test Prompt 1: Environment Agent - Multi-Choice Options

**User:** I need to manage my Cyoda environment. What can you help me with?

**Expected Agent Response:**
```
I can help you manage your Cyoda environment! Here are the main things I can do:

[🚀 Deploy Environment] [✅ Check Status] [🔐 Issue Credentials]

What would you like to do?
```

**Hook Type:** `option_selection`
**Hook Parameters:**
- question: "What would you like to do?"
- options: [deploy, check, credentials]

---

## Test Prompt 2: Setup Agent - Environment Selection

**User:** I need credentials for my development environment

**Expected Agent Response:**
```
I can issue technical user credentials for your environment. Which environment would you like credentials for?

[🔧 Development] [🧪 Staging] [🚀 Production]
```

**Hook Type:** `option_selection`
**Hook Parameters:**
- question: "Which environment would you like credentials for?"
- options: [dev, staging, prod]

---

## Test Prompt 3: GitHub Agent - Next Steps After Code Generation

**User:** Generate a Customer entity for me

**Expected Agent Response:**
```
✅ Customer entity created successfully!

I've generated:
- Entity definition with fields (id, name, email, phone)
- Workflow with states (DRAFT, ACTIVE, ARCHIVED)
- Routes for CRUD operations
- Validation processor
- Comprehensive tests

What would you like to do next?

[🔨 Build Application] [📊 Analyze Structure] [🚀 Deploy to Environment]
```

**Hook Type:** `option_selection`
**Hook Parameters:**
- question: "What would you like to do next?"
- options: [build, analyze, deploy]

---

## Test Prompt 4: Canvas Agent - Canvas Navigation

**User:** Create an Order entity

**Expected Agent Response:**
```
✅ Order entity created and saved!

I've created the Order entity with fields:
- order_id (string, required)
- customer_id (string, required)
- total_amount (number, required)
- status (string, required)

[📋 Open Canvas - Entities Tab]
```

**Hook Type:** `open_canvas_tab`
**Hook Parameters:**
- tab_name: "entities"

---

## Test Prompt 5: Conditional Options Based on Context

**User:** What should I do with my environment?

**Expected Agent Response (if environment exists):**
```
Your environment is already set up! What would you like to do?

[🚀 Deploy Application] [📊 View Metrics] [🔧 Manage Credentials]
```

**Expected Agent Response (if environment doesn't exist):**
```
You don't have an environment yet. Would you like to create one?

[✨ Create New Environment] [📖 Learn More]
```

**Hook Type:** `option_selection` (conditional)

---

## Test Prompt 6: Multiple Hooks in Sequence

**User:** Set up my development environment and deploy an app

**Expected Flow:**
1. Agent asks: "What's your environment name?"
   - User: "dev"
2. Agent deploys environment
3. Agent shows: "Environment deployed! What's next?"
   - [🚀 Deploy App] [✅ Check Status] [📊 View Logs]
4. User clicks "Deploy App"
5. Agent asks: "What's your app name?"
   - User: "my-api"
6. Agent deploys app
7. Agent shows: "App deployed! Opening Canvas..."
   - [📋 Open Canvas]

---

## Test Prompt 7: Error Handling with Fallback

**User:** Deploy my application

**Expected Agent Response (if hook creation fails):**
```
I can help you deploy your application. What's your app name?

If you prefer, here are common options:
1. my-api
2. my-web-app
3. my-service

Or provide a custom name.
```

**Fallback:** Text-based options if hook creation fails

---

## Test Prompt 8: Dynamic Options Based on Repository State

**User:** What can I do with my code?

**Expected Agent Response (if repo has uncommitted changes):**
```
You have uncommitted changes. What would you like to do?

[💾 Commit Changes] [📊 View Diff] [🔄 Discard Changes]
```

**Expected Agent Response (if repo is clean):**
```
Your repository is up to date. What would you like to do?

[🔨 Generate Code] [📊 Analyze Structure] [🚀 Deploy]
```

---

## Test Prompt 9: Canvas Navigation After Creation

**User:** Create a Payment workflow

**Expected Agent Response:**
```
✅ Payment workflow created!

Workflow Details:
- Name: Payment
- States: PENDING, PROCESSING, COMPLETED, FAILED
- Transitions: 4 defined

[📋 Open Canvas - Workflows Tab]
```

**Hook Type:** `open_canvas_tab`
**Hook Parameters:**
- tab_name: "workflows"

---

## Test Prompt 10: Multi-Step Workflow with Hooks

**User:** Help me set up a complete application

**Expected Flow:**
1. "What's your application name?"
   - User: "customer-portal"
2. "What entities do you need?"
   - [👤 Customer] [📦 Order] [💳 Payment] [⚙️ Custom]
3. "What workflows do you need?"
   - [📋 Order Processing] [💰 Payment] [📧 Notification] [⚙️ Custom]
4. "Ready to generate?"
   - [✨ Generate] [🔄 Modify] [❌ Cancel]
5. Generation completes
6. "What's next?"
   - [🚀 Deploy] [📊 Review] [💾 Commit]

---

## Testing Checklist

- [ ] Option selection hooks render as clickable buttons
- [ ] Canvas navigation hooks open correct tabs
- [ ] Conditional options display based on context
- [ ] Fallback to text works if hook creation fails
- [ ] Multiple hooks in sequence work correctly
- [ ] Hook parameters are passed correctly
- [ ] User selections are captured and processed
- [ ] Hooks work across all agents
- [ ] Hooks work with different conversation contexts
- [ ] Performance is acceptable (no delays)

---

## Running These Tests

1. Start an agent conversation
2. Use the test prompts above
3. Verify hooks render correctly
4. Click buttons and verify selections are processed
5. Check that agent responds appropriately to selections
6. Verify canvas opens to correct tabs
7. Test error scenarios and fallback behavior

