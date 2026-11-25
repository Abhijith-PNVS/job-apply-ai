"""Deterministic matcher contracts and an offline baseline implementation."""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, Field


class RequirementImportance(StrEnum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    INFERRED = "inferred"


class MatchStatus(StrEnum):
    STRONG = "strong_match"
    PARTIAL = "partial_match"
    UNCLEAR = "unclear"
    NONE = "no_match"


class EvidenceItem(BaseModel):
    id: str
    text: str


class JobRequirement(BaseModel):
    id: str
    text: str
    normalized_text: str


class RequirementGroup(BaseModel):
    id: str
    importance: RequirementImportance
    operator: str = Field(pattern="^(all|any)$")
    alternatives: list[JobRequirement] = Field(min_length=1)


class RequirementMatch(BaseModel):
    group_id: str
    status: MatchStatus
    matched_requirement_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    explanation: str


class MatchReport(BaseModel):
    groups: list[RequirementGroup]
    evidence: list[EvidenceItem]
    matches: list[RequirementMatch]
    required_coverage: float = Field(ge=0, le=100)
    preferred_coverage: float = Field(ge=0, le=100)
    overall_coverage: float = Field(ge=0, le=100)
    questions: list[str] = Field(default_factory=list)


_PREFIXES = {
    "required": RequirementImportance.REQUIRED,
    "must": RequirementImportance.REQUIRED,
    "preferred": RequirementImportance.PREFERRED,
    "nice to have": RequirementImportance.PREFERRED,
    "responsibility": RequirementImportance.INFERRED,
}
_STOPWORDS = {
    "a", "an", "and", "experience", "in", "of", "or", "the", "to", "with",
    "years", "year", "knowledge", "strong",
}


def _normalize(value: str) -> str:
    tokens = re.findall(r"[a-z0-9+#.]+", value.casefold())
    return " ".join(token.rstrip(".") for token in tokens if token.rstrip("."))


def _tokens(value: str) -> set[str]:
    return {token for token in _normalize(value).split() if token not in _STOPWORDS}


class DeterministicResumeMatcher:
    """Transparent text matcher used for fixtures and offline development."""

    def __init__(self) -> None:
        self.call_count = 0

    def match(self, *, resume_text: str, job_text: str) -> MatchReport:
        self.call_count += 1
        groups = self._extract_groups(job_text)
        evidence = self._extract_evidence(resume_text)
        matches = [self._match_group(group, evidence) for group in groups]
        return MatchReport(
            groups=groups,
            evidence=evidence,
            matches=matches,
            required_coverage=self._coverage(groups, matches, {RequirementImportance.REQUIRED}),
            preferred_coverage=self._coverage(groups, matches, {RequirementImportance.PREFERRED}),
            overall_coverage=self._coverage(groups, matches, set(RequirementImportance)),
            questions=[
                f"Can you provide evidence for: {group.alternatives[0].text}?"
                for group, match in zip(groups, matches, strict=True)
                if group.importance is RequirementImportance.REQUIRED
                if match.status in {MatchStatus.PARTIAL, MatchStatus.UNCLEAR}
            ],
        )

    def _extract_groups(self, job_text: str) -> list[RequirementGroup]:
        lines = [line.strip(" \t-*•") for line in job_text.splitlines() if line.strip()]
        groups: list[RequirementGroup] = []
        for group_index, raw_line in enumerate(lines, start=1):
            importance = RequirementImportance.INFERRED
            text = raw_line
            lowered = raw_line.casefold()
            for prefix, candidate in _PREFIXES.items():
                marker = f"{prefix}:"
                if lowered.startswith(marker):
                    importance = candidate
                    text = raw_line[len(marker):].strip()
                    break
            alternative_texts = [
                part.strip() for part in re.split(r"\s+or\s+", text, flags=re.I)
            ]
            alternatives = [
                JobRequirement(
                    id=f"req-{group_index}-{alternative_index}",
                    text=alternative,
                    normalized_text=_normalize(alternative),
                )
                for alternative_index, alternative in enumerate(alternative_texts, start=1)
                if alternative
            ]
            if alternatives:
                groups.append(
                    RequirementGroup(
                        id=f"group-{group_index}",
                        importance=importance,
                        operator="any" if len(alternatives) > 1 else "all",
                        alternatives=alternatives,
                    )
                )
        return groups

    def _extract_evidence(self, resume_text: str) -> list[EvidenceItem]:
        fragments = [
            fragment.strip(" \t-*•")
            for fragment in re.split(r"[\r\n]+|(?<=[.!?])\s+", resume_text)
            if fragment.strip(" \t-*•")
        ]
        return [
            EvidenceItem(id=f"evidence-{index}", text=fragment)
            for index, fragment in enumerate(fragments, start=1)
        ]

    def _match_group(
        self, group: RequirementGroup, evidence: list[EvidenceItem]
    ) -> RequirementMatch:
        candidates: list[tuple[MatchStatus, JobRequirement, EvidenceItem | None]] = []
        for requirement in group.alternatives:
            required_tokens = _tokens(requirement.normalized_text)
            best_status = MatchStatus.NONE
            best_evidence: EvidenceItem | None = None
            for item in evidence:
                overlap = required_tokens & _tokens(item.text)
                if required_tokens and overlap == required_tokens:
                    best_status, best_evidence = MatchStatus.STRONG, item
                    break
                if overlap and best_status is MatchStatus.NONE:
                    best_status, best_evidence = MatchStatus.PARTIAL, item
            candidates.append((best_status, requirement, best_evidence))

        rank = {
            MatchStatus.NONE: 0,
            MatchStatus.UNCLEAR: 1,
            MatchStatus.PARTIAL: 2,
            MatchStatus.STRONG: 3,
        }
        best_status, best_requirement, best_evidence = max(
            candidates, key=lambda candidate: rank[candidate[0]]
        )
        return RequirementMatch(
            group_id=group.id,
            status=best_status,
            matched_requirement_ids=[best_requirement.id] if best_evidence else [],
            evidence_ids=[best_evidence.id] if best_evidence else [],
            explanation=(
                f"Matched '{best_requirement.text}' to {best_evidence.id}."
                if best_evidence
                else "No resume evidence matched any accepted alternative."
            ),
        )

    def _coverage(
        self,
        groups: list[RequirementGroup],
        matches: list[RequirementMatch],
        included: set[RequirementImportance],
    ) -> float:
        weights = {
            RequirementImportance.REQUIRED: 3.0,
            RequirementImportance.PREFERRED: 1.0,
            RequirementImportance.INFERRED: 1.0,
        }
        values = {
            MatchStatus.STRONG: 1.0,
            MatchStatus.PARTIAL: 0.5,
            MatchStatus.UNCLEAR: 0.0,
            MatchStatus.NONE: 0.0,
        }
        selected = [
            (group, match)
            for group, match in zip(groups, matches, strict=True)
            if group.importance in included
        ]
        denominator = sum(weights[group.importance] for group, _ in selected)
        if denominator == 0:
            return 0.0
        numerator = sum(
            weights[group.importance] * values[match.status] for group, match in selected
        )
        return round(100 * numerator / denominator, 2)
