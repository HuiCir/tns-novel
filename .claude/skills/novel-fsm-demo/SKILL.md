---
name: novel-fsm-demo
description: Walk the TNS FSM novel-writing pipeline step by step, updating section state and dashboard in real time. Use for dry-run validation before live execution.
---

# Novel FSM Demo

Execute a simulated walk of the full novel-writing FSM pipeline,
updating TNS section state and dashboard at each step.

## When to Use

- Before starting a live TNS run to validate the FSM program
- After modifying `tns_config.json` program states
- For CI/dry-run verification of pipeline integrity

## How to Run

```bash
node skills/novel-fsm-demo/demo_fsm.js [--speed 200] [--steps 15]
```

## What It Does

- Reads the FSM program from `tns_config.json`
- Initializes TNS section state in `.tns/sections.json`
- Walks each state in sequence (sec-001 → sec-010)
- Simulates executor→verifier→done for each task state
- Updates dashboard via gateway API at 5-step intervals
- Reports final pipeline status and dashboard counts

## Options

- `--speed N`: milliseconds between steps (default 200)
- `--steps N`: maximum steps to execute (default 15)
