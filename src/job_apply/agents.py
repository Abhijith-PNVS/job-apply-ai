"""Reusable writer and reviewer implementations."""

from __future__ import annotations

from typing import Protocol, cast

from langchain_openai import ChatOpenAI

from job_apply.matching import MatchReport
from job_apply.models import DraftResult, ReviewResult, ReviewVerdict


class ResumeWriter(Protocol):
    def write(
        self,
        *,
        resume_text: str,
        job_text: str,
        previous_draft: str | None,
        feedback: list[str],
        match_report: MatchReport,
        revision_number: int,
    ) -> DraftResult: ...


class TechReviewer(Protocol):
    def review(
        self,
        *,
        resume_text: str,
        job_text: str,
        draft: str,
        revision_number: int,
    ) -> ReviewResult: ...


class DeterministicResumeWriter:
    """Offline agent used to prove graph behavior without API calls."""

    def __init__(self) -> None:
        self.call_count = 0

    def write(
        self,
        *,
        resume_text: str,
        job_text: str,
        previous_draft: str | None,
        feedback: list[str],
        match_report: MatchReport,
        revision_number: int,
    ) -> DraftResult:
        self.call_count += 1
        if previous_draft is None:
            content = (
                f"# Tailored Resume\n\n{resume_text.strip()}\n\n"
                f"<!-- match coverage: {match_report.overall_coverage:.2f}% -->"
            )
            summary = ["Created the initial evidence-linked text-only draft."]
        else:
            instructions = "; ".join(feedback) or "Improve technical clarity."
            content = (
                f"{previous_draft.rstrip()}\n\n"
                f"<!-- revision {revision_number}: {instructions} -->"
            )
            summary = [f"Applied revision {revision_number}: {instructions}"]
        return DraftResult(content=content, change_summary=summary)


class DeterministicTechReviewer:
    """Offline reviewer that requests revisions until a configured draft index."""

    def __init__(self, *, pass_at_revision: int = 1) -> None:
        self.pass_at_revision = pass_at_revision
        self.call_count = 0

    def review(
        self,
        *,
        resume_text: str,
        job_text: str,
        draft: str,
        revision_number: int,
    ) -> ReviewResult:
        self.call_count += 1
        if revision_number >= self.pass_at_revision:
            return ReviewResult(
                verdict=ReviewVerdict.PASS,
                score=88,
                findings=[],
                revision_instructions=[],
            )
        return ReviewResult(
            verdict=ReviewVerdict.REVISE,
            score=72,
            findings=["The draft needs a clearer description of technical ownership."],
            revision_instructions=["Clarify personal ownership without inventing facts."],
        )


class OpenAIResumeWriter:
    """Live writer using one reusable structured-output model binding."""

    def __init__(self, *, model: str) -> None:
        self._runner = ChatOpenAI(model=model).with_structured_output(
            DraftResult,
            method="json_schema",
            strict=True,
        )

    def write(
        self,
        *,
        resume_text: str,
        job_text: str,
        previous_draft: str | None,
        feedback: list[str],
        match_report: MatchReport,
        revision_number: int,
    ) -> DraftResult:
        prompt = (
            "Create the strongest defensible Markdown resume draft for the job. "
            "Do not change employers, dates, education, or credentials.\n\n"
            f"SOURCE RESUME:\n{resume_text}\n\nJOB DESCRIPTION:\n{job_text}\n\n"
            f"PREVIOUS DRAFT:\n{previous_draft or '(none)'}\n\n"
            f"REVIEW FEEDBACK:\n{feedback or ['(none)']}\n\n"
            f"MATCH REPORT:\n{match_report.model_dump_json()}\n\n"
            f"DRAFT INDEX: {revision_number}"
        )
        return cast(DraftResult, self._runner.invoke(prompt))


class OpenAITechReviewer:
    """Live technical reviewer using one reusable structured-output binding."""

    def __init__(self, *, model: str) -> None:
        self._runner = ChatOpenAI(model=model).with_structured_output(
            ReviewResult,
            method="json_schema",
            strict=True,
        )

    def review(
        self,
        *,
        resume_text: str,
        job_text: str,
        draft: str,
        revision_number: int,
    ) -> ReviewResult:
        prompt = (
            "Act as an independent principal technical reviewer. Review the draft "
            "against the source resume and job. Return pass only when the draft is "
            "technically coherent, defensible, and has no unresolved high-risk claim.\n\n"
            f"SOURCE RESUME:\n{resume_text}\n\nJOB DESCRIPTION:\n{job_text}\n\n"
            f"DRAFT:\n{draft}\n\nDRAFT INDEX: {revision_number}"
        )
        return cast(ReviewResult, self._runner.invoke(prompt))
