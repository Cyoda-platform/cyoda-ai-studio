#!/bin/bash
# Launch ADK Web UI for interactive agent testing

export DISABLE_MCP_TOOLSET=true
export MOCK_ALL_TOOLS=false  # Set to false for real interaction, true for mocking

echo "🚀 Launching ADK Web UI for Cyoda AI Assistant..."
echo "📍 URL: http://127.0.0.1:8080"
echo "🛑 Press Ctrl+C to stop"
echo ""

adk web application/agents \
  --port 8080 \
  --reload \
  --logo-text "Cyoda AI Assistant" \
  --session_service_uri "sqlite://application/agents/.adk/sessions.db" \
  --artifact_service_uri "file://application/agents/.adk/artifacts"
