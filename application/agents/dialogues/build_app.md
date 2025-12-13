If the user wants to build an application, first identify (by asking or from the context) whether the user already has an existing branch where they want to continue building the application, or whether they want to start from scratch.

---

## If the user has an existing branch

1. Set up the repository using the identified branch.
2. Ask the user whether they want to:

    * Add additional requirements
    * Attach files
    * Generate requirements, entities, or workflows together
3. Inform the user where in the current repository they can manually push their requirements files, and provide the exact path.
4. If the user provides any requirements (as a file or as text), immediately save them to their branch and open the Canvas panel.
5. Once the user confirms that their requirements are complete, ask whether they want to proceed with:

    * **Editing mode** (`generate_application`), or
    * **Full new application mode** (`generate_code_with_cli`)

   Explain that editing mode implies substantial work is already implemented, and that their branch is not new.
6. Start building immediately.
7. Offer to start deployment in the background.
8. Suggest calling the setup assistant once the user sees in the Tasks panel that application building is complete.
9. Let the user know they can request deployment to a Cyoda environment once the build is finished.

---

## If the user does not have an existing branch

1. Set up the repository with a new branch.
2. Explain how to use Canvas to work on requirements, entities, and workflows.
3. Inform the user that you can:

    * Generate requirements, entities, and workflows together and save them to the repository
    * Accept attached files and save them to the repository
    * Allow them to push files manually (provide the repository path)
4. Once the user confirms that the requirements are complete, start building immediately.
5. This will be done in **full new application mode** (`generate_application`).
6. Offer to start deployment in the background.
7. Suggest calling the setup assistant once the user sees in the Tasks panel that application building is complete.
8. Let the user know they can request deployment to a Cyoda environment once the build is finished.
