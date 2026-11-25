"""Typed contracts shared by the spike agents and graph."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field
from typing_extensions import NotRequired, TypedDict


class ReviewVerdict(StrEnum):
    PASS = "pass"
    REVISE = "revise"


class DraftResult(BaseModel):
    content: str = Field(description="Complete resume draft in Markdown.")
    change_summary: list[str] = Field(default_factory=list)


class ReviewResult(BaseModel):
    verdict: ReviewVerdict
    score: int = Field(ge=0, le=100)
    findings: list[str] = Field(default_factory=list)
    revision_instructions: list[str] = Field(default_factory=list)


class HumanDecision(BaseModel):
    action: Literal["approve", "revise", "stop"]
    draft_hash: str
    note: str = ""
    additional_revisions: int = Field(default=0, ge=0, le=5)


class CandidateClarification(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)
    stop: bool = False


class WorkflowState(TypedDict):
    resume_text: str
    job_text: str
    revision_number: int
    revision_limit: int
    status: str
    candidate_evidence: NotRequired[list[str]]
    asked_questions: NotRequired[list[str]]
    match_report: NotRequired[dict[str, object]]
    draft: NotRequired[dict[str, object]]
    draft_hash: NotRequired[str]
    review: NotRequired[dict[str, object]]
    review_history: NotRequired[list[dict[str, object]]]
    revision_feedback: NotRequired[list[str]]
    human_decision: NotRequired[dict[str, object]]
