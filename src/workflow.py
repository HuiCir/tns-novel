"""
Novel writing workflow - powered by Claude API + TNS-style orchestration.

Replaces LangGraph's StateGraph with a section-based workflow engine
(src/orchestrator.py) while keeping all agent logic, prompts, validation,
and the multi-agent supervisor architecture intact.

Architecture:
  - Workflow = collection of Section objects with conditional transitions
  - Each Section has a handler(state) -> dict
  - The stream() wrapper merges returned dicts into state after each section
  - Check (routing) sections are kept separate from validate sections
    so they see the correctly merged state — matching LangGraph behavior
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, Any, Iterator, AsyncIterator, Optional

from src.orchestrator import Workflow, Section, Transition
from src.agent import (
    OutlineGeneratorAgent,
    CharacterAgent,
    WriterAgent,
    ReflectAgent,
    EntityAgent,
)
from src.node import *
from src.feedback_nodes import (
    outline_feedback_node, process_outline_feedback_node, check_outline_feedback_node,
    character_feedback_node, process_character_feedback_node, check_character_feedback_node,
    chapter_feedback_node, process_chapter_feedback_node, check_chapter_feedback_deep_mode_node
)
from src.supervisor_node import supervisor_node, init_supervisor_node
from src.state import NovelState
from src.log_config import loggers
from src.model_manager import create_model_manager
from src.config_loader import (
    OutlineConfig,
    CharacterConfig,
    WriterConfig,
    ReflectConfig,
    BaseConfig,
    ModelConfig
)
from src.agents.registry import AgentRegistry

logger = loggers['workflow']


def _get_agent(agent_name: str, model_manager, config) -> object:
    if AgentRegistry.is_registered(agent_name):
        logger.info(f"[Workflow] 从注册表获取 Agent: {agent_name}")
        return AgentRegistry.get(agent_name, model_manager=model_manager, config=config)
    agent_map = {
        "outline": OutlineGeneratorAgent,
        "character": CharacterAgent,
        "writer": WriterAgent,
        "reflect": ReflectAgent,
        "entity": EntityAgent,
    }
    agent_class = agent_map.get(agent_name)
    if agent_class:
        logger.info(f"[Workflow] 直接实例化 Agent: {agent_name}")
        return agent_class(model_manager, config)
    raise KeyError(f"Unknown agent: {agent_name}")


# ---------------------------------------------------------------------------
#  Helpers: convert original check functions (return str) into section handlers
# ---------------------------------------------------------------------------

def _check_section(check_fn):
    """Wrap a check function (returns routing str) as a section handler.

    The handler returns {'_route': routing_decision} only.
    State is NOT modified — it's already been updated by the preceding
    validate section via the stream wrapper.
    """
    def handler(state: NovelState) -> Dict[str, Any]:
        route = check_fn(state)
        return {"_route": route}
    return handler


# ---------------------------------------------------------------------------
#  Compiled Workflow wrapper (compatible with LangGraph's .stream() API)
# ---------------------------------------------------------------------------

class CompiledWorkflow:
    """Wraps a compiled Workflow to provide .stream() and .astream()
    methods compatible with LangGraph's compiled_graph.stream()."""

    def __init__(self, workflow: Workflow):
        self._workflow = workflow

    def stream(self, initial_state: dict, config: Optional[dict] = None) -> Iterator[Dict[str, dict]]:
        """Yields {section_id: full_state_dict} dicts, matching LangGraph's API."""
        from src.orchestrator import WorkflowRunner

        # Build NovelState from initial dict
        state = NovelState(**{k: v for k, v in initial_state.items()
                              if k in NovelState.model_fields})
        for k, v in initial_state.items():
            if k not in NovelState.model_fields:
                try:
                    object.__setattr__(state, k, v)
                except Exception:
                    pass

        runner = WorkflowRunner(self._workflow)
        for section_id, update in runner.run(state):
            # Check for orchestrator error signals
            if update.get("_blocked"):
                logger.error(f"Section '{section_id}' blocked: {update.get('_section_error')}")
                break

            # Merge returned updates into state
            for k, v in update.items():
                if k.startswith("_"):
                    continue
                try:
                    setattr(state, k, v)
                except (AttributeError, ValueError):
                    pass

            # Yield full state as dict (callers expect all fields)
            state_dict = self._state_to_dict(state)
            # Carry _route so callers can inspect it if needed
            if "_route" in update:
                state_dict["_route"] = update["_route"]
            yield {section_id: state_dict}

    async def astream(self, initial_state: dict, config: Optional[dict] = None) -> AsyncIterator[Dict[str, dict]]:
        for item in self.stream(initial_state, config):
            yield item
            await asyncio.sleep(0)

    def _state_to_dict(self, state: NovelState) -> dict:
        """Convert NovelState to plain dict, including non-model fields."""
        d = state.model_dump()
        for k, v in state.__dict__.items():
            if k not in d and not k.startswith("_"):
                d[k] = v
        return d


