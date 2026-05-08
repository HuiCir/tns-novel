# tns-noval

TNS-powered novel writing workspace with persistent story bible tracking,
executor/verifier agent pipeline, and real-time dashboard monitoring.

## Architecture

```
task.md ──────► tns compile ──► .tns/compiled/program.json
    │
    ▼
tns run ──► [executor] claude -p --agent tns-executor
    │           │ writes chapter, updates story bible
    │           ▼
    └──────► [verifier] claude -p --agent tns-verifier
                │ checks continuity, acceptance criteria
                ▼
         .tns/sections.json (state tracking)
                │
                ▼
         Dashboard (port 48731)
```

## Quick Start

```bash
# Initialize workspace
tns init --workspace /path/to/project --template novel-writing --dashboard

# Plan your story
tns plan --text "describe your story" --apply --compile

# Run one section
tns run --once

# Continuous loop
tns start

# Monitor
tns status && tns btw
```

## Project Structure

```
├── task.md                  # Workflow definition (TNS sections)
├── tns_config.json          # TNS configuration
├── story_bible/             # Persistent world state
│   ├── world.md             # Setting, politics, magic system
│   ├── characters.md        # Character profiles with arcs
│   ├── timeline.md          # Chronology and causal chain
│   ├── entities.md          # Organizations, locations, items
│   ├── outline.md           # Story structure and themes
│   └── chapter_summaries.md # Per-chapter summaries + handoffs
├── draft/chapters/          # Chapter output
│   ├── chapter-01.md
│   └── ...
├── scripts/
│   └── check_novel.js       # Continuity checker
└── src/
    ├── orchestrator.py      # TNS-style section workflow engine
    └── workflow.py          # Novel writing workflow definition
```

## Section Pipeline

Each section in `task.md` goes through:

1. **pending** → Awaiting processing
2. **executor** → Claude Code agent writes/updates content
3. **verifier** → Independent agent checks acceptance criteria
4. **done** / **needs_fix** → Pass or retry (max 3 attempts)

## Python Orchestrator

The `src/orchestrator.py` module provides a LangGraph-free workflow engine
using TNS-style sections with conditional transitions:

```python
from src.orchestrator import Workflow, Section, Transition

wf = Workflow(entry="generate_outline")
wf.add_section(Section(
    id="generate_outline",
    handler=generate_outline_handler,
    transitions=[Transition(field="_route", equals="success", next="validate")],
))
wf.compile()
```

See `src/workflow.py` for the full novel-writing pipeline definition.
