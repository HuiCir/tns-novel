#!/usr/bin/env node
/**
 * TNS FSM Demo — walks the novel-writing pipeline and updates dashboard.
 * Usage: node scripts/demo_fsm.js [--speed 300] [--steps 20]
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const WORKSPACE = resolve(__dirname, "../../..");
const CONFIG_PATH = resolve(WORKSPACE, "tns_config.json");
const SECTIONS_PATH = resolve(WORKSPACE, ".tns", "sections.json");
const HANDOFF_PATH = resolve(WORKSPACE, ".tns", "handoff.md");

const args = process.argv.slice(2);
const SPEED = parseInt(args[args.indexOf("--speed") + 1] || "200", 10);
const MAX_STEPS = parseInt(args[args.indexOf("--steps") + 1] || "20", 10);
const DASHBOARD_KEY = "cc63-9f3c";
const DASHBOARD_URL = `http://127.0.0.1:48731/api/snapshot?workspace=${encodeURIComponent(WORKSPACE)}&key=${DASHBOARD_KEY}`;

const config = JSON.parse(readFileSync(CONFIG_PATH, "utf-8"));
const program = config.program;
const fsmStates = program.states.filter((s) => typeof s === "object");
const stateMap = new Map(fsmStates.map((s) => [s.id, s]));
const context = { ...program.context };

function ensureTnsDir() { mkdirSync(resolve(WORKSPACE, ".tns"), { recursive: true }); }
function writeHandoff(text) { writeFileSync(HANDOFF_PATH, text); }

function initSections() {
  ensureTnsDir();
  const sections = fsmStates.map((s) => ({
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

function resolveTransition(state, ctx) {
  for (const t of state.transitions || []) {
    if (t.to) return t;
  }
  return null;
}

async function checkDashboard() {
  try {
    const res = await fetch(DASHBOARD_URL);
    if (res.ok) {
      const snap = await res.json();
      const counts = {};
      for (const s of snap.sections || []) counts[s.status] = (counts[s.status] || 0) + 1;
      return counts;
    }
    return null;
  } catch { return null; }
}

async function main() {
  initSections();

  const stateIcons = { task: "📝", decision: "🔀", terminal: "🏁" };

  let currentId = program.entry;
  let steps = 0;
  const maxSteps = Math.min(MAX_STEPS, program.max_steps || 100);

  console.log("╔══════════════════════════════════════════════════╗");
  console.log("║   TNS FSM Demo — sec-00X Pipeline               ║");
  console.log("╚══════════════════════════════════════════════════╝");
  console.log(`\nLoaded ${fsmStates.length} FSM states | Entry: ${program.entry}`);
  console.log(`Dashboard: ${DASHBOARD_URL}\n`);

  while (currentId && steps < maxSteps) {
    const state = stateMap.get(currentId);
    if (!state) { console.error(`  ❌ Unknown state: ${currentId}`); break; }

    steps++;
    const icon = stateIcons[state.type] || "  ";

    // Process on_enter
    if (state.on_enter) {
      for (const inst of state.on_enter) {
        if (inst.op === "set") context[inst.path] = inst.value;
        if (inst.op === "inc") context[inst.path] = (context[inst.path] || 0) + (inst.by ?? 1);
      }
    }

    // Simulate executor→verifier→done for task states
    if (state.type === "task") {
      updateSection(currentId, {
        status: "in_progress", current_step: "executor", attempts: 1,
      });

      const desc = (state.description || "").slice(0, 55);
      console.log(`  ${icon} [${String(steps).padStart(3)}] ${currentId.padEnd(12)} | executor  → ${desc}`);

      await new Promise((r) => setTimeout(r, Math.floor(SPEED * 0.5)));

      updateSection(currentId, {
        status: "done", current_step: "done",
        verified_at: new Date().toISOString(),
        last_summary: `${state.description?.slice(0, 35) || "OK"} ✓`,
        attempts: 1,
      });
    } else {
      console.log(`  ${icon} [${String(steps).padStart(3)}] ${currentId.padEnd(12)} | routing`);
    }

    writeHandoff(`# TNS Handoff\n## Last: ${currentId}\n## Step: ${steps}/${maxSteps}\n`);

    // Every 5 steps: dashboard check
    if (steps % 5 === 0) {
      const counts = await checkDashboard();
      if (counts) {
        const done = counts.done || 0;
        const total = Object.values(counts).reduce((a, b) => a + b, 0);
        console.log(`  📊 Dashboard: ${done}/${total} done`);
      }
    }

    const transition = resolveTransition(state, context);
    if (!transition) break;
    currentId = transition.to;
  }

  const finalCounts = await checkDashboard();
  console.log(`\n══════════════════════════════════════════`);
  console.log(`  Steps: ${steps} | Context: ch=${context.current_chapter}, loop=${context.loop_count}`);
  if (finalCounts) console.log(`  Dashboard: ${JSON.stringify(finalCounts)}`);
  console.log(`══════════════════════════════════════════`);
}

main().catch(console.error);
