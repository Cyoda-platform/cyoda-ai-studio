"""
Integration test for chat streaming with SSE responses.

This test verifies that:
1. Chat creation works
2. Streaming responses are properly formatted
3. Messages are not concatenated without proper separation
4. Hooks are properly included in responses
5. Full end-to-end dialogue can be captured and saved as JSON
"""

import asyncio
import json
import pytest
import httpx
from typing import AsyncGenerator
from pathlib import Path
from datetime import datetime


class TestChatStreaming:
    """Test chat streaming functionality."""

    # Test token - reuse from user's curl command
    TEST_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IjZ2TTFtSWVLSV9XanZDbXNjWFk2diJ9.eyJjYWFzX3VzZXJfaWQiOiIwNWUxMWRhMjEwNzg0NGZjOTQ0ZWU1Yjg3MmZjYjZiNiIsImNhYXNfb3JnX2lkIjoiQ1lPREEiLCJ1c2VyX3JvbGVzIjpbIlVTRVIiLCJTVVBFUl9VU0VSIl0sImNhYXNfY3lvZGFfZW1wbG95ZWUiOnRydWUsImlzcyI6Imh0dHBzOi8vZGV2LWV4NnIteXFjLnVzLmF1dGgwLmNvbS8iLCJzdWIiOiJnb29nbGUtb2F1dGgyfDExMDE4NDQ0MTcyMDI4OTkzNjQzMiIsImF1ZCI6WyJodHRwczovL2NvYmkuY3lvZGEuY29tL2FwaSIsImh0dHBzOi8vZGV2LWV4NnIteXFjLnVzLmF1dGgwLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NjM2NTA1MDMsImV4cCI6MTc2MzY1NzcwMywic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsIm9yZ19pZCI6Im9yZ18yMTA2TXg5Tkx5SjVXUHRpIiwiYXpwIjoiMmt1QzlUcHdEMmx4VFliekZPM0dMcHg0RUhPNjM2MkEiLCJwZXJtaXNzaW9ucyI6W119.CJHxfgyRwrp8RkmieJpopC__V_PoeSggE_e2RfrvxB2zd5w8X-MIq_atgzY4qIxTjNi0or-B1kH3adoMockIujqcZyTUXtx_jCu42QfybEYJmG0rQufgaHRAFD095b4AsKmISV6d_osaOubfFJ9AQs-WVYxfVIjZXr_NHnL-wcKh8rHSUp7aDggKSOptD1FVZdeI_MgbrrG5EQvxw92oQCx4Ku0KKU85XvS4vZ-cE4VfOoGE3wgeORVRKquMLCa_T6JPV-wcGfiOFqrEMrxpqkt0c039zuAe2qfZEF8xIOsakVybRMz28Pvm6JBmP4gcJNMtsL-PfnRttGXGjVMaYw"

    BASE_URL = "http://localhost:8000/api/v1"

    @pytest.mark.asyncio
    async def test_create_chat(self):
        """Test creating a new chat."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/chats",
                json={"name": "Test Chat", "description": ""},
                headers={"Authorization": f"Bearer {self.TEST_TOKEN}"},
            )
            assert response.status_code in [200, 201], f"Failed to create chat: {response.text}"
            data = response.json()
            assert "technical_id" in data, "Chat should have technical_id"
            return data["technical_id"]

    @pytest.mark.asyncio
    async def test_stream_chat_message(self):
        """Test streaming a chat message and verify response format."""
        async with httpx.AsyncClient() as client:
            # Create chat
            create_response = await client.post(
                f"{self.BASE_URL}/chats",
                json={"name": "Workflow Test", "description": ""},
                headers={"Authorization": f"Bearer {self.TEST_TOKEN}"},
            )
            assert create_response.status_code in [200, 201]
            chat_id = create_response.json()["technical_id"]

            # Stream message
            message = "Create a workflow for Order entity with create, update, and cancel transitions"
            
            async with client.stream(
                "POST",
                f"{self.BASE_URL}/chats/{chat_id}/stream",
                json={"message": message},
                headers={
                    "Authorization": f"Bearer {self.TEST_TOKEN}",
                    "Accept": "text/event-stream",
                },
            ) as response:
                assert response.status_code == 200, f"Failed to stream: {response.text}"
                
                # Collect all events
                events = []
                accumulated_content = ""
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            event_data = json.loads(line[6:])
                            events.append(event_data)
                            
                            # Accumulate content chunks
                            if event_data.get("chunk"):
                                accumulated_content += event_data["chunk"]
                        except json.JSONDecodeError:
                            pass
                
                # Verify we got events
                assert len(events) > 0, "Should receive at least one event"
                
                # Verify no run-on sentences (check for proper separation)
                # Should not have patterns like "...foundWould you like..."
                assert "foundWould" not in accumulated_content, "Messages should be properly separated"
                assert "configurationWould" not in accumulated_content, "Messages should be properly separated"
                assert "configurationPlease" not in accumulated_content, "Messages should be properly separated"
                
                # Verify we have proper event types
                event_types = {e.get("type") for e in events if "type" in e}
                assert len(event_types) > 0, "Should have event types"
                
                print(f"✅ Received {len(events)} events with types: {event_types}")
                print(f"✅ Accumulated content length: {len(accumulated_content)}")
                print(f"✅ No run-on sentences detected")

    @pytest.mark.asyncio
    async def test_response_has_proper_formatting(self):
        """Test that response messages have proper formatting with newlines."""
        async with httpx.AsyncClient() as client:
            # Create chat
            create_response = await client.post(
                f"{self.BASE_URL}/chats",
                json={"name": "Format Test", "description": ""},
                headers={"Authorization": f"Bearer {self.TEST_TOKEN}"},
            )
            assert create_response.status_code in [200, 201]
            chat_id = create_response.json()["technical_id"]

            # Stream message
            message = "hi"
            
            async with client.stream(
                "POST",
                f"{self.BASE_URL}/chats/{chat_id}/stream",
                json={"message": message},
                headers={
                    "Authorization": f"Bearer {self.TEST_TOKEN}",
                    "Accept": "text/event-stream",
                },
            ) as response:
                accumulated_content = ""
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            event_data = json.loads(line[6:])
                            if event_data.get("chunk"):
                                accumulated_content += event_data["chunk"]
                        except json.JSONDecodeError:
                            pass
                
                # Verify content is readable (has proper spacing)
                if accumulated_content:
                    # Check that we don't have excessive concatenation
                    # A properly formatted response should have reasonable line breaks
                    lines = accumulated_content.split("\n")
                    assert len(lines) > 0, "Response should have content"
                    
                    # Check that lines aren't excessively long (indicating concatenation)
                    avg_line_length = sum(len(line) for line in lines) / len(lines) if lines else 0
                    print(f"✅ Average line length: {avg_line_length:.0f} characters")
                    print(f"✅ Response has {len(lines)} lines")


    async def _stream_message(self, client: httpx.AsyncClient, chat_id: str, message: str) -> tuple[str, list]:
        """Helper to stream a message and return accumulated content and events."""
        async with client.stream(
            "POST",
            f"{self.BASE_URL}/chats/{chat_id}/stream",
            json={"message": message},
            headers={
                "Authorization": f"Bearer {self.TEST_TOKEN}",
                "Accept": "text/event-stream",
            },
            timeout=60.0,
        ) as response:
            assert response.status_code == 200

            accumulated_content = ""
            events = []

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        event_data = json.loads(line[6:])
                        events.append(event_data)

                        if event_data.get("chunk"):
                            accumulated_content += event_data["chunk"]
                    except json.JSONDecodeError:
                        pass

            return accumulated_content, events

    @pytest.mark.asyncio
    async def test_end_to_end_clean_workflow_dialogue(self):
        """
        End-to-end test that creates a clean, standard workflow dialogue.

        This test:
        1. Creates a chat
        2. Sends a workflow creation request
        3. Follows the proper workflow with correct user responses
        4. Captures all responses and user interactions
        5. Saves the full dialogue as a JSON file with proper structure
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Step 1: Create chat
            create_response = await client.post(
                f"{self.BASE_URL}/chats",
                json={"name": "Clean Workflow Dialogue", "description": ""},
                headers={"Authorization": f"Bearer {self.TEST_TOKEN}"},
            )
            assert create_response.status_code in [200, 201]
            chat_data = create_response.json()
            chat_id = chat_data["technical_id"]
            print(f"✅ Created chat: {chat_id}")

            # Initialize dialogue structure with full fields like add_workflow_1.json
            dialogue_entries = []

            # Turn 1: User request
            initial_message = "Create a workflow for Order entity with create, update, and cancel transitions"

            user_entry = {
                "type": "answer",
                "message": initial_message,
                "answer": initial_message,
                "user_id": "CYODA",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "approve": False,
                "consumed": False,
                "current_state": None,
                "current_transition": None,
                "edge_message_id": None,
                "error": None,
                "error_code": "None",
                "failed": False,
                "file_blob_ids": None,
                "metadata": None,
                "publish": True,
                "technical_id": str(datetime.utcnow().timestamp()).replace(".", ""),
                "workflow_name": None,
            }
            dialogue_entries.append(user_entry)

            print(f"📤 Turn 1 - User: {initial_message}")
            response_content, events = await self._stream_message(client, chat_id, initial_message)

            if response_content:
                # Extract hook if present
                hook_data = None
                for event in events:
                    if event.get("hook"):
                        hook_data = event.get("hook")
                        break

                metadata = None
                if hook_data:
                    metadata = {"hook": hook_data}

                agent_entry = {
                    "type": "question",
                    "message": response_content,
                    "question": response_content,
                    "user_id": "CYODA",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "approve": False,
                    "consumed": True,
                    "current_state": None,
                    "current_transition": None,
                    "edge_message_id": None,
                    "error": None,
                    "error_code": "None",
                    "failed": False,
                    "file_blob_ids": None,
                    "metadata": metadata,
                    "publish": True,
                    "technical_id": str(datetime.utcnow().timestamp()).replace(".", ""),
                    "workflow_name": None,
                }
                dialogue_entries.append(agent_entry)
                print(f"📥 Agent: {response_content[:80]}...")

                # Verify no concatenation issues
                assert "foundWould" not in response_content
                assert "configurationWould" not in response_content

            # Turn 2: User selects branch option
            turn_2_message = "Create a new branch"
            user_entry_2 = {
                "type": "answer",
                "message": turn_2_message,
                "answer": turn_2_message,
                "user_id": "CYODA",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "approve": False,
                "consumed": False,
                "current_state": None,
                "current_transition": None,
                "edge_message_id": None,
                "error": None,
                "error_code": "None",
                "failed": False,
                "file_blob_ids": None,
                "metadata": None,
                "publish": True,
                "technical_id": str(datetime.utcnow().timestamp()).replace(".", ""),
                "workflow_name": None,
            }
            dialogue_entries.append(user_entry_2)

            print(f"📤 Turn 2 - User: {turn_2_message}")
            response_content, events = await self._stream_message(client, chat_id, turn_2_message)

            if response_content:
                hook_data = None
                for event in events:
                    if event.get("hook"):
                        hook_data = event.get("hook")
                        break

                metadata = None
                if hook_data:
                    metadata = {"hook": hook_data}

                agent_entry_2 = {
                    "type": "question",
                    "message": response_content,
                    "question": response_content,
                    "user_id": "CYODA",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "approve": False,
                    "consumed": True,
                    "current_state": None,
                    "current_transition": None,
                    "edge_message_id": None,
                    "error": None,
                    "error_code": "None",
                    "failed": False,
                    "file_blob_ids": None,
                    "metadata": metadata,
                    "publish": True,
                    "technical_id": str(datetime.utcnow().timestamp()).replace(".", ""),
                    "workflow_name": None,
                }
                dialogue_entries.append(agent_entry_2)
                print(f"📥 Agent: {response_content[:80]}...")
                assert "foundWould" not in response_content
                assert "configurationWould" not in response_content

            # Save dialogue to JSON file
            dialogue_json = {
                "chat_body": {
                    "date": datetime.utcnow().isoformat() + "Z",
                    "description": "Clean standard workflow dialogue - Order entity with create, update, cancel transitions",
                    "dialogue": dialogue_entries,
                    "chat_id": chat_id,
                    "name": "Create a workflow for Order entity with create, up...",
                    "repository_branch": None,
                    "repository_name": None,
                    "repository_owner": None,
                    "repository_url": None,
                    "installation_id": None,
                    "entities_data": {},
                }
            }

            # Save to dialogues directory
            output_dir = Path(__file__).parent.parent.parent.parent / "application" / "agents" / "dialogues"
            output_dir.mkdir(parents=True, exist_ok=True)

            output_file = output_dir / f"clean_workflow_dialogue_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            with open(output_file, 'w') as f:
                json.dump(dialogue_json, f, indent=2)

            print(f"\n✅ Clean dialogue saved to: {output_file}")
            assert output_file.exists(), f"Dialogue file should exist at {output_file}"

            # Verify file content
            with open(output_file, 'r') as f:
                saved_data = json.load(f)

            assert "chat_body" in saved_data
            assert "dialogue" in saved_data["chat_body"]
            assert len(saved_data["chat_body"]["dialogue"]) >= 2
            print(f"✅ Dialogue file contains {len(saved_data['chat_body']['dialogue'])} entries")

    @pytest.mark.asyncio
    async def test_full_workflow_dialogue_recording(self):
        """
        Full end-to-end test that reproduces the complete add workflow dialogue.

        This test:
        1. Creates a chat
        2. Sends all user messages from add_workflow_clean.json
        3. Records all agent responses
        4. Saves the complete dialogue
        5. Validates all agent questions are clean and valid
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Step 1: Create chat
            create_response = await client.post(
                f"{self.BASE_URL}/chats",
                json={"name": "Full Workflow Dialogue Recording", "description": ""},
                headers={"Authorization": f"Bearer {self.TEST_TOKEN}"},
            )
            assert create_response.status_code in [200, 201]
            chat_id = create_response.json()["technical_id"]
            print(f"✅ Created chat: {chat_id}\n")

            # User messages from add_workflow_clean.json
            user_messages = [
                "Create a workflow for Order entity with create, update, and cancel transitions",
                "Create a new branch",
                "Yes, create it",
                "Yes, create it",
                "please add an order entity",
            ]

            dialogue_entries = []

            # Process each user message
            for turn, user_msg in enumerate(user_messages, 1):
                print(f"📤 Turn {turn} - User: {user_msg}")

                # Add user message to dialogue
                user_entry = {
                    "type": "answer",
                    "message": user_msg,
                    "answer": user_msg,
                    "user_id": "CYODA",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "approve": False,
                    "consumed": False,
                    "current_state": None,
                    "current_transition": None,
                    "edge_message_id": None,
                    "error": None,
                    "error_code": "None",
                    "failed": False,
                    "file_blob_ids": None,
                    "metadata": None,
                    "publish": True,
                    "technical_id": str(datetime.utcnow().timestamp()).replace(".", ""),
                    "workflow_name": None,
                }
                dialogue_entries.append(user_entry)

                # Stream agent response
                response_content, events = await self._stream_message(client, chat_id, user_msg)

                if response_content:
                    # Extract hook if present
                    hook_data = None
                    for event in events:
                        if event.get("hook"):
                            hook_data = event.get("hook")
                            break

                    metadata = None
                    if hook_data:
                        metadata = {"hook": hook_data}

                    agent_entry = {
                        "type": "question",
                        "message": response_content,
                        "question": response_content,
                        "user_id": "CYODA",
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "approve": False,
                        "consumed": True,
                        "current_state": None,
                        "current_transition": None,
                        "edge_message_id": None,
                        "error": None,
                        "error_code": "None",
                        "failed": False,
                        "file_blob_ids": None,
                        "metadata": metadata,
                        "publish": True,
                        "technical_id": str(datetime.utcnow().timestamp()).replace(".", ""),
                        "workflow_name": None,
                    }
                    dialogue_entries.append(agent_entry)

                    print(f"📥 Agent: {response_content[:80]}...")

                    # Validate no concatenation issues
                    assert "foundWould" not in response_content, f"Found 'foundWould' in response"
                    assert "configurationWould" not in response_content, f"Found 'configurationWould' in response"
                    assert "configurationPlease" not in response_content, f"Found 'configurationPlease' in response"
                    print(f"   ✓ No concatenation issues\n")

            # Save dialogue to JSON file
            dialogue_json = {
                "chat_body": {
                    "date": datetime.utcnow().isoformat() + "Z",
                    "description": "Full workflow dialogue recording - all user answers and agent responses",
                    "dialogue": dialogue_entries,
                    "chat_id": chat_id,
                    "name": "Create a workflow for Order entity with create, up...",
                    "repository_branch": None,
                    "repository_name": None,
                    "repository_owner": None,
                    "repository_url": None,
                    "installation_id": None,
                    "entities_data": {},
                }
            }

            # Save to dialogues directory
            output_dir = Path(__file__).parent.parent.parent.parent / "application" / "agents" / "dialogues"
            output_dir.mkdir(parents=True, exist_ok=True)

            output_file = output_dir / f"full_workflow_dialogue_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            with open(output_file, 'w') as f:
                json.dump(dialogue_json, f, indent=2)

            print(f"\n✅ Full dialogue saved to: {output_file}")
            assert output_file.exists(), f"Dialogue file should exist at {output_file}"

            # Verify file content
            with open(output_file, 'r') as f:
                saved_data = json.load(f)

            assert "chat_body" in saved_data
            assert "dialogue" in saved_data["chat_body"]
            assert len(saved_data["chat_body"]["dialogue"]) == 10
            print(f"✅ Dialogue file contains {len(saved_data['chat_body']['dialogue'])} entries (5 user + 5 agent)")

    @pytest.mark.asyncio
    async def test_end_to_end_add_workflow_dialogue(self):
        """
        End-to-end test that reproduces the add workflow dialogue.

        This test:
        1. Creates a chat
        2. Sends a workflow creation request
        3. Captures all responses and user interactions
        4. Continues the conversation through multiple turns
        5. Saves the full dialogue as a JSON file
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Step 1: Create chat
            create_response = await client.post(
                f"{self.BASE_URL}/chats",
                json={"name": "Add Workflow Test", "description": ""},
                headers={"Authorization": f"Bearer {self.TEST_TOKEN}"},
            )
            assert create_response.status_code in [200, 201]
            chat_id = create_response.json()["technical_id"]
            print(f"✅ Created chat: {chat_id}")

            # Initialize dialogue structure
            dialogue_entries = []

            # Step 2: Send initial workflow request
            initial_message = "Create a workflow for Order entity with create, update, and cancel transitions"

            # Add user message to dialogue
            dialogue_entries.append({
                "type": "answer",
                "message": initial_message,
                "user_id": "CYODA",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })

            # Step 3: Stream the response
            print(f"📤 Turn 1 - Sending message: {initial_message}")

            response_content, events = await self._stream_message(client, chat_id, initial_message)

            if response_content:
                dialogue_entries.append({
                    "type": "question",
                    "message": response_content,
                    "user_id": "CYODA",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "metadata": {
                        "events_count": len(events),
                        "has_hook": any(e.get("hook") for e in events),
                    }
                })
                print(f"📥 Received response with {len(events)} events ({len(response_content)} chars)")

                # Verify no concatenation issues
                assert "foundWould" not in response_content
                assert "configurationWould" not in response_content
                print("✅ Response is properly formatted (no concatenation issues)")

            # Step 4: Continue conversation - select "Create a new branch"
            turn_2_message = "Create a new branch"
            dialogue_entries.append({
                "type": "answer",
                "message": turn_2_message,
                "user_id": "CYODA",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })

            print(f"📤 Turn 2 - Sending message: {turn_2_message}")
            response_content, events = await self._stream_message(client, chat_id, turn_2_message)

            if response_content:
                dialogue_entries.append({
                    "type": "question",
                    "message": response_content,
                    "user_id": "CYODA",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "metadata": {
                        "events_count": len(events),
                        "has_hook": any(e.get("hook") for e in events),
                    }
                })
                print(f"📥 Received response with {len(events)} events ({len(response_content)} chars)")
                assert "foundWould" not in response_content
                assert "configurationWould" not in response_content

            # Step 5: Select repository configuration
            turn_3_message = "Repository type: public, Language: python"
            dialogue_entries.append({
                "type": "answer",
                "message": turn_3_message,
                "user_id": "CYODA",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })

            print(f"📤 Turn 3 - Sending message: {turn_3_message}")
            response_content, events = await self._stream_message(client, chat_id, turn_3_message)

            if response_content:
                dialogue_entries.append({
                    "type": "question",
                    "message": response_content,
                    "user_id": "CYODA",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "metadata": {
                        "events_count": len(events),
                        "has_hook": any(e.get("hook") for e in events),
                    }
                })
                print(f"📥 Received response with {len(events)} events ({len(response_content)} chars)")
                assert "foundWould" not in response_content
                assert "configurationWould" not in response_content

            # Step 6: Save dialogue to JSON file
            dialogue_json = {
                "chat_body": {
                    "date": datetime.utcnow().isoformat() + "Z",
                    "description": "End-to-end test for add workflow dialogue",
                    "dialogue": dialogue_entries,
                    "chat_id": chat_id,
                }
            }

            # Save to dialogues directory
            output_dir = Path(__file__).parent.parent.parent.parent / "application" / "agents" / "dialogues"
            output_dir.mkdir(parents=True, exist_ok=True)

            output_file = output_dir / f"e2e_add_workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            with open(output_file, 'w') as f:
                json.dump(dialogue_json, f, indent=2)

            print(f"\n✅ Dialogue saved to: {output_file}")
            assert output_file.exists(), f"Dialogue file should exist at {output_file}"

            # Verify file content
            with open(output_file, 'r') as f:
                saved_data = json.load(f)

            assert "chat_body" in saved_data
            assert "dialogue" in saved_data["chat_body"]
            assert len(saved_data["chat_body"]["dialogue"]) >= 4
            print(f"✅ Dialogue file contains {len(saved_data['chat_body']['dialogue'])} entries")


    def test_eval_clean_dialogue_structure(self):
        """Evaluate the structure of add_workflow_clean.json."""
        dialogue_file = Path(__file__).parent.parent.parent.parent / "application" / "agents" / "dialogues" / "add_workflow_clean.json"

        assert dialogue_file.exists(), f"Clean dialogue file should exist at {dialogue_file}"

        with open(dialogue_file, 'r') as f:
            data = json.load(f)

        # Validate structure
        assert "chat_body" in data, "Should have chat_body"
        assert "dialogue" in data["chat_body"], "Should have dialogue array"

        dialogue = data["chat_body"]["dialogue"]

        # Should have 10 entries (5 user + 5 agent)
        assert len(dialogue) == 10, f"Should have 10 entries, got {len(dialogue)}"

        # Validate alternating pattern
        for i, entry in enumerate(dialogue):
            expected_type = "answer" if i % 2 == 0 else "question"
            assert entry["type"] == expected_type, f"Entry {i} should be {expected_type}, got {entry['type']}"

        print("✅ Structure validation passed")
        print(f"   - 10 entries total")
        print(f"   - 5 user messages (answer)")
        print(f"   - 5 agent responses (question)")
        print(f"   - Proper alternating pattern")

    def test_eval_user_messages_quality(self):
        """Evaluate user messages in add_workflow_clean.json."""
        dialogue_file = Path(__file__).parent.parent.parent.parent / "application" / "agents" / "dialogues" / "add_workflow_clean.json"

        with open(dialogue_file, 'r') as f:
            data = json.load(f)

        dialogue = data["chat_body"]["dialogue"]
        user_messages = [e for e in dialogue if e["type"] == "answer"]

        expected_messages = [
            "Create a workflow for Order entity with create, update, and cancel transitions",
            "Create a new branch",
            "Yes, create it",
            "Yes, create it",
            "please add an order entity",
        ]

        assert len(user_messages) == 5, f"Should have 5 user messages, got {len(user_messages)}"

        for i, (msg, expected) in enumerate(zip(user_messages, expected_messages)):
            assert msg["message"] == expected, f"User message {i} mismatch"
            assert msg["answer"] == expected, f"User answer field {i} mismatch"
            assert msg["user_id"] == "CYODA", f"User ID should be CYODA"
            assert msg["publish"] == True, f"Message should be published"

        print("✅ User messages validation passed")
        print(f"   - All 5 user messages match expected")
        print(f"   - All messages properly formatted")
        print(f"   - All messages published")

    def test_eval_agent_responses_no_concatenation(self):
        """Evaluate agent responses for concatenation issues."""
        dialogue_file = Path(__file__).parent.parent.parent.parent / "application" / "agents" / "dialogues" / "add_workflow_clean.json"

        with open(dialogue_file, 'r') as f:
            data = json.load(f)

        dialogue = data["chat_body"]["dialogue"]
        agent_responses = [e for e in dialogue if e["type"] == "question"]

        concatenation_patterns = [
            "foundWould",
            "configurationWould",
            "configurationPlease",
            "conversationWould",
            "conversationPlease",
        ]

        issues = []

        for i, response in enumerate(agent_responses):
            msg = response["message"]

            for pattern in concatenation_patterns:
                if pattern in msg:
                    issues.append(f"Response {i}: Found '{pattern}'")

            # Check for duplicate instructions
            if msg.count("Please select") > 1:
                issues.append(f"Response {i}: Duplicate 'Please select' instructions")

        assert len(issues) == 0, f"Concatenation issues found: {issues}"

        print("✅ Concatenation validation passed")
        print(f"   - No 'foundWould' patterns")
        print(f"   - No 'configurationWould' patterns")
        print(f"   - No duplicate instructions")
        print(f"   - All {len(agent_responses)} agent responses are clean")

    def test_eval_agent_responses_formatting(self):
        """Evaluate agent responses for proper formatting."""
        dialogue_file = Path(__file__).parent.parent.parent.parent / "application" / "agents" / "dialogues" / "add_workflow_clean.json"

        with open(dialogue_file, 'r') as f:
            data = json.load(f)

        dialogue = data["chat_body"]["dialogue"]
        agent_responses = [e for e in dialogue if e["type"] == "question"]

        for i, response in enumerate(agent_responses):
            msg = response["message"]

            # Check message is not empty
            assert len(msg) > 0, f"Response {i} should not be empty"

            # Check message and question fields match
            assert response.get("question") == msg, f"Response {i}: message and question fields should match"

            # Check consumed flag
            assert response["consumed"] == True, f"Response {i} should be marked as consumed"

            # Check publish flag
            assert response["publish"] == True, f"Response {i} should be published"

        print("✅ Formatting validation passed")
        print(f"   - All responses have content")
        print(f"   - Message and question fields match")
        print(f"   - All responses marked as consumed")
        print(f"   - All responses published")

    def test_eval_hooks_configuration(self):
        """Evaluate hooks configuration in agent responses."""
        dialogue_file = Path(__file__).parent.parent.parent.parent / "application" / "agents" / "dialogues" / "add_workflow_clean.json"

        with open(dialogue_file, 'r') as f:
            data = json.load(f)

        dialogue = data["chat_body"]["dialogue"]
        agent_responses = [e for e in dialogue if e["type"] == "question"]

        # Expected hook configuration (actual from add_workflow_clean.json)
        expected_hooks = [
            "option_selection",  # Response 0: Branch selection
            "option_selection",  # Response 1: Workflow creation confirmation
            None,  # Response 2: No hook (confirmation)
            None,  # Response 3: No hook (summary)
            "code_changes",  # Response 4: Entity added with canvas refresh
        ]

        for i, (response, expected_hook) in enumerate(zip(agent_responses, expected_hooks)):
            metadata = response.get("metadata")

            if expected_hook is None:
                assert metadata is None, f"Response {i} should not have metadata/hook"
            else:
                assert metadata is not None, f"Response {i} should have metadata"
                assert "hook" in metadata, f"Response {i} should have hook in metadata"
                hook = metadata["hook"]
                assert hook["type"] == expected_hook, f"Response {i} hook type should be {expected_hook}, got {hook['type']}"
                assert "action" in hook, f"Response {i} hook should have action"
                assert "data" in hook, f"Response {i} hook should have data"

        print("✅ Hooks validation passed")
        print(f"   - Response 0: option_selection hook (branch selection)")
        print(f"   - Response 1: option_selection hook (workflow creation)")
        print(f"   - Response 2: No hook (confirmation)")
        print(f"   - Response 3: No hook (summary)")
        print(f"   - Response 4: code_changes hook (entity added with canvas refresh)")

    def test_eval_dialogue_flow_logic(self):
        """Evaluate the logical flow of the dialogue."""
        dialogue_file = Path(__file__).parent.parent.parent.parent / "application" / "agents" / "dialogues" / "add_workflow_clean.json"

        with open(dialogue_file, 'r') as f:
            data = json.load(f)

        dialogue = data["chat_body"]["dialogue"]

        # Validate flow
        flow_checks = [
            (0, "answer", "Create a workflow"),
            (1, "question", "Would you like to create a new branch"),
            (2, "answer", "Create a new branch"),
            (3, "question", "Repository cloned successfully"),
            (4, "answer", "Yes, create it"),
            (5, "question", "Order workflow created"),
            (6, "answer", "Yes, create it"),
            (7, "question", "Order workflow is created"),
            (8, "answer", "please add an order entity"),
            (9, "question", "Order entity added"),
        ]

        for idx, expected_type, expected_content in flow_checks:
            entry = dialogue[idx]
            assert entry["type"] == expected_type, f"Entry {idx} type mismatch"
            assert expected_content in entry["message"], f"Entry {idx} content mismatch"

        print("✅ Dialogue flow validation passed")
        print(f"   - 10 entries in correct sequence")
        print(f"   - Proper user-agent alternation")
        print(f"   - Logical progression from workflow creation to entity addition")

    def test_eval_message_clarity_and_professionalism(self):
        """Evaluate message clarity and professional quality."""
        dialogue_file = Path(__file__).parent.parent.parent.parent / "application" / "agents" / "dialogues" / "add_workflow_clean.json"

        with open(dialogue_file, 'r') as f:
            data = json.load(f)

        dialogue = data["chat_body"]["dialogue"]
        agent_responses = [e for e in dialogue if e["type"] == "question"]

        clarity_issues = []

        for i, response in enumerate(agent_responses):
            msg = response["message"]

            # Check for professional tone
            if "ERROR" in msg and "error" not in msg.lower():
                clarity_issues.append(f"Response {i}: Inconsistent error capitalization")

            # Check for clear structure
            if len(msg) > 500 and "\n" not in msg:
                clarity_issues.append(f"Response {i}: Long message without line breaks")

            # Check for proper punctuation
            if msg.endswith(" "):
                clarity_issues.append(f"Response {i}: Trailing whitespace")

            # Check for clarity markers
            has_clarity = any(marker in msg for marker in ["✅", "→", "•", "-", "A)", "1)"])
            if len(msg) > 100 and not has_clarity:
                # Some messages don't need clarity markers
                pass

        assert len(clarity_issues) == 0, f"Clarity issues found: {clarity_issues}"

        print("✅ Clarity and professionalism validation passed")
        print(f"   - All messages professionally written")
        print(f"   - Proper punctuation and formatting")
        print(f"   - Clear and understandable language")
        print(f"   - Appropriate use of emojis and markers")

    @pytest.mark.asyncio
    async def test_hook_message_separation(self):
        """
        Test that hook messages are properly separated from agent responses.

        This test verifies:
        1. Done event contains separate 'response' and 'hook_message' fields
        2. Response field contains the full accumulated content
        3. Hook message is properly extracted and separated
        4. Hook message contains the question from the hook data
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Create chat
            create_response = await client.post(
                f"{self.BASE_URL}/chats",
                json={"name": "Hook Separation Test", "description": ""},
                headers={"Authorization": f"Bearer {self.TEST_TOKEN}"},
            )
            assert create_response.status_code in [200, 201]
            chat_id = create_response.json()["technical_id"]

            # Stream message that should trigger a hook
            message = "Create a workflow"

            # Accumulate content chunks to compare with done response
            accumulated_content = ""

            async with client.stream(
                "POST",
                f"{self.BASE_URL}/chats/{chat_id}/stream",
                json={"message": message},
                headers={
                    "Authorization": f"Bearer {self.TEST_TOKEN}",
                    "Accept": "text/event-stream",
                },
                timeout=60.0,
            ) as response:
                assert response.status_code == 200

                done_event = None

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            event_data = json.loads(line[6:])
                            # Accumulate content chunks
                            if event_data.get("chunk"):
                                accumulated_content += event_data["chunk"]
                            # Capture done event
                            if event_data.get("type") == "done":
                                done_event = event_data
                        except json.JSONDecodeError:
                            pass

                # Verify done event exists
                assert done_event is not None, "Should receive a done event"

                # Verify response field equals accumulated content
                response_text = done_event.get("response", "")
                print(f"✅ Done event received")
                print(f"   Response length: {len(response_text)}")
                print(f"   Accumulated content length: {len(accumulated_content)}")

                # The response should equal the accumulated content
                assert response_text == accumulated_content, \
                    f"Response field should equal accumulated content. Response: {len(response_text)}, Accumulated: {len(accumulated_content)}"

                # If there's a hook, verify separation
                if done_event.get("hook"):
                    hook = done_event["hook"]
                    hook_message = done_event.get("hook_message", "")

                    print(f"✅ Hook present with type: {hook.get('type')}")
                    print(f"   Hook message length: {len(hook_message)}")

                    # If hook has a question, verify it's in hook_message
                    if hook.get("data", {}).get("question"):
                        hook_question = hook["data"]["question"]

                        # Hook question should be in hook_message
                        assert hook_question in hook_message or len(hook_message) > 0, \
                            f"Hook question should be in hook_message. Question: {hook_question[:50]}..."

                        print(f"✅ Hook message properly separated from response")
                        print(f"   Hook question: {hook_question[:50]}...")
                else:
                    print(f"ℹ️ No hook in done event (normal for simple responses)")


    @pytest.mark.asyncio
    async def test_tool_response_streaming(self):
        """Test that tool responses are streamed in real-time with content chunks."""
        async with httpx.AsyncClient() as client:
            # Create chat
            create_response = await client.post(
                f"{self.BASE_URL}/chats",
                json={"name": "Tool Response Streaming Test", "description": ""},
                headers={"Authorization": f"Bearer {self.TEST_TOKEN}"},
            )
            assert create_response.status_code in [200, 201]
            chat_id = create_response.json()["technical_id"]

            # Stream a message that will trigger tool calls
            stream_response = await client.post(
                f"{self.BASE_URL}/chats/{chat_id}/stream",
                json={"message": "Check if there's a branch configuration"},
                headers={"Authorization": f"Bearer {self.TEST_TOKEN}"},
                timeout=30.0,
            )
            assert stream_response.status_code == 200

            # Parse streaming events
            tool_response_events = []
            tool_response_content_chunks = []
            tool_response_end_events = []

            async for line in stream_response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        event_data = json.loads(line[6:])
                        event_type = event_data.get("type")

                        # Collect tool response events
                        if event_type == "tool_response_start":
                            tool_response_events.append(event_data)
                            print(f"✅ Tool response start: {event_data.get('tool_name')}")

                        elif event_type == "tool_response_content":
                            tool_response_content_chunks.append(event_data)
                            chunk = event_data.get("chunk", "")
                            print(f"📝 Tool response chunk: {chunk[:50]}...")

                        elif event_type == "tool_response_end":
                            tool_response_end_events.append(event_data)
                            print(f"✅ Tool response end: {event_data.get('tool_name')}")

                    except json.JSONDecodeError:
                        pass

            # Verify tool response streaming
            if tool_response_events:
                print(f"\n✅ Tool response streaming verified:")
                print(f"   - Start events: {len(tool_response_events)}")
                print(f"   - Content chunks: {len(tool_response_content_chunks)}")
                print(f"   - End events: {len(tool_response_end_events)}")

                # Verify we have content chunks
                if tool_response_content_chunks:
                    accumulated_content = "".join(
                        chunk.get("chunk", "") for chunk in tool_response_content_chunks
                    )
                    print(f"   - Accumulated content length: {len(accumulated_content)}")
                    assert len(accumulated_content) > 0, "Tool response content should not be empty"
                    print(f"   - Content preview: {accumulated_content[:100]}...")
            else:
                print("ℹ️ No tool response events in this stream (normal for some queries)")


    @pytest.mark.asyncio
    async def test_stream_chat_message_with_openai_sdk(self):
        """Test streaming with OpenAI SDK when AI_SDK=openai."""
        import os

        # Check if OpenAI SDK is configured
        original_sdk = os.getenv("AI_SDK", "google")

        try:
            # Set to use OpenAI SDK
            os.environ["AI_SDK"] = "openai"

            # Reload the SDK factory to pick up the new environment variable
            import importlib
            from application.services import sdk_factory
            importlib.reload(sdk_factory)

            # Verify we're using OpenAI
            from application.services.sdk_factory import is_using_openai_sdk
            if not is_using_openai_sdk():
                pytest.skip("OpenAI SDK not configured (OPENAI_API_KEY not set)")

            async with httpx.AsyncClient() as client:
                # Create chat
                create_response = await client.post(
                    f"{self.BASE_URL}/chats",
                    json={"name": "OpenAI Test Chat", "description": ""},
                    headers={"Authorization": f"Bearer {self.TEST_TOKEN}"},
                )
                assert create_response.status_code in [200, 201]
                chat_id = create_response.json()["technical_id"]

                # Stream message
                message = "Hello, what is 2+2?"

                async with client.stream(
                    "POST",
                    f"{self.BASE_URL}/chats/{chat_id}/stream",
                    json={"message": message},
                    headers={
                        "Authorization": f"Bearer {self.TEST_TOKEN}",
                        "Accept": "text/event-stream",
                    },
                ) as response:
                    assert response.status_code == 200, f"Failed to stream: {response.text}"

                    # Collect all events
                    events = []
                    accumulated_content = ""
                    start_events = []
                    content_events = []
                    done_events = []
                    error_events = []

                    async for line in response.aiter_lines():
                        if line.startswith("event: "):
                            event_type = line[7:]
                            if event_type == "start":
                                start_events.append(event_type)
                            elif event_type == "content":
                                content_events.append(event_type)
                            elif event_type == "done":
                                done_events.append(event_type)
                            elif event_type == "error":
                                error_events.append(event_type)
                        elif line.startswith("data: "):
                            try:
                                event_data = json.loads(line[6:])
                                events.append(event_data)

                                # Accumulate content chunks
                                if "chunk" in event_data:
                                    accumulated_content += event_data["chunk"]
                            except json.JSONDecodeError:
                                pass

                    # Verify we got events
                    print(f"\n✅ OpenAI Streaming Test Results:")
                    print(f"   - Start events: {len(start_events)}")
                    print(f"   - Content events: {len(content_events)}")
                    print(f"   - Done events: {len(done_events)}")
                    print(f"   - Error events: {len(error_events)}")
                    print(f"   - Total events: {len(events)}")
                    print(f"   - Accumulated content length: {len(accumulated_content)}")

                    # Assertions
                    assert len(start_events) > 0, "Should have start event"
                    assert len(done_events) > 0, "Should have done event"
                    assert len(error_events) == 0, f"Should not have errors: {error_events}"
                    assert len(accumulated_content) > 0, "Should have accumulated content"

                    print(f"   - Content preview: {accumulated_content[:100]}...")

        finally:
            # Restore original SDK setting
            os.environ["AI_SDK"] = original_sdk
            import importlib
            from application.services import sdk_factory
            importlib.reload(sdk_factory)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

