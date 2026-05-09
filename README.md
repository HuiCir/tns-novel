# tns-novel

`tns-novel` is a Token Never Sleeps novel-writing template. It is a TNS
case/reference workspace, not an independent npm package.

The complete novel-writing pipeline is defined as a **TNS FSM program** in
`tns_config.json` — no Python, no LangGraph, no external orchestration.
TNS drives everything: section sequencing, executor/verifier dispatch,
skill injection, continuity validation, and dashboard monitoring.

## Install TNS

```bash
npm install -g token-never-sleeps@1.0.3
tns --version
```

## Run With TNS

```bash
git clone https://github.com/HuiCir/tns-novel.git
cd tns-novel
tns init --workspace "$PWD" --task task.md --runner direct --dashboard
tns compile
tns doctor
```

`git clone` gives you the template workspace: `task.md`, `tns_config.json`,
story bible templates, chapter draft templates, and `.claude/skills/`. It
does not include `.tns/`, because `.tns/` is local runtime state: locks,
section status, compiled program, dashboard key, gateway events, runner
heartbeats, and agent run records. `tns init` creates that local runtime
directory for the clone you are about to run. Note the **dashboard key**
printed by `tns init --dashboard` — you will need it to open the dashboard URL.

### Start the dashboard (terminal 1)

```bash
tns gateway web --port 48731
```

Then open the dashboard URL printed by `tns init --dashboard`, e.g.
`http://127.0.0.1:48731/?workspace=...&key=xxxx-xxxx`.

### Start the runner (terminal 2)

```bash
tns start
```

This runs the executor→verifier loop continuously. For a one-shot
non-monitoring check, use `tns run --once` instead.

The gateway and runner are long-running processes — keep them in
separate terminals or a process manager.

The template is driven by `tns_config.json`, `task.md`, and the workspace
skills `.claude/skills/novel-check` and `.claude/skills/novel-fsm-demo`.
Writing-related executor stages inject `novel-check` through TNS skill
management.

## Architecture

```
tns_config.json          task.md
  │  FSM program           │  Section definitions
  │  10 states             │  Objective/Inputs/Deliverables/Acceptance criteria
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

## FSM Pipeline

```
sec-001  Story premise & world setting
sec-002  Global protocol
sec-003  Story outline & act structure
sec-004  Character profiles
sec-005  Character review & finalization
sec-006  Chapter 01 — Opening, inciting incident
sec-007  Chapter 02 — Escalation
sec-008  Chapter 03 — Reversal
sec-009  Chapter 04 — Confrontation
sec-010  Chapter 05 — Resolution
```

Each section goes through the TNS executor→verifier loop:
1. **pending** → awaiting processing
2. **executor** → Claude Code agent writes/updates content
3. **verifier** → independent agent checks acceptance criteria
4. **done** / **needs_fix** → pass or retry (max 3 attempts)

Content-producing sections (sec-003, sec-005, sec-006–sec-010) run
`node .claude/skills/novel-check/check_novel.js` as a post-step
command hook for continuity validation.

## Project Structure

```
├── tns_config.json              # TNS config + 10-state FSM program
├── task.md                      # Section definitions (Objective/Inputs/Deliverables/Acceptance)
├── .claude/skills/              # Workspace skills (TNS-managed injection)
│   ├── novel-check/
│   │   ├── SKILL.md             # Skill definition
│   │   └── check_novel.js       # Continuity checker
│   └── novel-fsm-demo/
│       ├── SKILL.md             # Skill definition
│       └── demo_fsm.js          # FSM pipeline dry-run
├── story_bible/                 # Persistent world state
│   ├── world.md                 # Setting, politics, belief system
│   ├── characters.md            # Character profiles with arcs
│   ├── timeline.md              # Chronology tracking
│   ├── entities.md              # Organizations, locations, items
│   ├── outline.md               # Story structure and themes
│   └── chapter_summaries.md     # Per-chapter summaries + handoffs
├── draft/chapters/              # Chapter output
│   ├── chapter-01.md
│   └── ...
├── .env.example                 # Environment variable template
└── .gitignore
```

## Skills

The template includes two workspace skills under `.claude/skills/`:

### novel-check (required)

Continuity validation for story bible files and chapter drafts.
Injected into executor_task and verifier_audit profiles.

```bash
node .claude/skills/novel-check/check_novel.js
```

Checks: story bible file existence and substance, chapter file structure
and minimum length, chapter summary coverage.

### novel-fsm-demo (optional)

Dry-run the FSM pipeline before live execution, updating section state
and dashboard in real time.

```bash
node .claude/skills/novel-fsm-demo/demo_fsm.js --speed 200 --steps 15
```

## Customize For Your Story

1. Edit `story_bible/world.md` with your world setting.
2. Fill in `story_bible/characters.md` with your character profiles.
3. Write your outline in `story_bible/outline.md`.
4. Update chapter descriptions in `task.md` sec-006 through sec-010
   with your specific chapter content requirements.
5. Run `tns compile` to synchronize sections.
6. Start the pipeline with `tns start` (or step through with `tns run --once`).
