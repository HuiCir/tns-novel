"""
TNS-style Section Orchestrator

Replaces LangGraph's StateGraph with a section-based workflow engine:
- Sections define workflow steps with transitions and validators
- Each section tracks its own status (pending/in_progress/needs_fix/done/blocked)
- Conditional transitions based on section output fields
- Built-in retry with max_attempts per section

Pattern inspired by TNS (Tool-using Natural-language System).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Literal, Optional, Union
from enum import Enum

logger = logging.getLogger(__name__)


class SectionStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    needs_fix = "needs_fix"
    done = "done"
    blocked = "blocked"


@dataclass
class Transition:
    """Conditional transition from a section to another section."""
    field: str                                  # State field to check
    equals: Optional[Any] = None                # Match exact value
    not_equals: Optional[Any] = None             # Match anything but this
    in_set: Optional[List[Any]] = None           # Match any in set
    truthy: Optional[bool] = None               # Match truthy/falsy
    next: Optional[str] = None                  # Target section id
    end: bool = False                           # True = workflow ends

    def matches(self, value: Any) -> bool:
        if self.equals is not None and value == self.equals:
            return True
        if self.not_equals is not None and value != self.not_equals:
            return True
        if self.in_set is not None and value in self.in_set:
            return True
        if self.truthy is not None:
            if self.truthy and value:
                return True
            if not self.truthy and not value:
                return True
        return False


@dataclass
class Section:
    """A single step in the workflow."""
    id: str
    title: str
    handler: Callable                                  # fn(state) -> Dict[str, Any]
    transitions: List[Transition] = field(default_factory=list)
    default_transition: Optional[str] = None            # Fallback if no transition matches
    max_attempts: int = 10
    attempts: int = 0
    status: SectionStatus = SectionStatus.pending
    last_error: Optional[str] = None

    def reset(self):
        self.attempts = 0
        self.status = SectionStatus.pending
        self.last_error = None


@dataclass
class Workflow:
    """A complete workflow definition (TNS-style)."""
    entry: str                                         # Entry section id
    sections: Dict[str, Section] = field(default_factory=dict)
    max_steps: int = 500                               # Safety limit

    def add_section(self, section: Section) -> "Workflow":
        self.sections[section.id] = section
        return self

    def compile(self) -> "Workflow":
        """Validate the workflow (analogous to LangGraph's compile)."""
        if self.entry not in self.sections:
            raise ValueError(f"Entry section '{self.entry}' not found")
        for sid, sec in self.sections.items():
            for t in sec.transitions:
                if t.next and t.next not in self.sections:
                    raise ValueError(
                        f"Section '{sid}' has transition to unknown section '{t.next}'"
                    )
        return self


class WorkflowRunner:
    """Executes a compiled Workflow, stepping through sections.

    Usage:
        wf = Workflow(entry="generate_outline")
        wf.add_section(Section(id="generate_outline", handler=...))
        runner = WorkflowRunner(wf)
        for section_id, state_update in runner.run(initial_state):
            state.update(state_update)
            # emit progress, check for end, etc.
    """

    def __init__(self, workflow: Workflow):
        self.workflow = workflow

    def run(self, state: Any) -> Any:
        """Generator that yields (section_id, state_update) at each step.

        The caller merges state_update into their state object and
        inspects for termination (section transitions with end=True).
        """
        current_id = self.workflow.entry
        steps = 0

        while current_id is not None and steps < self.workflow.max_steps:
            section = self.workflow.sections.get(current_id)
            if section is None:
                logger.error(f"Section '{current_id}' not found")
                break

            section.status = SectionStatus.in_progress
            steps += 1

            # Execute handler
            try:
                section.attempts += 1
                result = section.handler(state)
                section.last_error = None
                section.status = SectionStatus.done
            except Exception as e:
                section.last_error = str(e)
                logger.warning(
                    f"Section '{current_id}' failed (attempt {section.attempts}/{section.max_attempts}): {e}"
                )
                if section.attempts < section.max_attempts:
                    section.status = SectionStatus.needs_fix
                    # Re-yield same section for retry (caller increments attempt in state)
                    yield current_id, {"_section_error": str(e)}
                    continue
                else:
                    section.status = SectionStatus.blocked
                    yield current_id, {"_section_error": str(e), "_blocked": True}
                    break

            yield current_id, result

            # Resolve next section via transitions
            next_id = self._resolve_transition(section, result)
            if next_id is None:
                logger.info(f"Workflow ended at section '{current_id}' (end=True)")
                break

            current_id = next_id

    def _resolve_transition(self, section: Section, result: Dict[str, Any]) -> Optional[str]:
        """Find the first matching transition."""
        for t in section.transitions:
            if t.end:
                return None
            if t.field and t.field in result:
                value = result[t.field]
                if t.matches(value):
                    logger.debug(
                        f"Transition: {section.id} -> {t.next} (field={t.field}, value={value})"
                    )
                    return t.next
            elif t.field is None:
                # Unconditional transition (always matches)
                if t.end:
                    return None
                logger.debug(f"Unconditional transition: {section.id} -> {t.next}")
                return t.next

        # Fallback to default transition
        if section.default_transition:
            logger.debug(
                f"Default transition: {section.id} -> {section.default_transition}"
            )
            return section.default_transition

        logger.warning(f"No transition matched for section '{section.id}', ending workflow")
        return None


# ---------------------------------------------------------------------------
#  Convenience: decorator for creating transition-checker lambdas
# ---------------------------------------------------------------------------

def transition(field: str, mapping: Dict[Any, str], default: Optional[str] = None) -> Callable:
    """Create a routing function from a field-to-section-id mapping.

    This replaces LangGraph's add_conditional_edges pattern:

        # Old (LangGraph):
        workflow.add_conditional_edges("validate_outline", check_outline_node, {
            "success": "outline_feedback",
            "retry": "generate_outline",
            "failure": "failure"
        })

        # New (TNS-style):
        Section(
            id="validate_outline",
            handler=validate_outline_node,
            transitions=[
                Transition(field="_route", equals="success", next="outline_feedback"),
                Transition(field="_route", equals="retry", next="generate_outline"),
                Transition(field="_route", equals="failure", end=True),
            ]
        )
    """
    def router(state) -> str:
        val = getattr(state, field, None)
        return mapping.get(val, default)
    return router
