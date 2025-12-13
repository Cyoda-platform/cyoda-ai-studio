# Dialogue Scenarios: Application Build Assistant

---

## Scenario 1: Existing Branch Identified From Context

**User:**
I want to continue building the payments service we started last week.

**Assistant:**
I see you already have an existing branch for this work. I’ll set up the repository using that branch now.

Before we continue, would you like to:

* Add or update requirements
* Attach any files
* Generate requirements, entities, or workflows together?

You can also push requirements manually to:
`/requirements/`

---

**User:**
Let’s add a few new requirements.

**Assistant:**
Great. Please share the requirements as text or attach a file. I’ll save them directly to your branch.

---

**User:**
We need support for partial refunds and audit logging.

**Assistant:**
Thanks. I’ve saved these requirements to your branch and opened them in Canvas so we can review and refine them together.

Let me know when the requirements are complete.

---

**User:**
They’re complete.

**Assistant:**
Since this branch already contains existing work, how would you like to proceed?

* **Editing mode** (build on top of the existing implementation), or
* **Full new application mode** (regenerate the application)

Editing mode assumes substantial work is already implemented.

---

**User:**
Editing mode.

**Assistant:**
Perfect. I’ll start building immediately in editing mode.

I can also start deployment in the background. Once the build is complete, you’ll see it in the Tasks panel. At that point, you can call the setup assistant or ask me to deploy to a Cyoda environment.

---

## Scenario 2: Existing Branch, User Uploads Files

**User:**
I want to continue work on branch `feature/user-onboarding`.

**Assistant:**
Got it. I’ve set up the repository using the `feature/user-onboarding` branch.

Would you like to add more requirements, attach files, or generate entities and workflows?

If you prefer, you can also push files manually to:
`/requirements/`

---

**User:**
I’ll upload a requirements document.

**Assistant:**
Sounds good. Please upload the file when ready.

---

**User uploads a file**

**Assistant:**
The file has been saved to your branch. I’ve opened it in Canvas so we can review it together.

Let me know when the requirements are complete.

---

## Scenario 3: No Existing Branch (New Application)

**User:**
I want to build a new application for inventory management.

**Assistant:**
Great. Since this is a new application, I’ll create and set up a new branch for you.

You can use Canvas to work on:

* Requirements
* Entities
* Workflows

I can also:

* Generate requirements, entities, and workflows with you
* Save any attached files to the repository
* Let you push files manually to:
  `/requirements/`

How would you like to start?

---

**User:**
Let’s generate requirements together.

**Assistant:**
Perfect. I’ll start drafting requirements and save them to the repository as we go. I’ll also keep everything visible in Canvas for review.

---

**User:**
The app should track products, stock levels, and warehouse locations.

**Assistant:**
I’ve saved these requirements to the new branch and opened them in Canvas.

Let me know when the requirements are complete or if you’d like to add entities or workflows next.

---

## Scenario 4: New Branch, User Pushes Manually

**User:**
I’ll push the requirements myself.

**Assistant:**
No problem. Please push your requirements files to the following path in the repository:

`/requirements/`

Once you’re done, let me know and we’ll continue.

---

**User:**
I’ve pushed everything.

**Assistant:**
Great. I see the requirements in the repository.

Are the requirements complete, or would you like to make additional changes in Canvas?

---

## Scenario 5: Build Completion and Deployment

**User:**
The requirements are complete. Let’s proceed.

**Assistant:**
Great. I’m starting the build now in full new application mode.

I can also start deployment in the background while the build runs.

You’ll be able to track progress in the Tasks panel. Once the build is complete, I recommend calling the setup assistant.

When you’re ready, you can also ask me to deploy the application to a Cyoda environment.

---

## Scenario 6: Clarifying Build Mode on Existing Branch

**User:**
Why do I need to choose a build mode?

**Assistant:**
Good question.

Because you’re working on an existing branch, there are two options:

* **Editing mode** builds on top of the code that already exists
* **Full new application mode** regenerates the application from scratch

If you already have substantial functionality implemented, editing mode is usually the best choice.

Let me know which one you’d like to use.
