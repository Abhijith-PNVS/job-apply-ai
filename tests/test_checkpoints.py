from langgraph.types import Command

from job_apply.agents import DeterministicResumeWriter, DeterministicTechReviewer
from job_apply.checkpoints import sqlite_checkpointer
from job_apply.graph import build_workflow, initial_state


def test_interrupted_run_resumes_after_checkpointer_reopens(tmp_path) -> None:
    checkpoint_path = tmp_path / "checkpoints.db"
    config = {"configurable": {"thread_id": "durable-run"}}

    with sqlite_checkpointer(checkpoint_path) as saver:
        first_graph = build_workflow(
            DeterministicResumeWriter(),
            DeterministicTechReviewer(pass_at_revision=0),
            checkpointer=saver,
        )
        paused = first_graph.invoke(
            initial_state(resume_text="Python engineer", job_text="Python role"),
            config,
        )
        assert "__interrupt__" in paused

    with sqlite_checkpointer(checkpoint_path) as saver:
        resumed_graph = build_workflow(
            DeterministicResumeWriter(),
            DeterministicTechReviewer(pass_at_revision=0),
            checkpointer=saver,
        )
        completed = resumed_graph.invoke(
            Command(
                resume={
                    "action": "approve",
                    "draft_hash": paused["draft_hash"],
                    "note": "",
                    "additional_revisions": 0,
                }
            ),
            config,
        )

    assert completed["status"] == "approved"
    assert completed["draft_hash"] == paused["draft_hash"]
