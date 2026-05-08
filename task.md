# Novel Writing Task

Write a multi-chapter story using the persistent story bible files in this
workspace. Each section owns one phase of the pipeline.

## Global Protocol (each section must follow)

- Read all `story_bible/*.md` files and previous chapter drafts before writing.
- Before drafting, update any needed assumptions in world, timeline, or character notes.
- Write the chapter to `draft/chapters/chapter-XX.md`.
- Append a concise chapter summary and continuity handoff to `story_bible/chapter_summaries.md`.
- Update entity relationship changes in `story_bible/entities.md`.
- Merge lasting character state changes back into `story_bible/characters.md`.
- Run `node scripts/check_novel.js` before claiming the section is ready.

## Section 01: Story Outline & World Building

Define the complete story structure before writing any chapters.

- Define the act structure for this arc.
- Establish the world setting, political landscape, and central conflict.
- List all major characters with their arcs.
- Write the outline to `story_bible/outline.md`.

Acceptance criteria:
- `story_bible/outline.md` exists with complete structure.
- Major characters are defined with motivations and arcs.
- The central conflict is clearly outlined.

## Section 02: Character Profiles

Develop deep character profiles for every major character.

Write profiles to `story_bible/characters.md`.

Acceptance criteria:
- Each character has background, personality, goals, conflicts, and arc.
- Character relationships are mapped with tension points.
- Profiles are consistent with the outline.

## Chapter 01: Opening

Write the first chapter. Establish the world, introduce the protagonist,
present the inciting incident, and set the immediate stakes.

Acceptance criteria:
- `draft/chapters/chapter-01.md` exists with substantial content.
- The chapter creates a clear inciting pressure point.
- Story bible files reflect the chapter's durable changes.
- `node scripts/check_novel.js` passes.

## Chapter 02: Escalation

Write the second chapter. Escalate the conflict and deepen character
relationships. Introduce complications that raise the stakes.

Acceptance criteria:
- `draft/chapters/chapter-02.md` exists with substantial content.
- The chapter follows causally from chapter 01.
- Story bible files updated.
- `node scripts/check_novel.js` passes.

## Chapter 03: Reversal

Write the third chapter. Deliver the central reversal that changes the
trajectory of the story irreversibly.

Acceptance criteria:
- `draft/chapters/chapter-03.md` exists with substantial content.
- The reversal is clear and changes the situation permanently.
- Story bible files updated.
- `node scripts/check_novel.js` passes.

## Chapter 04: Confrontation

Write the fourth chapter. Bring tensions to a head. Show the cost of
earlier choices and force characters into their final positions.

Acceptance criteria:
- `draft/chapters/chapter-04.md` exists with substantial content.
- The chapter tightens the danger and prepares the ending.
- Story bible files updated.
- `node scripts/check_novel.js` passes.

## Chapter 05: Resolution

Write the final chapter. Complete the arc while leaving a clean opening
for continuation. Resolve the immediate stakes while preserving future
possibilities.

Acceptance criteria:
- `draft/chapters/chapter-05.md` exists with substantial content.
- The ending resolves the immediate arc satisfyingly.
- Story bible files contain final summaries and character states.
- `node scripts/check_novel.js` passes.
