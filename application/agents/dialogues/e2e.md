U: Hello! What to start with?

A: Hello! I am Cyoda AI Assistant. I can help you build and edit event-driven applications naturally.
I can also manage your Cyoda environment, answer your questions, and more.
We have 2 options of working together:
- You can ask me to build an application from scratch. For example, you can say: "Build a solution that enables customers to order products online."
- We can first work together on building your requirements: build requirements, add entities, workflows, etc. And then you can ask me to build the application from these sources.
- You can ask me to make changes to an existing application. For example, you can say: "Add a new entity to the existing application based on the attached branch."
- You can ask me to answer your questions about Cyoda. For example, you can say: "What is Cyoda?"

Which ways suite you best?

Scenario 1: User asks to build an application from scratch

U: I want to build an application from scratch. Can you help me?

A: Sure! Let's build an application from scratch. Please provide me with the requirements.

U: Build a solution that enables customers to order products online.

A: **[Cyoda AI Assistant → generate_application() tool]**
   **→ Returns: open_tasks_panel_hook, create_deploy_cyoda_environment_hook, create_launch_setup_assistant_hook**

Got it! I will build an application for you. Please wait a moment while I generate the code.
You can check the progress in the Tasks panel. Once ready please ask me to launch the setup assistant.
Meanwhile, I can deploy your Cyoda environment for you. Would you like me to do that?

U: Yes, please.

A: **[Cyoda AI Assistant → deploy_cyoda_environment() tool]**
   **→ Returns: deploy_and_open_cloud_hook, open_cloud_tab_hook**

Sure! I will deploy your Cyoda environment for you. Please wait a moment while I deploy it.
Once ready, you can access your environment in the cloud. You can track the progress in the Tasks panel.

U: My application is ready. Can you launch the setup assistant for me?

A: **[Cyoda AI Assistant → launch_setup_assistant() tool]**
   **→ Returns: launch_setup_assistant_hook, open_canvas_tab_hook**

Sure! I will launch the setup assistant for you. Please wait a moment while I launch it.
Once ready, you can access the setup assistant in the cloud. You can track the progress in the Tasks panel.

The query is passed to the Setup Assistant Agent. The assistant will guide the user through the setup process.

