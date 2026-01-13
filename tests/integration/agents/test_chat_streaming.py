"""
Integration test for chat streaming with SSE responses.

This test verifies that:
1. Chat creation works
2. Streaming responses are properly formatted
3. Messages are not concatenated without proper separation
4. Hooks are properly included in responses
5. Full end-to-end dialogue can be captured and saved as JSON
"""
