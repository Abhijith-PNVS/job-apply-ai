from job_apply.analytics import ApplicationOutcome, assign_variant, summarize_experiment
from job_apply.discovery import ATSProvider, JobPosting
from job_apply.research import assess_job_quality, build_company_brief


def _posting(title: str, description: str, location: str = "Remote") -> JobPosting:
    return JobPosting(
        source=ATSProvider.GREENHOUSE,
        source_id=title,
        company="Acme",
        title=title,
        location=location,
        url="https://example.com/job",
        description=description,
    )


def test_job_quality_and_company_signals_are_explainable() -> None:
    weak = _posting("Engineer", "Rockstar wanted for a fast-paced environment.", "")
    assessment = assess_job_quality(weak)
    brief = build_company_brief(
        "Acme",
        [
            _posting("Platform Engineer", "Responsibilities " + "build systems " * 30),
            _posting("Data Engineer", "Requirements " + "data systems " * 30),
            _posting("Product Manager", "You will " + "lead products " * 30),
        ],
    )

    assert assessment.score < 60
    assert assessment.signals
    assert brief.open_role_count == 3
    assert len(brief.hiring_signals) == 2


def test_ab_learning_waits_for_enough_submitted_outcomes() -> None:
    outcomes = [
        ApplicationOutcome(
            application_id=f"A-{index}", variant="A", submitted=True, interview=index < 6
        )
        for index in range(15)
    ] + [
        ApplicationOutcome(
            application_id=f"B-{index}", variant="B", submitted=True, interview=index < 3
        )
        for index in range(15)
    ]

    summary = summarize_experiment(outcomes)

    assert assign_variant("application-1") == assign_variant("application-1")
    assert summary.status == "directional"
    assert summary.leader == "A"


def test_ab_learning_does_not_choose_from_small_sample() -> None:
    summary = summarize_experiment(
        [
            ApplicationOutcome(
                application_id="one", variant="A", submitted=True, interview=True
            ),
            ApplicationOutcome(application_id="two", variant="B", submitted=True),
        ]
    )

    assert summary.status == "insufficient_data"
    assert summary.leader is None
