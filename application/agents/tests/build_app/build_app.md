Below is a structured set of **test cases** covering the full flow you described.
They are written in a clear, reusable format suitable for **QA, product validation, or automation later**.

---

# Test Cases: Application Build Flow

## 1. Entry & Branch Identification

### TC-01: Detect Existing Branch From Context

**Preconditions:**

* User starts a conversation indicating they want to build an application
* User mentions an existing branch name implicitly or explicitly

**Steps:**

1. User states they want to build or continue building an application
2. System parses context for branch information

**Expected Result:**

* System correctly identifies the existing branch
* No prompt asking whether a branch exists
* Repository setup starts using the identified branch

---

### TC-02: Ask for Branch When Not Provided

**Preconditions:**

* User wants to build an application
* No branch information provided

**Steps:**

1. User requests application build
2. System checks context and finds no branch

**Expected Result:**

* System asks whether the user has an existing branch or wants to start from scratch

---

## 2. Existing Branch Flow

### TC-03: Setup Repository With Existing Branch

**Preconditions:**

* User confirms an existing branch

**Steps:**

1. User provides branch name
2. System sets up repository using that branch

**Expected Result:**

* Repository is initialized on the specified branch
* User is informed setup is complete

---

### TC-04: Prompt for Additional Inputs (Existing Branch)

**Preconditions:**

* Repository is set up with existing branch

**Steps:**

1. System asks user if they want to:

    * Add requirements
    * Attach files
    * Generate requirements/entities/workflows

**Expected Result:**

* User is clearly presented with all options

---

### TC-05: Show Manual Requirements Path

**Preconditions:**

* Existing branch is active

**Steps:**

1. System informs user where to manually push requirements

**Expected Result:**

* Repository path is clearly provided
* Path is correct and consistent across sessions

---

### TC-06: Save Textual Requirements to Branch

**Preconditions:**

* Existing branch is active

**Steps:**

1. User provides requirements as text
2. System saves requirements to the branch

**Expected Result:**

* Requirements file is created or updated in the correct path
* No user confirmation required to save

---

### TC-07: Save Uploaded Requirement Files

**Preconditions:**

* Existing branch is active

**Steps:**

1. User uploads a requirements file
2. System saves the file to the branch

**Expected Result:**

* File appears in correct repository location
* File contents are unchanged

---

### TC-08: Open Canvas After Saving Requirements

**Preconditions:**

* Requirements are saved (text or file)

**Steps:**

1. System completes save operation

**Expected Result:**

* Canvas panel opens automatically
* Canvas displays saved content

---

### TC-09: Confirm Requirements Completion

**Preconditions:**

* Requirements exist in branch

**Steps:**

1. System asks user to confirm requirements are complete

**Expected Result:**

* User can confirm or continue editing
* No build starts before confirmation

---

### TC-10: Choose Build Mode for Existing Branch

**Preconditions:**

* User confirms requirements are complete

**Steps:**

1. System asks user to choose:

    * Editing mode (`generate_application`)
    * Full new application mode (`generate_code_with_cli`)
2. System explains editing mode assumption

**Expected Result:**

* User understands the difference between modes
* Selected mode is acknowledged

---

## 3. New Branch Flow

### TC-11: Create New Branch

**Preconditions:**

* User has no existing branch

**Steps:**

1. User confirms they want to start from scratch
2. System creates and sets up a new branch

**Expected Result:**

* New branch is created
* Repository is initialized correctly

---

### TC-12: Explain Canvas Usage

**Preconditions:**

* New branch is active

**Steps:**

1. System explains how to use Canvas for:

    * Requirements
    * Entities
    * Workflows

**Expected Result:**

* User understands how to collaborate using Canvas

---

### TC-13: Offer Requirement Input Options (New Branch)

**Preconditions:**

* New branch is active

**Steps:**

1. System offers options to:

    * Generate requirements/entities/workflows
    * Attach files
    * Push manually (with path)

**Expected Result:**

* All options are clearly communicated

---

### TC-14: Save Generated Requirements to New Branch

**Preconditions:**

* User chooses to generate requirements

**Steps:**

1. System generates requirements/entities/workflows
2. Saves them to repository

**Expected Result:**

* Files are created in correct paths
* Canvas reflects saved content

---

### TC-15: Confirm Requirements Completion (New Branch)

**Preconditions:**

* Requirements exist in new branch

**Steps:**

1. System asks user to confirm requirements are complete

**Expected Result:**

* Build does not start without confirmation

---

## 4. Build & Deployment

### TC-16: Start Build Immediately After Confirmation

**Preconditions:**

* Requirements are confirmed complete

**Steps:**

1. System starts build automatically

**Expected Result:**

* Build process begins without further prompts

---

### TC-17: Use Correct Build Mode

**Preconditions:**

* Build is starting

**Steps:**

1. System selects build tool based on branch type

**Expected Result:**

* Existing branch:

    * Editing mode → `generate_application`
    * Full rebuild → `generate_code_with_cli`
* New branch:

    * Always `generate_application`

---

### TC-18: Offer Background Deployment

**Preconditions:**

* Build has started

**Steps:**

1. System offers to deploy in the background

**Expected Result:**

* User can accept or decline
* Build continues regardless

---

### TC-19: Notify About Tasks Panel Completion

**Preconditions:**

* Build is in progress

**Steps:**

1. System explains how to monitor progress

**Expected Result:**

* User knows to check the Tasks panel

---

### TC-20: Suggest Setup Assistant After Build

**Preconditions:**

* Build is complete

**Steps:**

1. System suggests calling the setup assistant

**Expected Result:**

* User understands next steps

---

### TC-21: Offer Deployment to Cyoda Environment

**Preconditions:**

* Build is complete

**Steps:**

1. System informs user they can request deployment

**Expected Result:**

* User knows deployment to a Cyoda environment is available

---

If you want, I can also:

* Convert these into **Gherkin (Given/When/Then)**
* Generate **automated test skeletons**
* Split them into **unit / integration / E2E test sets**
