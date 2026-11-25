from job_apply.review_policy import (
    CATEGORY_WEIGHTS,
    CategoryAssessment,
    FindingSeverity,
    PolicyVerdict,
    ReviewCategory,
    ReviewFinding,
    ReviewPolicyInput,
    evaluate_review_policy,
)


def _assessments(rating: int) -> list[CategoryAssessment]:
    return [
        CategoryAssessment(category=category, rating=rating, rationale="Fixture rating.")
        for category in CATEGORY_WEIGHTS
    ]


def test_all_level_three_ratings_score_75_and_require_revision() -> None:
    result = evaluate_review_policy(ReviewPolicyInput(assessments=_assessments(3)))

    assert result.score == 75.0
    assert result.verdict is PolicyVerdict.REVISE


def test_all_level_four_ratings_pass() -> None:
    result = evaluate_review_policy(ReviewPolicyInput(assessments=_assessments(4)))

    assert result.score == 100.0
    assert result.assessed_weight == 100
    assert result.verdict is PolicyVerdict.PASS


def test_high_finding_blocks_even_a_perfect_score() -> None:
    result = evaluate_review_policy(
        ReviewPolicyInput(
            assessments=_assessments(4),
            findings=[
                ReviewFinding(
                    id="finding-1",
                    category=ReviewCategory.TECHNICAL_CREDIBILITY,
                    severity=FindingSeverity.HIGH,
                    message="Unsupported ownership claim.",
                )
            ],
        )
    )

    assert result.score == 100.0
    assert result.verdict is PolicyVerdict.REVISE
    assert result.unresolved_blocker_ids == ["finding-1"]


def test_missing_check_returns_null_score_and_needs_verification() -> None:
    result = evaluate_review_policy(
        ReviewPolicyInput(
            assessments=_assessments(4),
            missing_checks=["Technology chronology source unavailable."],
        )
    )

    assert result.score is None
    assert result.verdict is PolicyVerdict.NEEDS_VERIFICATION


def test_material_question_takes_precedence() -> None:
    result = evaluate_review_policy(
        ReviewPolicyInput(
            assessments=_assessments(4),
            material_questions=["Did the candidate personally own deployment?"],
        )
    )

    assert result.score is None
    assert result.verdict is PolicyVerdict.NEEDS_CLARIFICATION


def test_insufficient_applicable_weight_cannot_pass() -> None:
    assessments = _assessments(4)
    for assessment in assessments:
        if assessment.category in {
            ReviewCategory.PRODUCTION_ENGINEERING,
            ReviewCategory.BUSINESS_IMPACT,
            ReviewCategory.TECHNOLOGY_CHRONOLOGY,
        }:
            assessment.applicable = False
            assessment.rating = None

    result = evaluate_review_policy(ReviewPolicyInput(assessments=assessments))

    assert result.assessed_weight == 75
    assert result.score is None
    assert result.verdict is PolicyVerdict.NEEDS_VERIFICATION
