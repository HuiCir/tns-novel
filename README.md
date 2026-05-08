# tns-noval

Pure TNS-orchestrated novel writing workspace. The complete novel-writing
pipeline is defined as a **TNS FSM program** in `tns_config.json` — no
Python, no LangGraph, no external orchestration. TNS drives everything.

## Architecture

```
tns_config.json          task.md
  │  FSM program           │  Section definitions
  │  70+ states            │  Acceptance criteria
  ▼                        ▼
  └──────────┬─────────────┘
             ▼
     TNS FSM Runtime
             │
     ┌───────┴────────┐
     ▼                ▼
 [executor]        [verifier]
 claude -p         claude -p
     │                │
     ▼                ▼
 sections.json    dashboard
 state tracking   :48731
```

## FSM Pipeline (defined in `program.states`)

```
Phase 1: Outline
  outline_gen → outline_val → [decide] → outline_fb → outline_fb_proc → [decide]

Phase 2: Characters
  char_gen → char_val → [decide] → char_fb → char_fb_proc → [decide]

Phase 3: Chapter Loop (×5)
  For each chapter (01–05):
    ch0X_write → ch0X_val → ch0X_fb → ch0X_fb_proc
      → [decide_ch0X_fb]
      → ch0X_eval → ch0X_eval_val → [decide_ch0X_eval]
          ├─ deep mode → ch0X_super → [decide_ch0X_super]
          │                 ├─ pass → ch0X_accept
          │                 └─ revise → ch0X_write (loop)
          └─ fast mode → ch0X_accept
      → [decide_chapter_done]
          ├─ more chapters → ch0Y_write
          └─ all done → success

Terminal: success | failure
```

## FSM Features

- **70+ states**: task states for generation/validation/evaluation, decision
  states for conditional routing
- **Retry loops**: failed validation routes back to generation via `needs_fix`
- **Dual evaluation modes**: `deep` (supervisor review) vs `fast` (direct accept)
  controlled by context variable `evaluation_mode`
- **Revision loop**: supervisor-detected issues route back to chapter rewrite
- **Chapter loop**: `decide_chapter_done` state routes to next chapter or success
- **Safety limits**: `chapter_loop_count` capped at 25 to prevent infinite loops
- **Phase grouping**: each chapter uses `parallel.resource` for isolation

## Quick Start

```bash
# Initialize
tns init --workspace ./my-novel --template novel-writing --dashboard

# Write story bible and customize task.md with your story

# Compile and run
tns compile --synthesize --apply
tns run --once          # One section at a time
tns start               # Continuous loop

# Monitor
tns status && tns btw
open http://127.0.0.1:48731/?workspace=...&key=...  # Dashboard
```

## Project Structure

```
├── tns_config.json          # TNS config + complete FSM program
├── task.md                  # Section definitions with acceptance criteria
├── story_bible/             # Persistent world state
│   ├── world.md             # Setting, politics, belief system
│   ├── characters.md        # Character profiles with arcs
│   ├── timeline.md          # Chronology tracking
│   ├── entities.md          # Organizations, locations, items
│   ├── outline.md           # Story structure and themes
│   └── chapter_summaries.md # Per-chapter summaries + handoffs
├── draft/chapters/          # Chapter output
│   ├── chapter-01.md
│   └── ...
└── scripts/
    └── check_novel.js       # Continuity checker
```

## FSM Program (excerpt)

```json
{
  "program": {
    "entry": "outline_gen",
    "context": {
      "evaluation_mode": "deep",
      "current_chapter": 1,
      "total_chapters": 5
    },
    "states": [
      {
        "id": "ch01_write",
        "type": "task",
        "transitions": [{ "to": "ch01_val" }]
      },
      {
        "id": "decide_ch01_eval",
        "type": "decision",
        "transitions": [
          { "to": "ch01_super", "when": { "path": "evaluation_mode", "equals": "deep" } },
          { "to": "ch01_accept", "when": { "path": "evaluation_mode", "equals": "fast" } },
          { "to": "ch01_write", "when": { "path": "action", "equals": "revise" } }
        ]
      }
    ]
  }
}
```

See `tns_config.json` for the complete 70+ state FSM program.
