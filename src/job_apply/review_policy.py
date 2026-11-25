"""Deterministic Tech God review-policy-v1 calculation."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ReviewCategory(StrEnum):
    TECHNICAL_CREDIBILITY = "technical_credibility"
    ARCHITECTURE_DEPTH = "architecture_and_engineering_depth"
    INTERVIEW_DEFENSIBILITY = "interview_defensibility"
    CAREER_OWNERSHIP = "career_progression_and_ownership"
    PRODUCTION_ENGINEERING = "production_engineering"
    TECHNOLOGY_CHRONOLOGY = "technology_chronology"
    JOB_DOMAIN_ALIGNMENT = "job_and_domain_alignment"
    BUSINESS_IMPACT = "business_impact"


CATEGORY_WEIGHTS: dict[ReviewCategory, int] = {
    ReviewCategory.TECHNICAL_CREDIBILITY: 20,
    ReviewCategory.ARCHITECTURE_DEPTH: 20,
    ReviewCategory.INTERVIEW_DEFENSIBILITY: 15,
    ReviewCategory.CAREER_OWNERSHIP: 10,
    ReviewCategory.PRODUCTION_ENGINEERING: 10,
    ReviewCategory.TECHNOLOGY_CHRONOLOGY: 10,
    ReviewCategory.JOB_DOMAIN_ALIGNMENT: 10,
    ReviewCategory.BUSINESS_IMPACT: 5,
}


class FindingSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PolicyVerdict(StrEnum):
    PASS = "pass"
    REVISE = "revise"
    NEEDS_CLARIFICATION = "needs_clarification"
    NEEDS_VERIFICATION = "needs_verification"


class CategoryAssessment(BaseModel):
    category: ReviewCategory
    applicable: bool = True
    rating: int | None = Field(default=None, ge=0, le=4)
    rationale: str


class ReviewFinding(BaseModel):
    id: str
    category: ReviewCategory
    severity: FindingSeverity
    message: str
    resolved: bool = False


class ReviewPolicyInput(BaseModel):
    assessments: list[CategoryAssessment]
    findings: list[ReviewFinding] = Field(default_factory=list)
    review_complete: bool = True
    material_questions: list[str] = Field(default_factory=list)
    missing_checks: list[str] = Field(default_factory=list)


class ReviewPolicyResult(BaseModel):
    rubric_version: str = "tech-god-v1"
    verdict: PolicyVerdict
    score: float | None
    assessed_weight: int
    unresolved_blocker_ids: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


def evaluate_review_policy(
    review: ReviewPolicyInput,
    *,
    pass_score: float = 85.0,
    minimum_assessed_weight: int = 80,
) -> ReviewPolicyResult:
    """Calculate score and routing verdict from fixed reviewer assessments."""

    by_category = {assessment.category: assessment for assessment in review.assessments}
    missing_categories = set(CATEGORY_WEIGHTS) - set(by_category)
    applicable = [assessment for assessment in by_category.values() if assessment.applicable]
    unassessed = [assessment.category for assessment in applicable if assessment.rating is None]
    assessed_weight = sum(CATEGORY_WEIGHTS[item.category] for item in applicable)
    blockers = [
        finding.id
        for finding in review.findings
        if not finding.resolved
        and finding.severity in {FindingSeverity.CRITICAL, FindingSeverity.HIGH}
    ]

    if review.material_questions:
        return ReviewPolicyResult(
            verdict=PolicyVerdict.NEEDS_CLARIFICATION,
            score=None,
            assessed_weight=assessed_weight,
            unresolved_blocker_ids=blockers,
            reasons=list(review.material_questions),
        )

    verification_reasons = [*review.missing_checks]
    if not review.review_complete:
        verification_reasons.append("The review is incomplete.")
    if missing_categories:
        verification_reasons.append(
            "Missing category assessments: "
            + ", ".join(sorted(category.value for category in missing_categories))
        )
    if unassessed:
        verification_reasons.append(
            "Applicable categories are unassessed: "
            + ", ".join(sorted(category.value for category in unassessed))
        )
    if assessed_weight < minimum_assessed_weight:
        verification_reasons.append(
            f"Assessed weight {assessed_weight} is below {minimum_assessed_weight}."
        )
    if verification_reasons:
        return ReviewPolicyResult(
            verdict=PolicyVerdict.NEEDS_VERIFICATION,
            score=None,
            assessed_weight=assessed_weight,
            unresolved_blocker_ids=blockers,
            reasons=verification_reasons,
        )

    weighted_points = sum(
        CATEGORY_WEIGHTS[item.category] * (item.rating or 0) / 4 for item in applicable
    )
    score = 100 * weighted_points / assessed_weight
    if not blockers and score >= pass_score:
        return ReviewPolicyResult(
            verdict=PolicyVerdict.PASS,
            score=score,
            assessed_weight=assessed_weight,
        )
    reasons = []
    if blockers:
        reasons.append("Unresolved critical/high findings block readiness.")
    if score < pass_score:
        reasons.append(f"Score {score:.2f} is below {pass_score:.2f}.")
    return ReviewPolicyResult(
        verdict=PolicyVerdict.REVISE,
        score=score,
        assessed_weight=assessed_weight,
        unresolved_blocker_ids=blockers,
        reasons=reasons,
    )
