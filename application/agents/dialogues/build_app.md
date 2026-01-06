## Phase 1: Context & Branching

**Goal:** Determine the workspace foundation without overwhelming the user.

* **Greeting & Inquiry:** "Ready to build! Should we start fresh, or do you have an existing branch you'd like to continue working on?"
* **Branch Setup:** * *If existing:* "Connected to your branch. Let’s pick up where you left off."
* *If new:* "No problem. I’ve initialized a new branch for this project to keep your main codebase clean."

---

## Phase 2: Requirement Gathering

**Goal:** Offer multiple ways to define the app logic and establish the "Manual Push" path early.

* **The Multi-Channel Prompt:** "How would you like to define your requirements? You can:
* **Collaborate:** We can generate entities, workflows, and requirements together right here.
* **Upload:** Attach your files directly.
* **Manual Push:** You can push files yourself to `/requirements/` in the repository.


Any input you provide (text or file) will be saved immediately to your branch, and I'll open the **Canvas** panel so we can visualize the logic."

---

## Phase 3: Transition to Build

**Goal:** Guide the user toward the correct build engine based on their branch status.

### **Scenario A: Existing Branch (Hybrid/Edit Mode)**

"I see we have some existing work here. Since this isn't a blank slate, how would you like to proceed?"

* **Editing Mode (`generate_application`):** "Best if you already have substantial work implemented. I’ll refine and add to your current logic."
* **Full New Application (`generate_code_with_cli`):** "I'll rebuild the application structure from scratch while incorporating your new requirements."

### **Scenario B: New Branch (Full Build)**

"Requirements locked in! I’m starting the full application build now using the `generate_application` engine."

---

## Phase 4: Background Execution & Deployment

**Goal:** Manage expectations and provide a clear path to "Go Live."

* **The 'Build' Notification:** "I'm building your application in the background. You can track progress in the **Tasks Panel**."
* **Next Steps (Deployment):**
  "Once the build is complete, you'll see it in the tasks panel. At that point:
1. **Run Setup Assistant:** I recommend calling the Setup Assistant to configure your environment.
2. **Deploy to Cyoda:** Just ask, and I can deploy your application directly to a **Cyoda environment** for testing or production."
