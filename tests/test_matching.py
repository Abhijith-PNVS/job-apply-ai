from job_apply.matching import DeterministicResumeMatcher, MatchStatus


def test_any_alternative_is_scored_once() -> None:
    matcher = DeterministicResumeMatcher()
    report = matcher.match(
        resume_text="Built and operated services on Microsoft Azure.",
        job_text="Required: AWS or Azure",
    )

    assert len(report.groups) == 1
    assert report.groups[0].operator == "any"
    assert report.matches[0].status is MatchStatus.STRONG
    assert report.required_coverage == 100.0
    assert report.overall_coverage == 100.0


def test_partial_match_gets_half_credit_with_evidence() -> None:
    matcher = DeterministicResumeMatcher()
    report = matcher.match(
        resume_text="Created Python automation for internal reporting.",
        job_text="Required: production Python services",
    )

    assert report.matches[0].status is MatchStatus.PARTIAL
    assert report.matches[0].evidence_ids == ["evidence-1"]
    assert report.required_coverage == 50.0


def test_required_and_preferred_coverage_are_separate() -> None:
    matcher = DeterministicResumeMatcher()
    report = matcher.match(
        resume_text="Professional Python engineer.",
        job_text="Required: Python\nPreferred: Kubernetes",
    )

    assert report.required_coverage == 100.0
    assert report.preferred_coverage == 0.0
    assert report.overall_coverage == 75.0


def test_only_required_partial_matches_request_clarification() -> None:
    matcher = DeterministicResumeMatcher()
    report = matcher.match(
        resume_text="Used Python for automation.",
        job_text="Required: production Python services\nPreferred: Kubernetes platform",
    )

    assert report.questions == [
        "Can you provide evidence for: production Python services?"
    ]
