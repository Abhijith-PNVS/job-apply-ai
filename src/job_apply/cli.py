"""Command-line demonstration of the compatibility spike."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from langgraph.types import Command

from job_apply.agents import (
    DeterministicResumeWriter,
    DeterministicTechReviewer,
    OpenAIResumeWriter,
    OpenAITechReviewer,
)
from job_apply.graph import build_workflow, initial_state


def _read(path: str | None, fallback: str) -> str:
    return Path(path).read_text(encoding="utf-8") if path else fallback


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the LangGraph compatibility spike.")
    parser.add_argument("--resume")
    parser.add_argument("--job")
    parser.add_argument("--live", action="store_true", help="Use OpenAI instead of offline agents.")
    parser.add_argument("--auto-approve", action="store_true")
    args = parser.parse_args()

    load_dotenv()
    if args.live:
        model = os.getenv("OPENAI_MODEL")
        if not os.getenv("OPENAI_API_KEY") or not model:
            raise SystemExit("Live mode requires OPENAI_API_KEY and OPENAI_MODEL in .env.")
        writer = OpenAIResumeWriter(model=model)
        reviewer = OpenAITechReviewer(model=model)
    else:
        writer = DeterministicResumeWriter()
        reviewer = DeterministicTechReviewer(pass_at_revision=1)

    resume_text = _read(args.resume, "Python engineer who built internal automation.")
    job_text = _read(args.job, "Seeking a Python engineer with clear technical ownership.")
    graph = build_workflow(writer, reviewer)
    config = {"configurable": {"thread_id": str(uuid4())}}
    result = graph.invoke(initial_state(resume_text=resume_text, job_text=job_text), config)

    while "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        if payload.get("kind") == "candidate_clarification":
            answers = {
                question: input(f"{question}\nAnswer (blank to skip): ").strip()
                for question in payload["questions"]
            }
            result = graph.invoke(
                Command(resume={"answers": answers, "stop": False}), config
            )
            continue
        print(f"Draft {payload['revision_number']} scored {payload['review']['score']}.")
        if args.auto_approve:
            action = "approve"
        else:
            action = input("Choose approve, revise, or stop: ").strip().lower()
        note = ""
        if action == "revise":
            note = input("One revision instruction: ").strip()
        result = graph.invoke(
            Command(
                resume={
                    "action": action,
                    "draft_hash": payload["draft_hash"],
                    "note": note,
                    "additional_revisions": 1 if action == "revise" else 0,
                }
            ),
            config,
        )

    print(f"Workflow status: {result['status']}")
    print(result["draft"]["content"])


if __name__ == "__main__":
    main()