# =============================================================================
#  create_workflow: main entry point
# =============================================================================

def create_workflow(
    model_config: ModelConfig,
    Agent_config: BaseConfig = None,
    execution_mode: str = "serial"
) -> CompiledWorkflow:
    """创建 TNS-style 小说创作工作流。

    Sections mirror the original LangGraph nodes but use conditional
    transitions instead of add_conditional_edges. Validate + check are
    kept as separate sections so check functions see the merged state.
    """

    model_manager = create_model_manager(model_config, execution_mode)
    logger.info(f"成功加载{model_config.model_type}模型管理器")

    outline_cfg = Agent_config if Agent_config is not None else OutlineConfig
    master_outline = outline_cfg.master_outline

    if not AgentRegistry.list_agents():
        from src.agents.setup import register_builtin_agents
        register_builtin_agents()

    outline_agent = _get_agent("outline", model_manager, outline_cfg)
    character_agent = _get_agent("character", model_manager, CharacterConfig)
    writer_agent = _get_agent("writer", model_manager, WriterConfig)
    reflect_agent = _get_agent("reflect", model_manager, ReflectConfig)

    init_supervisor_node(model_manager)

    logger.info("代理初始化完成, 开始构建 TNS-style 工作流...")

    # =========================================================================
    #  Build Workflow
    # =========================================================================
    wf = Workflow(entry="generate_outline")

    # Convenience: a generate section always routes to success
    def gen_section(id: str, title: str, handler_fn, next_id: str):
        """Create a generate section that routes to next_id on success."""
        def wrapped(state):
            result = handler_fn(state)
            result["_route"] = "success"
            return result
        wf.add_section(Section(
            id=id, title=title, handler=wrapped,
            transitions=[Transition(field="_route", equals="success", next=next_id)],
        ))

    # A check section routes based on the check function's return value
    def chk_section(id: str, title: str, check_fn, routes: dict):
        """Create a check section. routes maps routing_str -> section_id (or None for end)."""
        transitions = []
        for route_val, next_id in routes.items():
            if next_id is None:
                transitions.append(Transition(field="_route", equals=route_val, end=True))
            else:
                transitions.append(Transition(field="_route", equals=route_val, next=next_id))
        wf.add_section(Section(
            id=id, title=title, handler=_check_section(check_fn),
            transitions=transitions,
        ))

    # ---- Outline (master_outline or single-volume) ----
    if master_outline:
        gen_section("generate_outline", "Generate Master Outline",
                    lambda s: generate_master_outline_node(s, outline_agent),
                    "validate_master_outline")
        gen_section("validate_master_outline", "Validate Master Outline",
                    validate_master_outline_node, "check_master_outline")
        chk_section("check_master_outline", "Check Master Outline",
                    check_master_outline_node, {
                        "success": "generate_volume_outline",
                        "retry": "generate_outline",
                        "failure": None,  # end
                    })

        gen_section("generate_volume_outline", "Generate Volume Outline",
                    lambda s: generate_volume_outline_node(s, outline_agent),
                    "validate_volume_outline")
        gen_section("validate_volume_outline", "Validate Volume Outline",
                    validate_volume_outline_node, "check_volume_outline")
        chk_section("check_volume_outline", "Check Volume Outline",
                    check_volume_outline_node, {
                        "success": "volume2character",
                        "retry": "generate_volume_outline",
                        "failure": None,
                    })

        wf.add_section(Section(
            id="volume2character", title="Volume to Character Bridge",
            handler=lambda s: {**volume2character(s), "_route": "success"},
            transitions=[Transition(field="_route", equals="success", next="accpet_outline")],
        ))
        # accpet_outline both saves the volume AND checks completion
        wf.add_section(Section(
            id="accpet_outline", title="Accept Outline Volume",
            handler=lambda s: {
                **accept_outline_node(s),
                "_route": check_outline_completion_node(s)
            },
            transitions=[
                Transition(field="_route", equals="complete", next="outline_feedback"),
                Transition(field="_route", equals="continue", next="generate_volume_outline"),
            ],
        ))
    else:
        gen_section("generate_outline", "Generate Outline",
                    lambda s: generate_outline_node(s, outline_agent),
                    "validate_outline")
        gen_section("validate_outline", "Validate Outline",
                    validate_outline_node, "check_outline")
        chk_section("check_outline", "Check Outline",
                    check_outline_node, {
                        "success": "outline_feedback",
                        "retry": "generate_outline",
                        "failure": None,
                    })

    # ---- Outline Feedback ----
    wf.add_section(Section(
        id="outline_feedback", title="Outline Feedback",
        handler=lambda s: {**outline_feedback_node(s), "_route": "success"},
        transitions=[Transition(field="_route", equals="success", next="process_outline_feedback")],
    ))
    wf.add_section(Section(
        id="process_outline_feedback", title="Process Outline Feedback",
        handler=lambda s: {
            **process_outline_feedback_node(s),
            "_route": check_outline_feedback_node(s)
        },
        transitions=[
            Transition(field="_route", equals="success", next="generate_characters"),
            Transition(field="_route", equals="retry", next="generate_outline"),
            Transition(field="_route", equals="failure", end=True),
        ],
    ))

    # ---- Characters ----
    gen_section("generate_characters", "Generate Characters",
                lambda s: generate_characters_node(s, character_agent),
                "validate_characters")
    gen_section("validate_characters", "Validate Characters",
                validate_characters_node, "check_characters")
    chk_section("check_characters", "Check Characters",
                check_characters_node, {
                    "success": "character_feedback",
                    "retry": "generate_characters",
                    "failure": None,
                })

    # ---- Character Feedback ----
    wf.add_section(Section(
        id="character_feedback", title="Character Feedback",
        handler=lambda s: {**character_feedback_node(s), "_route": "success"},
        transitions=[Transition(field="_route", equals="success", next="process_character_feedback")],
    ))
    wf.add_section(Section(
        id="process_character_feedback", title="Process Character Feedback",
        handler=lambda s: {
            **process_character_feedback_node(s),
            "_route": check_character_feedback_node(s)
        },
        transitions=[
            Transition(field="_route", equals="success", next="route_to_writing"),
            Transition(field="_route", equals="retry", next="generate_characters"),
            Transition(field="_route", equals="failure", end=True),
        ],
    ))

    # ---- Execution Mode Routing ----
    wf.add_section(Section(
        id="route_to_writing", title="Route to Writing Mode",
        handler=lambda s: {
            **route_to_writing_node(s),
            "_route": check_execution_mode_node(s)
        },
        transitions=[
            Transition(field="_route", equals="serial", next="write_chapter"),
            Transition(field="_route", equals="parallel", next="batch_write_chapters"),
        ],
    ))

    # ---- Batch Parallel Writing ----
    gen_section("batch_write_chapters", "Batch Write Chapters",
                lambda s: batch_write_chapters_node(s, writer_agent),
                "batch_validate_chapters")
    wf.add_section(Section(
        id="batch_validate_chapters", title="Batch Validate Chapters",
        handler=lambda s: {
            **batch_validate_chapters_node(s),
            "_route": check_batch_completion_node(s)
        },
        transitions=[
            Transition(field="_route", equals="continue_serial", next="chapter_feedback"),
            Transition(field="_route", equals="continue_parallel", next="route_to_writing"),
            Transition(field="_route", equals="complete", next="success"),
        ],
    ))

    # ---- Chapter Writing ----
    gen_section("write_chapter", "Write Chapter",
                lambda s: write_chapter_node(s, writer_agent),
                "validate_chapter")
    gen_section("validate_chapter", "Validate Chapter",
                validate_chapter_node, "check_chapter")
    chk_section("check_chapter", "Check Chapter",
                check_chapter_node, {
                    "success": "chapter_feedback",
                    "retry": "write_chapter",
                    "failure": None,
                })

    # ---- Chapter Feedback ----
    wf.add_section(Section(
        id="chapter_feedback", title="Chapter Feedback",
        handler=lambda s: {**chapter_feedback_node(s), "_route": "success"},
        transitions=[Transition(field="_route", equals="success", next="process_chapter_feedback")],
    ))
    wf.add_section(Section(
        id="process_chapter_feedback", title="Process Chapter Feedback",
        handler=lambda s: {
            **process_chapter_feedback_node(s),
            "_route": check_chapter_feedback_deep_mode_node(s)
        },
        transitions=[
            Transition(field="_route", equals="success", next="evaluate_chapter"),
            Transition(field="_route", equals="deep_skip", next="supervisor_node"),
            Transition(field="_route", equals="retry", next="write_chapter"),
            Transition(field="_route", equals="failure", end=True),
        ],
    ))

    # ---- Evaluation ----
    gen_section("evaluate_chapter", "Evaluate Chapter",
                lambda s: evaluate_chapter_node(s, reflect_agent),
                "validate_evaluate")
    gen_section("validate_evaluate", "Validate Evaluation",
                validate_evaluate_node, "evaluate_report")

    wf.add_section(Section(
        id="evaluate_report", title="Generate Evaluation Report",
        handler=lambda s: {
            **evaluate_report_node(s, reflect_agent),
            "_route": check_evaluation_node(s)
        },
        transitions=[
            Transition(field="_route", equals="success", next="evaluate2wirte"),
            Transition(field="_route", equals="retry", next="evaluate_chapter"),
            Transition(field="_route", equals="failure", end=True),
        ],
    ))
    wf.add_section(Section(
        id="evaluate2wirte", title="Evaluation to Chapter Bridge",
        handler=lambda s: {
            **evaluation_to_chapter_node(s),
            "_route": check_evaluation_chapter_node(s)
        },
        transitions=[
            Transition(field="_route", equals="accept", next="supervisor_node"),
            Transition(field="_route", equals="revise", next="write_chapter"),
            Transition(field="_route", equals="force_accpet", next="accpet_chapter"),
            Transition(field="_route", equals="fast_accept", next="accpet_chapter"),
        ],
    ))

    # ---- Supervisor ----
    wf.add_section(Section(
        id="supervisor_node", title="Supervisor Review",
        handler=lambda s: {
            **supervisor_node(s),
            "_route": "revise" if getattr(s, 'revision_needed', False) else "accept_chapter"
        },
        transitions=[
            Transition(field="_route", equals="revise", next="write_chapter"),
            Transition(field="_route", equals="accept_chapter", next="accpet_chapter"),
        ],
    ))

    # ---- Accept Chapter ----
    wf.add_section(Section(
        id="accpet_chapter", title="Accept Chapter",
        handler=lambda s: {
            **accept_chapter_node(s),
            "_route": check_chapter_completion_node(s)
        },
        transitions=[
            Transition(field="_route", equals="complete", next="success"),
            Transition(field="_route", equals="continue", next="write_chapter"),
        ],
    ))

    # ---- Terminal Sections ----
    wf.add_section(Section(
        id="success", title="Success",
        handler=lambda s: {
            "result": "小说创作流程完成",
            "final_outline": s.novel_storage.load_outline(),
            "final_characters": s.novel_storage.load_characters(),
            "final_content": s.novel_storage.load_all_chapters(),
            "_route": "end"
        },
        transitions=[Transition(field="_route", equals="end", end=True)],
    ))

    wf.add_section(Section(
        id="failure", title="Failure",
        handler=lambda s: {
            "result": "生成失败",
            "final_error": (s.outline_validated_error or s.characters_validated_error
                           or s.current_chapter_validated_error
                           or s.evaluation_validated_error),
            "_route": "end"
        },
        transitions=[Transition(field="_route", equals="end", end=True)],
    ))

    logger.info("TNS-style 工作流构建完成, 编译中...")
    return CompiledWorkflow(wf.compile())
