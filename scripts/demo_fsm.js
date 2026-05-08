#!/usr/bin/env node
/**
 * TNS FSM Demo — walks the novel-writing FSM program step by step
 * and updates TNS section state + dashboard in real time.
 *
 * Usage: node scripts/demo_fsm.js [--speed 500] [--steps 10]
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";
import { execSync } from "node:child_process";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const WORKSPACE = resolve(__dirname, "..");
const CONFIG_PATH = resolve(WORKSPACE, "tns_config.json");
const SECTIONS_PATH = resolve(WORKSPACE, ".tns", "sections.json");
const HANDOFF_PATH = resolve(WORKSPACE, ".tns", "handoff.md");
const ACTIVITY_PATH = resolve(WORKSPACE, ".tns", "activity.jsonl");

// Parse CLI args
const args = process.argv.slice(2);
const SPEED = parseInt(args[args.indexOf("--speed") + 1] || "300", 10);
const MAX_STEPS = parseInt(args[args.indexOf("--steps") + 1] || "25", 10);

// Dashboard config
const DASHBOARD_KEY = "cc63-9f3c";
const DASHBOARD_URL = `http://127.0.0.1:48731/api/snapshot?workspace=${encodeURIComponent(WORKSPACE)}&key=${DASHBOARD_KEY}`;

// ============================================================
// Load FSM program
// ============================================================
const config = JSON.parse(readFileSync(CONFIG_PATH, "utf-8"));
const program = config.program;

if (!program || !program.states) {
  console.error("ERROR: No FSM program found in tns_config.json");
  process.exit(1);
}

// Filter out comment strings (non-object entries)
const fsmStates = program.states.filter((s) => typeof s === "object");

// Build state lookup
const stateMap = new Map(fsmStates.map((s) => [s.id, s]));

// Context (runtime variables)
const context = { ...program.context };

console.log("╔══════════════════════════════════════════════════╗");
console.log("║   TNS FSM Demo — Novel Writing Pipeline         ║");
console.log("╚══════════════════════════════════════════════════╝");
console.log(`\nLoaded ${fsmStates.length} FSM states from tns_config.json`);
console.log(`Entry: ${program.entry}`);
console.log(`Context: ${JSON.stringify(context)}`);
console.log(`Max steps: ${program.max_steps}`);
console.log(`\nDashboard: ${DASHBOARD_URL}`);
console.log(`\nStarting pipeline simulation...\n`);

// ============================================================
// Section state management
// ============================================================
function ensureTnsDir() {
  const tnsDir = resolve(WORKSPACE, ".tns");
  if (!existsSync(tnsDir)) mkdirSync(tnsDir, { recursive: true });
}

function initSections() {
  ensureTnsDir();
  const sections = fsmStates
    .filter((s) => s.type === "task" || s.type === "decision")
    .map((s, i) => ({
      id: s.id,
      title: s.description || s.id,
      anchor: `## ${s.id}`,
      body: s.description || "",
      status: "pending",
      attempts: 0,
      verified_at: null,
      last_summary: "",
      last_review: "",
      current_step: "",
    }));
  writeFileSync(SECTIONS_PATH, JSON.stringify(sections, null, 2));
  return sections;
}

function updateSection(sectionId, updates) {
  if (!existsSync(SECTIONS_PATH)) return;
  const sections = JSON.parse(readFileSync(SECTIONS_PATH, "utf-8"));
  const section = sections.find((s) => s.id === sectionId);
  if (!section) return;
  Object.assign(section, updates);
  writeFileSync(SECTIONS_PATH, JSON.stringify(sections, null, 2));
}

function appendActivity(event) {
  ensureTnsDir();
  const line = JSON.stringify({ ...event, at: new Date().toISOString() });
  try {
    execSync(`echo '${line.replace(/'/g, "'\\''")}' >> "${ACTIVITY_PATH}"`, {
      stdio: "ignore",
    });
  } catch {}
}

function writeHandoff(text) {
  writeFileSync(HANDOFF_PATH, text);
}

// ============================================================
// FSM walker
// ============================================================
function resolveTransition(state, context) {
  const transitions = state.transitions || [];
  const defaultTransition = state.default_transition;

  for (const t of transitions) {
    const when = t.when;
    if (!when) {
      // Unconditional transition
      if (t.to) return t;
      continue;
    }

    // Evaluate condition
    const value = when.path ? context[when.path] ?? when.path : undefined;
    let match = false;

    if (when.equals !== undefined && value === when.equals) match = true;
    if (when.not_equals !== undefined && value !== when.not_equals) match = true;
    if (when.truthy === true && value) match = true;
    if (when.truthy === false && !value) match = true;
    if (when.gt !== undefined && value > when.gt) match = true;
    if (when.gte !== undefined && value >= when.gte) match = true;

    if (match) return t;
  }

  if (defaultTransition) return defaultTransition;
  return null;
}

function stateIcon(type) {
  switch (type) {
    case "task": return "📝";
    case "decision": return "🔀";
    case "terminal": return "🏁";
    default: return "  ";
  }
}

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ============================================================
// Dashboard check
// ============================================================
async function checkDashboard() {
  try {
    const res = await fetch(DASHBOARD_URL);
    if (res.ok) {
      const snap = await res.json();
      const counts = {};
      for (const s of snap.sections || []) {
        counts[s.status] = (counts[s.status] || 0) + 1;
      }
      return counts;
    }
    return null;
  } catch {
    return null;
  }
}

// ============================================================
// Main demo loop
// ============================================================
async function main() {
  // Initialize sections
  initSections();

  let currentId = program.entry;
  let steps = 0;
  const maxSteps = Math.min(MAX_STEPS, program.max_steps || 100);

  // Simulate results for decision routing
  const simulateResult = {
    passes: true,
    action: "continue",
    revision_needed: false,
  };

  while (currentId && steps < maxSteps) {
    const state = stateMap.get(currentId);
    if (!state) {
      console.error(`  ❌ State "${currentId}" not found in FSM`);
      break;
    }

    steps++;
    const icon = stateIcon(state.type);

    // Update context via on_enter instructions
    if (state.on_enter) {
      for (const inst of state.on_enter) {
        if (inst.op === "set" && inst.path) {
          context[inst.path] = inst.value;
        }
        if (inst.op === "inc" && inst.path) {
          context[inst.path] = (context[inst.path] || 0) + (inst.by ?? 1);
        }
        if (inst.op === "emit") {
          appendActivity({ event: inst.event, state: currentId, step: steps });
        }
      }
    }

    // Task states: simulate executor→verifier→done
    if (state.type === "task") {
      updateSection(currentId, {
        status: "in_progress",
        current_step: "executor",
        attempts: (fsmStates.find((s) => s.id === currentId)?.attempts || 0) + 1,
      });

      console.log(
        `  ${icon} [${String(steps).padStart(3)}] ${currentId.padEnd(22)} | executor  → ${state.description?.slice(0, 55) || ""}`
      );

      await sleep(Math.floor(SPEED * 0.6));

      // Simulate verifier pass
      updateSection(currentId, {
        status: "done",
        current_step: "done",
        verified_at: new Date().toISOString(),
        last_summary: `${state.description?.slice(0, 40) || "Completed"} ✓`,
        attempts: 1,
      });

      appendActivity({
        event: "section_completed",
        state: currentId,
        step: steps,
        outcome: "implemented",
        verifier_status: "pass",
      });

      // Update context from simulated result
      if (simulateResult.passes !== undefined) context.passes = simulateResult.passes;
      if (simulateResult.action !== undefined) context.action = simulateResult.action;
      if (simulateResult.revision_needed !== undefined) context.revision_needed = simulateResult.revision_needed;

      // For accept states, chapter number stays (next ch0X_write on_enter sets it)
      if (currentId.match(/ch0(\d)_accept/)) {
        simulateResult.passes = true;
        simulateResult.action = "continue";
      }

      // For eval decision routing, set mode-based context
      if (currentId.match(/ch0(\d)_eval_val/)) {
        context.evaluation_mode = context.evaluation_mode || "deep";
      }
      if (currentId.match(/decide_ch0(\d)_eval/)) {
        // Simulate: deep mode goes to supervisor, fast goes to accept
        if (context.evaluation_mode === "deep") {
          context.action = "deep_super";
        }
      }
      if (currentId.match(/decide_ch0(\d)_super/)) {
        context.revision_needed = false; // Simulate pass
      }

      writeHandoff(
        `# TNS Handoff\n## Last: ${currentId}\n## Step: ${steps}/${maxSteps}\n## Context: ${JSON.stringify(context, null, 2)}\n`
      );
    }

    // Decision states: just route
    if (state.type === "decision") {
      console.log(
        `  ${icon} [${String(steps).padStart(3)}] ${currentId.padEnd(22)} | decide   → evaluating conditions...`
      );
      await sleep(Math.floor(SPEED * 0.3));
    }

    // Terminal states
    if (state.type === "terminal" || state.terminal) {
      console.log(`\n  ${icon} TERMINAL: ${currentId} — ${state.description || "Pipeline end"}`);
      appendActivity({ event: "pipeline_end", state: currentId, steps });
      break;
    }

    // Resolve next state
    const transition = resolveTransition(state, context);
    if (!transition) {
      console.log(`  ⚠️  No transition from ${currentId}, ending`);
      break;
    }

    if (transition.to) {
      if (transition.actions) {
        for (const act of transition.actions) {
          if (act.op === "emit") {
            appendActivity({ event: act.event, state: currentId, step: steps });
          }
        }
      }
      currentId = transition.to;
    } else if (transition.end) {
      console.log(`  🏁 End transition from ${currentId}`);
      break;
    } else {
      break;
    }

    // Check every 5 steps
    if (steps % 5 === 0) {
      const counts = await checkDashboard();
      if (counts) {
        const done = counts.done || 0;
        const total = Object.values(counts).reduce((a, b) => a + b, 0);
        console.log(`  📊 Dashboard: ${done}/${total} done | step ${steps}/${maxSteps}`);
      }
    }
  }

  // Final dashboard check
  const finalCounts = await checkDashboard();
  console.log(`\n══════════════════════════════════════════════════`);
  console.log(`  Pipeline complete: ${steps} steps executed`);
  console.log(`  Final context: ${JSON.stringify(context)}`);
  if (finalCounts) {
    console.log(`  Dashboard: ${JSON.stringify(finalCounts)}`);
  }
  console.log(`══════════════════════════════════════════════════`);
}

main().catch(console.error);
