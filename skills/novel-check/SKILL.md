---
name: novel-check
description: Validate novel continuity across story bible files, chapter drafts, and acceptance criteria. Run after each content-producing section to ensure consistency.
---

# Novel Continuity Check

Validate that all story bible files and chapter drafts maintain continuity
and meet structural requirements.

## When to Use

Run after any section that produces or modifies content:
- After outline generation (sec-003)
- After character profile creation (sec-005)
- After every chapter write (sec-006 through sec-010)

## How to Run

```bash
node skills/novel-check/check_novel.js
```

## What It Checks

- All 5 story bible files exist and have substantial content
- All chapter files exist, start with H1 titles, and meet minimum length
- Chapter summaries reference each existing chapter
- Template vs content mode detection (lower threshold for templates)

## Output

- Exit 0: all checks pass, reports chapter and bible file counts
- Exit 1: lists specific failures for the next executor to fix
