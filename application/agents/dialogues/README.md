# Agent Dialogues Directory

This directory contains test dialogues and prompts for testing UI hooks functionality across all agents.

## Files

### Test Prompts
- **ui_hooks_test_prompts.md** - Comprehensive test prompts for all UI hook types
  - Multi-choice options (option_selection hooks)
  - Canvas navigation (open_canvas_tab hooks)
  - Conditional options based on context
  - Error handling and fallback behavior
  - Multi-step workflows with hooks

### Test Dialogues (JSON)
- **test_prompt_hooks_dialogue.json** - Complete dialogue demonstrating prompt-level hooks
  - Shows multi-choice option selection
  - Demonstrates hook rendering and user interaction
  - Includes test results validation

- **test_canvas_hooks_dialogue.json** - Complete dialogue demonstrating canvas navigation
  - Shows entity and workflow creation
  - Demonstrates canvas tab navigation hooks
  - Shows multiple hooks in sequence

## Testing UI Hooks

### Quick Start
1. Open a conversation with any agent
2. Use test prompts from `ui_hooks_test_prompts.md`
3. Verify hooks render as clickable buttons/options
4. Click options and verify agent responds correctly

### Test Scenarios

**Environment Agent:**
- Multi-choice deployment options
- Environment selection
- Credential issuance

**Setup Agent:**
- Environment selection for credentials
- Conditional options based on setup state

**GitHub Agent:**
- Next steps after code generation
- Multi-choice workflow options

**Canvas Agent:**
- Canvas tab navigation
- Entity and workflow creation with canvas opening

## Hook Types Tested

1. **option_selection** - Multi-choice questions
   - Renders as clickable buttons
   - User selection captured and processed
   - Conditional options based on context

2. **open_canvas_tab** - Canvas navigation
   - Opens specific canvas tabs (entities, workflows, requirements)
   - Works after entity/workflow creation
   - Seamless integration with agent flow

3. **code_changes** - Code generation feedback
   - Shows generated code changes
   - Offers next steps options

## Validation Checklist

- [ ] Hooks render correctly in UI
- [ ] Options are clickable
- [ ] User selections are captured
- [ ] Agent responds to selections
- [ ] Canvas opens to correct tabs
- [ ] Fallback to text works
- [ ] Multiple hooks in sequence work
- [ ] Performance is acceptable
- [ ] Works across all agents
- [ ] Error handling works

## Adding New Test Dialogues

1. Create a new JSON file: `test_<feature>_dialogue.json`
2. Follow the structure of existing dialogue files
3. Include complete message flow
4. Add hook definitions with parameters
5. Include test results section
6. Document in this README

## Related Documentation

- `PROMPT_HOOKS_GUIDE.md` - How to use prompt-level hooks
- `HOOK_FRAMEWORK_README.md` - Hook framework overview
- Agent prompt templates - Examples in each agent's prompts directory

