from __future__ import annotations

from langgraph.types import Command

from job_apply.agents import DeterministicResumeWriter, DeterministicTechReviewer
from job_apply.graph import build_workflow, initial_state


def _config(thread_id: str) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": thread_id}}


def test_reuses_agents_across_revision_loop_and_resumes_approval() -> None:
    writer = DeterministicResumeWriter()
    reviewer = DeterministicTechReviewer(pass_at_revision=1)
    graph = build_workflow(writer, reviewer)
    config = _config("reuse-agents")

    paused = graph.invoke(
        initial_state(resume_text="Python engineer", job_text="Python role"), config
    )

    assert "__interrupt__" in paused
    assert paused["revision_number"] == 1
    assert writer.call_count == 2
    assert reviewer.call_count == 2

    completed = graph.invoke(
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
    assert writer.call_count == 2
    assert reviewer.call_count == 2


def test_limit_pauses_then_human_can_extend_the_same_run() -> None:
    writer = DeterministicResumeWriter()
    reviewer = DeterministicTechReviewer(pass_at_revision=2)
    graph = build_workflow(writer, reviewer)
    config = _config("extend-run")

    first_pause = graph.invoke(
        initial_state(
            resume_text="Automation engineer",
            job_text="Production Python engineer",
            revision_limit=0,
        ),
        config,
    )
    assert first_pause["revision_number"] == 0
    assert first_pause["review"]["verdict"] == "revise"

    second_pause = graph.invoke(
        Command(
            resume={
                "action": "revise",
                "draft_hash": first_pause["draft_hash"],
                "note": "Clarify ownership.",
                "additional_revisions": 2,
            }
        ),
        config,
    )

    assert "__interrupt__" in second_pause
    assert second_pause["revision_number"] == 2
    assert second_pause["review"]["verdict"] == "pass"
    assert writer.call_count == 3
    assert reviewer.call_count == 3


def test_human_can_stop_without_an_extra_generation() -> None:
    writer = DeterministicResumeWriter()
    reviewer = DeterministicTechReviewer(pass_at_revision=0)
    graph = build_workflow(writer, reviewer)
    config = _config("stop-run")

    paused = graph.invoke(
        initial_state(resume_text="Engineer", job_text="Engineering role"), config
    )
    completed = graph.invoke(
        Command(
            resume={
                "action": "stop",
                "draft_hash": paused["draft_hash"],
                "note": "",
                "additional_revisions": 0,
            }
        ),
        config,
    )

    assert "__interrupt__" in paused
    assert completed["status"] == "stopped"
    assert writer.call_count == 1
    assert reviewer.call_count == 1


def test_approval_is_bound_to_the_current_draft() -> None:
    writer = DeterministicResumeWriter()
    reviewer = DeterministicTechReviewer(pass_at_revision=0)
    graph = build_workflow(writer, reviewer)
    config = _config("draft-binding")
    graph.invoke(initial_state(resume_text="Engineer", job_text="Role"), config)

    try:
        graph.invoke(
            Command(
                resume={
                    "action": "approve",
                    "draft_hash": "stale-draft",
                    "note": "",
                    "additional_revisions": 0,
                }
            ),
            config,
        )
    except ValueError as error:
        assert "current draft" in str(error)
    else:
        raise AssertionError("A stale draft approval must be rejected.")


def test_candidate_answer_is_saved_then_matching_runs_again() -> None:
    writer = DeterministicResumeWriter()
    reviewer = DeterministicTechReviewer(pass_at_revision=0)
    graph = build_workflow(writer, reviewer)
    config = _config("clarification")

    clarification = graph.invoke(
        initial_state(
            resume_text="Created Python automation.",
            job_text="Required: production Python services",
        ),
        config,
    )
    clarification_payload = clarification["__interrupt__"][0].value
    assert clarification_payload["kind"] == "candidate_clarification"

    review_pause = graph.invoke(
        Command(
            resume={
                "answers": {
                    clarification_payload["questions"][0]: (
                        "Built production Python services."
                    )
                },
                "stop": False,
            }
        ),
        config,
    )

    assert review_pause["__interrupt__"][0].value["kind"] == "human_review"
    assert review_pause["match_report"]["required_coverage"] == 100.0
    assert len(review_pause["asked_questions"]) == 1
