# Gemini Integration Guidelines

This document outlines guidelines and best practices for integrating Gemini models into the Cyoda AI Studio project. Adhering to these guidelines will ensure efficient, reliable, and secure interactions with Gemini, leveraging its capabilities while maintaining project standards.

## 1. General Principles

*   **Prioritize Gemini Capabilities:** When interacting with AI models, prioritize Gemini's strengths, such as multimodal input, advanced reasoning, and structured output capabilities.
*   **Modularity:** Ensure Gemini-related logic is encapsulated and adheres to existing architectural patterns (e.g., coordinator-agent, service layers).
*   **Observability:** Implement robust logging and monitoring for Gemini interactions, including request/response payloads (sanitized for sensitive data), latency, and error rates.
*   **Cyoda Platform Context:** When integrating with Cyoda platform, always reference the documentation files in `llm_docs/outputs/`:
    *   `cyoda-api-sitemap-llms.txt` - API endpoint reference (79 endpoints)
    *   `cyoda-api-descriptions-llms.txt` - API section descriptions (13 categories)
    *   `cyoda-docs-llms.txt` - Platform documentation sitemap (105+ pages)

## 2. Project Structure and Code Organization

Gemini-related code should integrate seamlessly into the existing project structure.

*   **Dedicated Modules/Packages:** For significant Gemini-specific functionalities (e.g., custom model wrappers, prompt managers, response parsers), create dedicated modules or sub-packages within `application/agents/` or `application/services/`, following the existing naming conventions.
*   **Prompt Templates:** All prompt templates should reside in `application/agents/shared/prompts/` and be versioned and clearly named.
*   **Configuration:** Model configurations (e.g., API keys, model names, safety settings) should be managed centrally, ideally through environment variables or a configuration service, and not hardcoded.
*   **Tests:** Implement comprehensive unit and integration tests for all Gemini-related code, mirroring the project's testing methodology.

## 3. Code Standards and Quality

All code related to Gemini integration must adhere to the highest software engineering standards.

*   **PEP 8 Compliance:** Follow Python Enhancement Proposal 8 (PEP 8) for code style consistency. Utilize linters (e.g., `flake8`, `pylint`) and formatters (e.g., `black`, `isort`) to enforce this.
*   **Type Hinting:** Use type hints extensively for improved readability, maintainability, and early bug detection.
*   **SOLID Principles:** Apply SOLID principles (Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion) to design robust, flexible, and maintainable code.
*   **Clean Architecture:** Strive for clean architecture principles, ensuring clear separation of concerns between different layers (e.g., presentation, application, domain, infrastructure).
*   **Defensive Programming:** Implement defensive programming techniques, including input validation, error handling, and robust exception management, especially when interacting with external APIs.
*   **Documentation:** Provide clear and concise documentation for all functions, classes, and modules, explaining their purpose, parameters, return values, and any assumptions or side effects.
*   **Code Reviews:** All Gemini-related code must undergo thorough code reviews by experienced team members to ensure quality, adherence to standards, and security.

## 4. Model Interaction

The `CyodaAssistantWrapper` in `application/agents/cyoda_assistant.py` is the primary interface for AI model interactions.

*   **Model Selection:** Explicitly define which Gemini model (e.g., `gemini-pro`, `gemini-1.5-flash`) is being used and ensure it's configurable, ideally via environment variables or a dedicated configuration service.
*   **Error Handling & Retries:** Leverage the existing retry mechanisms. Implement specific error handling for Gemini API responses, distinguishing between transient and permanent errors.
*   **Timeout Management:** Configure appropriate timeouts for Gemini API calls to prevent long-running requests from blocking the system.
*   **Safety Settings:** Always include appropriate safety settings (e.g., `HARM_CATEGORY_HARASSMENT`, `HARM_CATEGORY_DANGEROUS_CONTENT`) in API requests to ensure responsible AI usage.

## 5. Prompt Engineering

Effective prompt engineering is crucial for guiding Gemini's behavior and obtaining desired outputs. Prompt templates are located in `application/agents/shared/prompts/`.

*   **Clarity and Specificity:** Prompts should be clear, concise, and explicit about the desired task, format, and constraints. Avoid ambiguity.
*   **Few-Shot Examples:** Where possible, include few-shot examples within the prompt to demonstrate the expected input and output format. This is particularly effective for guiding structured responses.
*   **Role Definition:** Clearly define the AI's persona or role within the prompt (e.g., "You are a helpful assistant that generates Python code...").
*   **Iterative Refinement:** Treat prompts as code. Regularly review, test, and refine prompts based on observed model behavior and evaluation results.
*   **UI Hooks Pattern:** Reinforce the project's "UI Hooks" pattern in prompts. Guide Gemini to generate responses that facilitate UI interactions (e.g., suggest specific button labels or actions) rather than open-ended questions when appropriate.

## 6. Data Handling & Context Management

`CyodaSessionService` in `application/services/cyoda_session_service.py` manages session persistence.

*   **Context Window Optimization:** Be mindful of Gemini's context window limits. Employ strategies like summarization, sliding windows, or hierarchical retrieval to manage conversation history efficiently without losing critical context.
*   **Data Privacy:** Never send sensitive, personally identifiable information (PII) or confidential data to Gemini unless absolutely necessary and with explicit user consent and appropriate legal safeguards. Redact or mask such data where possible.
*   **Session State:** Ensure that session-specific data passed to Gemini is correctly associated with the `CyodaSessionService` for persistence and retrieval across interactions.

## 7. Output Validation

