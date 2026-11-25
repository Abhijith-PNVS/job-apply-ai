"""Deterministic company summary and job-quality signals."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from job_apply.discovery import JobPosting


class GhostJobAssessment(BaseModel):
    score: int = Field(ge=0, le=100)
    signals: list[str] = Field(default_factory=list)


class CompanyBrief(BaseModel):
    company: str
    open_role_count: int
    titles: list[str]
    locations: list[str]
    hiring_signals: list[str]


_VAGUE_PHRASES = {
    "rockstar",
    "ninja",
    "wear many hats",
    "fast-paced environment",
    "competitive salary",
}


def assess_job_quality(posting: JobPosting) -> GhostJobAssessment:
    description = posting.description.casefold()
    score = 100
    signals: list[str] = []
    if len(description.split()) < 40:
        score -= 25
        signals.append("Description is unusually short.")
    vague = sorted(phrase for phrase in _VAGUE_PHRASES if phrase in description)
    if vague:
        score -= min(25, 5 * len(vague))
        signals.append("Vague phrases: " + ", ".join(vague))
    if not re.search(r"responsibilit|required|qualification|you will", description):
        score -= 20
        signals.append("No clear responsibilities or qualifications section.")
    if not posting.location:
        score -= 10
        signals.append("Location is missing.")
    if not posting.url.startswith("https://"):
        score -= 20
        signals.append("Posting URL is not HTTPS.")
    return GhostJobAssessment(score=max(0, score), signals=signals)


def build_company_brief(company: str, postings: list[JobPosting]) -> CompanyBrief:
    relevant = [item for item in postings if item.company.casefold() == company.casefold()]
    titles = sorted({item.title for item in relevant})
    locations = sorted({item.location for item in relevant if item.location})
    signals = []
    if len(relevant) >= 3:
        signals.append(f"Company has {len(relevant)} concurrently indexed openings.")
    engineering_roles = [title for title in titles if "engineer" in title.casefold()]
    if len(engineering_roles) >= 2:
        signals.append("Multiple engineering roles suggest active team growth.")
    return CompanyBrief(
        company=company,
        open_role_count=len(relevant),
        titles=titles,
        locations=locations,
        hiring_signals=signals,
    )
