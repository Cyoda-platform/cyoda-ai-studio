# Claude Code Configuration

This directory contains Claude Code-specific configuration and skills for the Cyoda AI Studio project.

## Files in This Directory

### instructions.md
Detailed coding guidelines and project-specific instructions that Claude Code reads at the start of every session.

**Contains:**
- Project overview
- Primary code guidelines (function sizes, naming, type hints)
- Google ADK reference
- Cyoda platform integration patterns
- Code review checklist
- Decision log

**When to consult:** Before writing any code in this project.

### skills/
Directory containing specialized workflows that Claude Code can load on-demand when relevant to the task.

## Available Skills

### 1. add-agent
**Use when:** Creating new ADK agents or modifying agent structure

**Provides:**
- Step-by-step agent creation workflow
- Agent directory structure
- Prompt template creation
- Tool registration patterns
- Evaluation test setup
- Common agent patterns (multi-modal, structured output, delegation)

**Entry point:** `.claude/skills/add-agent/SKILL.md`

### 2. cyoda-integration
**Use when:** Integrating with Cyoda platform APIs

**Provides:**
- Entity CRUD operations (create, read, update, delete)
- Search patterns (simple & complex conditions)
- Workflow management (export/import)
- Authentication & token management
- Error handling patterns
- Point-in-time queries

**Entry point:** `.claude/skills/cyoda-integration/SKILL.md`

### 3. debug-streaming
**Use when:** Debugging or implementing SSE streaming

**Provides:**
- Common streaming issues & solutions
- Field name troubleshooting (chunk vs content)
- Connection timeout handling
- Event handling patterns
- Debugging techniques
- Testing strategies

**Entry point:** `.claude/skills/debug-streaming/SKILL.md`

### 4. run-evals
**Use when:** Running or creating ADK evaluations

**Provides:**
- Running evaluation commands
- Creating evaluation tests
- Eval best practices
- Report generation & interpretation
- CI/CD integration
- Debugging failing evals

**Entry point:** `.claude/skills/run-evals/SKILL.md`

### 5. workflow-management
**Use when:** Managing Cyoda entity workflows (FSM)

**Provides:**
- Workflow JSON structure (FSM)
- States, transitions, processors
- Criterion patterns (simple, function, group)
- Processor implementation guidelines
- Export/import operations
- Workflow debugging techniques

**Entry point:** `.claude/skills/workflow-management/SKILL.md`

## How Skills Work

Skills use the **progressive disclosure** pattern:

1. **SKILL.md** - Main documentation (always read first)
   - YAML frontmatter with metadata
   - Step-by-step workflows
   - Common patterns
   - Best practices
   - Troubleshooting

2. **scripts/** - Executable helper scripts (optional)
   - Automation for repetitive tasks
   - Validation scripts
   - Setup/cleanup utilities

3. **references/** - Deep-dive documentation (optional)
   - Extended technical details
   - Architecture diagrams
   - Complex examples
   - Reference implementations

## Skill Loading Strategy

Claude Code loads skills **on-demand** based on:
- Task description keywords
- User explicit requests
- Context analysis

**Example triggers:**
- "Create a new agent" → Loads `add-agent` skill
- "Debug streaming issue" → Loads `debug-streaming` skill
- "Search entities in Cyoda" → Loads `cyoda-integration` skill
- "Run evaluations" → Loads `run-evals` skill
- "Export workflow" → Loads `workflow-management` skill

## Creating New Skills

To add a new skill:

1. **Create directory structure:**
   ```bash
   mkdir -p .claude/skills/my-skill/{scripts,references}
   ```

2. **Create SKILL.md with YAML frontmatter:**
   ```markdown
   ---
   name: my-skill
   description: Use this skill when [describe trigger condition]
   tags: [tag1, tag2, tag3]
   ---

   # My Skill

   ## Purpose
   [Brief description]

   ## When to Use This Skill
   - [Trigger 1]
   - [Trigger 2]

   ## Step-by-Step Workflow
   [Detailed steps...]
   ```

3. **Add helper scripts (optional):**
   ```bash
   # In .claude/skills/my-skill/scripts/
   touch helper.py
   chmod +x helper.py
   ```

4. **Add deep-dive docs (optional):**
   ```bash
   # In .claude/skills/my-skill/references/
   touch advanced-topics.md
   ```

## Best Practices for Skills

1. **Keep SKILL.md concise** - Aim for 300-600 lines
2. **Use progressive disclosure** - Link to references/ for deep dives
3. **Include checklists** - Help ensure nothing is missed
4. **Provide code examples** - Show, don't just tell
5. **Add troubleshooting sections** - Common errors & solutions
6. **Reference existing files** - Link to project files for context

## Integration with Project Documentation

Skills complement but don't replace:

- **CLAUDE.md** - High-level project brain (always loaded)
- **instructions.md** - Coding standards (always loaded)
- **llms.txt** - Documentation map (universal AI standard)
- **README.md** - Human-readable project docs

**Hierarchy:**
```
CLAUDE.md (project brain)
    ↓
instructions.md (coding standards)
    ↓
skills/ (specialized workflows, loaded on-demand)
    ↓
Project code (application/, common/, etc.)
```

## Naming Conventions

- **Skill directories:** Use kebab-case (`my-skill`, not `MySkill` or `my_skill`)
- **SKILL.md:** Always uppercase `SKILL.md`
- **Frontmatter name:** Match directory name
- **Tags:** Lowercase, hyphenated

## Examples of Good Skill Organization

### Focused Skill (Good)
```
add-agent/
├── SKILL.md              # ~400 lines, covers agent creation
├── scripts/
│   └── validate_agent.py # Validation helper
└── references/
    └── adk-advanced.md   # Deep ADK patterns
```

### Over-scoped Skill (Bad)
```
do-everything/
└── SKILL.md              # 2000 lines, tries to cover too much
```

**Why bad:** Should be split into multiple focused skills.

## Maintenance

**When to update skills:**
- New patterns emerge in the codebase
- Common bugs/issues identified
- Framework updates (Google ADK, Cyoda API)
- User feedback on workflows

**Version control:**
- Skills are versioned with the project
- Breaking changes should update skill docs
- Keep examples in sync with actual code

## Quick Reference

| Skill | Primary Use Case | Key Files |
|-------|-----------------|-----------|
| add-agent | Create new ADK agents | `application/agents/` |
| cyoda-integration | Cyoda API operations | `common/repository/`, `llm_docs/` |
| debug-streaming | Fix SSE streaming | `application/services/streaming_service.py` |
| run-evals | ADK evaluations | `application/agents/tests/evals/` |
| workflow-management | FSM workflows | `application/entity/*/workflow.py` |

---

**Last Updated:** 2026-04-28
**For AI Agents:** Read `instructions.md` first, then load skills as needed
**For Humans:** Skills provide step-by-step guides for common tasks
