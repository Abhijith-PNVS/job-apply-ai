"""Minimal repeatable LangGraph writer/reviewer workflow."""

from __future__ import annotations

import hashlib
from typing import Literal

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from job_apply.agents import ResumeWriter, TechReviewer
from job_apply.matching import DeterministicResumeMatcher, MatchReport
from job_apply.models import (
    CandidateClarification,
    DraftResult,
    HumanDecision,
    ReviewResult,
    ReviewVerdict,
    WorkflowState,
)


def build_workflow(
    writer: ResumeWriter,
    reviewer: TechReviewer,
    matcher: DeterministicResumeMatcher | None = None,
    *,
    checkpointer: BaseCheckpointSaver | None = None,
):
    """Compile the spike graph with reusable injected agent instances."""

    active_matcher = matcher or DeterministicResumeMatcher()

    def match_job(state: WorkflowState) -> dict[str, object]:
        evidence = "\n".join(state.get("candidate_evidence", []))
        resume_text = state["resume_text"]
        if evidence:
            resume_text = f"{resume_text}\n{evidence}"
        report = active_matcher.match(
            resume_text=resume_text, job_text=state["job_text"]
        )
        return {"match_report": report.model_dump(mode="json"), "status": "matched"}

    def route_after_match(
        state: WorkflowState,
    ) -> Literal["candidate_clarification", "generate_draft"]:
        report = MatchReport.model_validate(state["match_report"])
        asked = set(state.get("asked_questions", []))
        return (
            "candidate_clarification"
            if any(question not in asked for question in report.questions)
            else "generate_draft"
        )

    def candidate_clarification(state: WorkflowState) -> dict[str, object]:
        report = MatchReport.model_validate(state["match_report"])
        asked = set(state.get("asked_questions", []))
        questions = [question for question in report.questions if question not in asked]
        response = interrupt(
            {
                "kind": "candidate_clarification",
                "message": "Answer the material matching questions or continue without them.",
                "questions": questions,
            },
            response_schema=CandidateClarification,
        )
        if response.stop:
            return {"status": "stopped"}
        new_evidence = [answer.strip() for answer in response.answers.values() if answer.strip()]
        return {
            "candidate_evidence": [*state.get("candidate_evidence", []), *new_evidence],
            "asked_questions": [*state.get("asked_questions", []), *questions],
            "status": "clarified",
        }

    def route_after_clarification(
        state: WorkflowState,
    ) -> Literal["match_job", "__end__"]:
        return END if state["status"] == "stopped" else "match_job"

    def generate_draft(state: WorkflowState) -> dict[str, object]:
        next_revision = state["revision_number"] + 1
        previous = DraftResult.model_validate(state["draft"]) if state.get("draft") else None
        match_report = MatchReport.model_validate(state["match_report"])
        result = writer.write(
            resume_text=state["resume_text"],
            job_text=state["job_text"],
            previous_draft=previous.content if previous else None,
            feedback=state.get("revision_feedback", []),
            match_report=match_report,
            revision_number=next_revision,
        )
        draft_hash = hashlib.sha256(result.content.encode("utf-8")).hexdigest()
        return {
            "draft": result.model_dump(mode="json"),
            "draft_hash": draft_hash,
            "revision_number": next_revision,
            "revision_feedback": [],
            "status": "drafted",
        }

    def review_draft(state: WorkflowState) -> dict[str, object]:
        draft = DraftResult.model_validate(state["draft"])
        result = reviewer.review(
            resume_text=state["resume_text"],
            job_text=state["job_text"],
            draft=draft.content,
            revision_number=state["revision_number"],
        )
        history = [*state.get("review_history", []), result.model_dump(mode="json")]
        return {
            "review": result.model_dump(mode="json"),
            "review_history": history,
            "status": "reviewed",
        }

    def route_after_review(
        state: WorkflowState,
    ) -> Literal["generate_draft", "human_review"]:
        review = ReviewResult.model_validate(state["review"])
        if review.verdict is ReviewVerdict.PASS:
            return "human_review"
        if state["revision_number"] >= state["revision_limit"]:
            return "human_review"
        return "generate_draft"

    def human_review(state: WorkflowState) -> dict[str, object]:
        review = ReviewResult.model_validate(state["review"])
        decision = interrupt(
            {
                "message": "Review the current draft and Tech God findings.",
                "kind": "human_review",
                "revision_number": state["revision_number"],
                "revision_limit": state["revision_limit"],
                "review": review.model_dump(mode="json"),
                "draft": state["draft"],
                "draft_hash": state["draft_hash"],
            },
            response_schema=HumanDecision,
        )
        if decision.draft_hash != state["draft_hash"]:
            raise ValueError("Human decision does not match the current draft.")
        if decision.action == "approve":
            return {
                "human_decision": decision.model_dump(mode="json"),
                "status": "approved",
            }
        if decision.action == "stop":
            return {
                "human_decision": decision.model_dump(mode="json"),
                "status": "stopped",
            }

        extra = decision.additional_revisions or 1
        feedback = [decision.note] if decision.note else list(review.revision_instructions)
        return {
            "human_decision": decision.model_dump(mode="json"),
            "revision_limit": max(state["revision_limit"], state["revision_number"] + extra),
            "revision_feedback": feedback,
            "status": "revision_requested",
        }

    def route_after_human(
        state: WorkflowState,
    ) -> Literal["generate_draft", "__end__"]:
        return "generate_draft" if state["status"] == "revision_requested" else END

    builder = StateGraph(WorkflowState)
    builder.add_node("match_job", match_job)
    builder.add_node("candidate_clarification", candidate_clarification)
    builder.add_node("generate_draft", generate_draft)
    builder.add_node("review_draft", review_draft)
    builder.add_node("human_review", human_review)
    builder.add_edge(START, "match_job")
    builder.add_conditional_edges("match_job", route_after_match)
    builder.add_conditional_edges("candidate_clarification", route_after_clarification)
    builder.add_edge("generate_draft", "review_draft")
    builder.add_conditional_edges("review_draft", route_after_review)
    builder.add_conditional_edges("human_review", route_after_human)
    return builder.compile(checkpointer=checkpointer or InMemorySaver())


def initial_state(
    *, resume_text: str, job_text: str, revision_limit: int = 3
) -> WorkflowState:
    return WorkflowState(
        resume_text=resume_text,
        job_text=job_text,
        revision_number=-1,
        revision_limit=revision_limit,
        status="new",
        review_history=[],
        revision_feedback=[],
        candidate_evidence=[],
        asked_questions=[],
    )
