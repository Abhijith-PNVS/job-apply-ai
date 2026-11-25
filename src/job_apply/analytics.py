"""Application funnel and conservative A/B strategy analytics."""

from __future__ import annotations

import hashlib
from collections import defaultdict

from pydantic import BaseModel


class ApplicationOutcome(BaseModel):
    application_id: str
    variant: str
    submitted: bool
    interview: bool = False
    offer: bool = False


class VariantMetrics(BaseModel):
    variant: str
    submitted: int
    interviews: int
    offers: int
    interview_rate: float
    offer_rate: float


class ExperimentSummary(BaseModel):
    variants: list[VariantMetrics]
    status: str
    leader: str | None = None


def assign_variant(subject_id: str, variants: tuple[str, ...] = ("A", "B")) -> str:
    if not variants:
        raise ValueError("At least one variant is required.")
    value = int(hashlib.sha256(subject_id.encode("utf-8")).hexdigest(), 16)
    return variants[value % len(variants)]


def summarize_experiment(
    outcomes: list[ApplicationOutcome], *, minimum_submitted_per_variant: int = 15
) -> ExperimentSummary:
    grouped: dict[str, list[ApplicationOutcome]] = defaultdict(list)
    for outcome in outcomes:
        grouped[outcome.variant].append(outcome)
    metrics = []
    for variant, records in sorted(grouped.items()):
        submitted = sum(record.submitted for record in records)
        interviews = sum(record.submitted and record.interview for record in records)
        offers = sum(record.submitted and record.offer for record in records)
        metrics.append(
            VariantMetrics(
                variant=variant,
                submitted=submitted,
                interviews=interviews,
                offers=offers,
                interview_rate=interviews / submitted if submitted else 0.0,
                offer_rate=offers / submitted if submitted else 0.0,
            )
        )
    enough_data = len(metrics) >= 2 and all(
        item.submitted >= minimum_submitted_per_variant for item in metrics
    )
    leader = max(metrics, key=lambda item: item.interview_rate).variant if metrics else None
    return ExperimentSummary(
        variants=metrics,
        status="directional" if enough_data else "insufficient_data",
        leader=leader if enough_data else None,
    )
