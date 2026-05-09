# tns-novel

Token Never Sleeps Novel Writing Template.

Current scope: write a five-chapter dark gothic novel via TNS FSM
orchestration, with persistent story bible tracking and dashboard
monitoring.

## sec-001: Story Premise & World Setting

Objective: establish the complete story world before any writing begins.

Inputs: user story concept.

Deliverables:
- `story_bible/world.md` — era, geography, political landscape, belief system, tone.

Acceptance criteria:
- World has internal consistency and supports the full story arc.
- Setting is distinctive enough to sustain gothic horror atmosphere.
- Supernatural elements are organically integrated with the Victorian-style world.

## sec-002: Global Protocol

Objective: confirm the workflow protocol that every writing section must follow.

Inputs: task.md global protocol section.

Deliverables: confirmed protocol embedded in executor context.

Acceptance criteria:
- Protocol is clear and executable.
- Continuity check script covers all key checkpoints.
- Story bible update rules are unambiguous.

## sec-003: Story Outline

Objective: define the act structure and character arcs before writing.

Inputs: `story_bible/world.md`.

Deliverables:
- `story_bible/outline.md` — act breakdown, character arcs table, central conflict, themes.

Acceptance criteria:
- Outline forms a complete causal chain across all five chapters.
- Each character arc has a clear start, turning point, and end state.
- Five-chapter structure accommodates the full central conflict.

## sec-004: Character Profiles

Objective: develop detailed profiles for every major character.

Inputs: `story_bible/outline.md`.

Deliverables:
- `story_bible/characters.md` — per-character identity, personality, background,
  internal conflict, arc, and relationship map.

Acceptance criteria:
- Each character has a distinct voice and motivation.
- Relationship tensions are mapped and exploitable for drama.
- Antagonist has credible motivation beyond pure evil.

## sec-005: Character Review

Objective: audit character profiles for consistency and completeness.

Inputs: `story_bible/characters.md`, `story_bible/outline.md`.

Deliverables: finalized `story_bible/characters.md` with resolved inconsistencies.

Acceptance criteria:
- All characters are compatible with the outline.
- Cross-character interaction potential is fully surfaced.
- No contradictions in backstory or motivation.

---

Each chapter section (sec-006 ~ sec-010) follows the same executor→verifier pattern:
1. Read all story bible files and previous chapters.
2. Write the chapter to `draft/chapters/chapter-0X.md`.
3. Update story bible with chapter summary, entity changes, and character state.
4. Run `node .claude/skills/novel-check/check_novel.js` for continuity.

### sec-006: Chapter 01 — Opening

Objective: establish the world, introduce the protagonist, and deliver
the inciting incident that sets the plot in motion.

Inputs: `story_bible/world.md`, `story_bible/characters.md`, `story_bible/outline.md`.

Deliverables:
- `draft/chapters/chapter-01.md` (3000+ characters).
- Updated `story_bible/chapter_summaries.md`, `story_bible/timeline.md`, `story_bible/entities.md`.

Acceptance criteria:
- Gothic horror atmosphere is established in the first paragraphs.
- Protagonist's internal conflict is shown through action and detail, not stated.
- Chapter ends with a clear inciting decision that makes the next chapter inevitable.
- World details are woven into narrative, not info-dumped.

### sec-007: Chapter 02 — Escalation

Objective: escalate the conflict, deepen character relationships,
and introduce complications that raise the stakes.

Inputs: `draft/chapters/chapter-01.md`, all story bible files.

Deliverables:
- `draft/chapters/chapter-02.md` (3000+ characters).
- Updated story bible files.

Acceptance criteria:
- Chapter follows causally from Chapter 01's ending.
- At least one relationship or loyalty is meaningfully complicated.
- Backstory reveals change the reader's understanding of earlier events.
- A parallel tension thread creates dramatic irony.

### sec-008: Chapter 03 — Reversal

Objective: deliver the central reversal that changes the story's trajectory
irreversibly.

Inputs: previous chapters, all story bible files.

Deliverables:
- `draft/chapters/chapter-03.md` (3000+ characters).
- Updated story bible files.

Acceptance criteria:
- The reversal is clear and cannot be undone.
- Personal stakes connect to the larger thematic conflict.
- Revelation scenes build tension rather than dumping information.
- The protagonist's transformation from one state to another is complete.

### sec-009: Chapter 04 — Confrontation

Objective: bring all tensions to a head and force characters into their
final positions.

Inputs: previous chapters, all story bible files.

Deliverables:
- `draft/chapters/chapter-04.md` (3000+ characters).
- Updated story bible files.

Acceptance criteria:
- The confrontation scene is dramatic and earned by earlier setup.
- Secondary character arcs converge meaningfully with the main plot.
- The cost of earlier choices is made visible and painful.
- The stakes feel genuinely life-or-death.

### sec-010: Chapter 05 — Resolution

Objective: complete the immediate arc while preserving future stakes.

Inputs: previous chapters, all story bible files.

Deliverables:
- `draft/chapters/chapter-05.md` (3000+ characters).
- Finalized story bible files with complete summaries and character states.

Acceptance criteria:
- The immediate arc resolves satisfyingly.
- The ending balances closure with open possibility.
- The gothic horror tone is sustained to the final page.
- All story bible files contain final summaries and character states.
- `node .claude/skills/novel-check/check_novel.js` passes.
