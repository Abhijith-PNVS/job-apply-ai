import pytest

from job_apply.star import StarBullet, assess_star_bullet


def test_star_bullet_renders_action_context_and_result_without_forcing_metric() -> None:
    bullet = StarBullet(
        situation="a high-volume catalog workflow",
        task="seller item onboarding",
        action="Designed reusable validation services",
        result="faster and more reliable item setup",
        technologies=["Java 17", "Spring Boot"],
    )

    rendered = bullet.render()
    assessment = assess_star_bullet(rendered)

    assert rendered.startswith("Designed")
    assert "resulting in faster and more reliable item setup" in rendered
    assert assessment.passes


def test_star_bullet_requires_a_result() -> None:
    with pytest.raises(ValueError, match="requires a result"):
        StarBullet(task="catalog onboarding", action="Designed services", result="")


def test_star_assessment_flags_responsibility_only_bullet() -> None:
    assessment = assess_star_bullet("Responsible for Java services.")

    assert not assessment.passes
    assert len(assessment.issues) == 3
