"""Minimal local Gradio MVP for dual-response twin output.

This module is intentionally local-first. It only reads local SQLite memory,
uses deterministic in-process twin logic, and does not call network services.
"""

from __future__ import annotations

import importlib
from pathlib import Path

from u_core.memory import SQLiteStore
from u_core.twin import TwinContext, TwinReasoningEngine, build_twin_context


def _default_db_path() -> Path:
    primary = Path.home() / "Library" / "Application Support" / "U" / "db" / "memory.sqlite3"
    fallback = Path.home() / "U" / "data" / "db" / "memory.sqlite3"

    try:
        primary.parent.mkdir(parents=True, exist_ok=True)
        return primary
    except OSError:
        fallback.parent.mkdir(parents=True, exist_ok=True)
        return fallback


def build_planner_preview(user_text: str, context: TwinContext) -> tuple[str, str]:
    cleaned = (user_text or "").strip()
    goal = cleaned if cleaned else "Clarify the immediate next step"

    actions: list[str] = [
        "Define one 25-minute action aligned to this goal.",
        "State one success signal you can verify today.",
    ]

    if context.tags:
        actions.insert(0, f"Prioritize work tagged: {context.tags[0]}.")
    if context.outcomes:
        actions.append(f"Reuse prior winning pattern: {context.outcomes[0]}.")

    actions_text = "\n".join(f"- {item}" for item in actions)
    return goal, actions_text


def generate_dual_outputs(user_text: str, context: TwinContext) -> tuple[str, str, str, str]:
    engine = TwinReasoningEngine()
    response = engine.generate_dual_response(user_text, context)
    planner_goal, planner_actions = build_planner_preview(user_text, context)

    return (
        response.supportive_response,
        response.honest_response,
        planner_goal,
        planner_actions,
    )


def run_local_inference(user_text: str, db_path: Path | None = None) -> tuple[str, str, str, str]:
    target_db_path = db_path or _default_db_path()

    with SQLiteStore(target_db_path) as store:
        store.initialize()
        context = build_twin_context(store)
        return generate_dual_outputs(user_text, context)


def build_app(db_path: Path | None = None):
    gr = importlib.import_module("gradio")

    with gr.Blocks(title="U UI MVP") as app:
        gr.Markdown("# U MVP\nLocal dual-response preview with a simple planner panel.")

        user_input = gr.Textbox(
            label="Your input",
            placeholder="Describe your current situation or ask for guidance...",
            lines=4,
        )
        submit_button = gr.Button("Generate")

        with gr.Row():
            supportive_output = gr.Textbox(label="Supportive U", lines=8)
            honest_output = gr.Textbox(label="Honest U", lines=8)

        gr.Markdown("## Planner Preview")
        planner_goal_output = gr.Textbox(label="Goal", lines=2)
        planner_actions_output = gr.Textbox(label="Proposed actions", lines=6)

        submit_button.click(
            fn=lambda user_text: run_local_inference(user_text, db_path=db_path),
            inputs=[user_input],
            outputs=[
                supportive_output,
                honest_output,
                planner_goal_output,
                planner_actions_output,
            ],
        )

    return app


def launch(db_path: Path | None = None) -> None:
    app = build_app(db_path=db_path)
    app.launch()


if __name__ == "__main__":
    launch()
