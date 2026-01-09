"""
Test that coordinator routes credential requests to Environment Agent

This test verifies that when a user asks for credentials, the coordinator
properly routes the request to the environment agent, which then calls
ui_function_issue_technical_user and returns JSON.
"""
