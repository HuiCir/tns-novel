# Novel Writing Task

This task is orchestrated by the TNS FSM program defined in `tns_config.json`.
Each section below corresponds to an FSM state. The FSM handles conditional
routing (success/retry/failure), evaluation mode branching (deep/fast), and
the chapter writing loop.

## Global Protocol (all sections)

- Read story bible files before writing: `story_bible/world.md`, `characters.md`,
  `timeline.md`, `entities.md`, `chapter_summaries.md`, and all previous chapters.
- Write chapter output to `draft/chapters/chapter-0X.md`.
- After each chapter, update story bible with summaries, entity changes,
  and character state changes.
- Run `node scripts/check_novel.js` before claiming the section ready.

---

## Phase 1: Outline

### outline_gen — Generate Story Outline
Define the complete story structure: act breakdown, world setting, central
conflict, character list with arcs. Output to `story_bible/outline.md`.

Acceptance criteria:
- `story_bible/outline.md` exists with complete structure.
- At least 5 major characters defined with arcs.
- Central conflict and themes articulated.

### outline_val — Validate Outline
Verify the outline meets all structural requirements. Check character count,
conflict clarity, and format compliance.

### outline_fb — Outline Feedback
Present the outline for human review. User may approve, request changes,
or trigger regeneration.

### outline_fb_proc — Process Outline Feedback
Apply user feedback: accept modifications, confirm approval, or flag retry.

---

## Phase 2: Characters

### char_gen — Generate Character Profiles
Develop deep profiles for every major character: background, personality,
goals, conflicts, arc, and relationships. Output to `story_bible/characters.md`.

Acceptance criteria:
- Each character has background, personality, goals, conflicts, arc.
- Character relationships mapped with tension points.
- Profiles consistent with outline.

### char_val — Validate Character Profiles
Verify character profiles for completeness and outline consistency.

### char_fb — Character Feedback
Present character profiles for human review.

### char_fb_proc — Process Character Feedback
Apply user feedback on character profiles.

---

## Phase 3: Chapter Pipeline (repeats for chapters 01–05)

Each chapter follows this pipeline (FSM handles the loop):

### ch0X_write — Write Chapter 0X
Write the complete chapter following the outline and character profiles.
Output to `draft/chapters/chapter-0X.md`.

Acceptance criteria:
- Complete chapter with substantial word count.
- Follows causally from previous chapters.
- Characters act consistently with their profiles.
- Story bible files updated.

### ch0X_val — Validate Chapter 0X
Verify chapter structure, word count, and format compliance.

### ch0X_fb — Chapter 0X Feedback
Present chapter for human review.

### ch0X_fb_proc — Process Chapter 0X Feedback
Apply user feedback on the chapter.

### ch0X_eval — Evaluate Chapter 0X
Score chapter on plot, character consistency, style, pacing, and logic.
Generate structured evaluation report.

### ch0X_eval_val — Validate Evaluation
Verify evaluation report format and completeness.

### ch0X_super — Supervisor Review (deep mode)
Multi-agent consistency check: character arcs, plot thread resolution,
world state coherence. Only runs in "deep" evaluation mode.

### ch0X_accept — Accept Chapter 0X
Save chapter to storage, update story bible, advance chapter index.

---

## Terminal States

### success
All chapters written, evaluated, and accepted. Pipeline complete.

### failure
Pipeline failed due to max attempts exceeded or unrecoverable error.