Basic output validation is provided by `CyodaResponsePlugin` in `application/agents/shared/cyoda_response_plugin.py`.

*   **Structured Output:** For tasks requiring structured data, instruct Gemini to output in a specific format (e.g., JSON). Leverage Gemini's JSON mode when available to ensure valid JSON responses.
*   **Schema Validation:** Implement schema validation (e.g., using Pydantic or similar libraries) for structured outputs from Gemini to ensure they conform to expected data models.
*   **Semantic Validation:** Beyond format, validate the semantic correctness of Gemini's output where feasible. For instance, if Gemini generates code, attempt to lint or run basic tests on it.

## 8. Streaming

The project utilizes Server-Sent Events (SSE) for streaming (`application/routes/chat.py`, `application/config/streaming_config.py`).

*   **Chunk Handling:** Ensure the application correctly handles streamed chunks from Gemini, reassembling them into a complete response.
*   **Latency Management:** Optimize the streaming pipeline to minimize perceived latency for the end-user.
*   **Error Reporting:** Clearly communicate streaming errors to the client to provide a better user experience.

## 9. Tool Use (MCP Server)

The Cyoda MCP server (`cyoda_mcp/server.py`) exposes tools to the AI.

*   **Tool Definition:** Define tools clearly and precisely, with accurate descriptions of their functionality, parameters, and expected outputs, to help Gemini select and use them effectively.
*   **Parameter Schema:** Provide clear and strict schemas for tool parameters to guide Gemini in generating valid tool calls.
*   **Robust Tool Execution:** Ensure that the underlying implementations of the tools are robust, handle edge cases, and provide informative feedback to Gemini when errors occur.
*   **Security:** Exercise caution when exposing tools that can modify the system or access sensitive data. Implement appropriate authorization and validation for tool calls originating from Gemini.

## 9. Tool Use (MCP Server)

The Cyoda MCP server (`cyoda_mcp/server.py`) exposes tools to the AI.

*   **Tool Definition:** Define tools clearly and precisely, with accurate descriptions of their functionality, parameters, and expected outputs, to help Gemini select and use them effectively.
*   **Parameter Schema:** Provide clear and strict schemas for tool parameters to guide Gemini in generating valid tool calls.
*   **Robust Tool Execution:** Ensure that the underlying implementations of the tools are robust, handle edge cases, and provide informative feedback to Gemini when errors occur.
*   **Security:** Exercise caution when exposing tools that can modify the system or access sensitive data. Implement appropriate authorization and validation for tool calls originating from Gemini.

## 10. Best Practices for Tool Development (from `application/agents/environment/tools.py` analysis)

The `tools.py` file in `application/agents/environment/` serves as a practical example for implementing agent tools. The following best practices, derived from its analysis, should guide future tool development:

*   **Centralize API Client and Authentication:** Avoid repetitive `httpx.AsyncClient` initialization and token requests. Implement a dedicated client class for external services (e.g., `CloudManagerClient`) that handles client lifecycle, token caching, and refresh logic.
*   **Centralized Configuration:** All environment variables and magic values should be loaded and managed through a central configuration system (e.g., a Pydantic `BaseSettings` class or a dedicated `config.py` module). Avoid scattered `os.getenv()` calls.
*   **Consistent Error Reporting:** Standardize error responses across all tools. Return structured JSON messages (e.g., `{"error": "message", "code": "ERR_CODE"}`) for machine readability, rather than inconsistent plain strings or mixed formats.
*   **Module-Level Imports:** Place all `import` statements at the top of the file, following PEP 8. Avoid imports inside function bodies to prevent performance overhead and improve code clarity.
*   **Named Constants for Magic Values:** Replace magic strings and numbers (e.g., timeouts, truncation lengths, check intervals) with clearly named constants to enhance readability and maintainability.
*   **Robust Namespace Generation and Validation:** Implement comprehensive validation and sanitization for user-provided names (e.g., `env_name`, `app_name`) that are used in forming Kubernetes namespaces. Document any truncation or transformation logic clearly, and consider robust hashing or more sophisticated uniqueness checks if truncation is prone to collisions.
*   **Granular Error Handling and Logging:** Use specific exception types rather than broad `except Exception` clauses. Ensure all error logs provide sufficient context, including function names, relevant identifiers, and full exception details (`exc_info=True`). Review and refine logging levels (INFO, WARNING, ERROR) for accuracy.
*   **Structured Tool Context State:** While `tool_context.state` is for session management, avoid over-reliance without clear structure. Document the lifecycle and expected format of state variables. For complex states, consider using Pydantic models for validation and clarity.
*   **Adherence to SOLID Principles (Especially SRP):** Break down large, multi-responsibility functions into smaller, focused units. For instance, separate concerns like task creation, monitoring initiation, and UI hook generation into distinct, testable functions.
*   **Consider Event-Driven Monitoring:** For long-running operations, explore event-driven mechanisms (e.g., webhooks) from external services as an alternative or complement to polling, which can reduce API load and provide more real-time updates.
*   **Secure Credentials Management:** Reiterate that sensitive credentials (`CLOUD_MANAGER_API_KEY`, `CLOUD_MANAGER_API_SECRET`) must be managed securely (e.g., Kubernetes Secrets, Vault) and never hardcoded or committed to version control.

By following these guidelines, tool development will be more consistent, robust, and maintainable, contributing to the overall quality of the Cyoda AI Studio.

By following these guidelines, we can ensure that our integration with Gemini models is both powerful and responsible, contributing to the overall quality and reliability of the Cyoda AI Studio.

