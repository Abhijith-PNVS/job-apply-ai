"""STAR-derived resume bullet contracts and validation."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, model_validator


class StarBullet(BaseModel):
    situation: str = ""
    task: str
    action: str
    result: str
    technologies: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_action_and_result(self) -> "StarBullet":
        if not self.action.strip():
            raise ValueError("A STAR bullet requires a concrete action.")
        if not self.result.strip():
            raise ValueError("A STAR bullet requires a result; qualitative results are valid.")
        return self

    def render(self) -> str:
        context = ", ".join(part.strip() for part in (self.situation, self.task) if part.strip())
        action = self.action.strip().rstrip(".")
        result = self.result.strip().rstrip(".")
        bullet = f"{action}"
        if context:
            bullet += f" for {context}"
        bullet += f", resulting in {result}"
        if self.technologies:
            bullet += f" using {', '.join(self.technologies)}"
        return bullet + "."


class StarBulletAssessment(BaseModel):
    has_action: bool
    has_context: bool
    has_result: bool
    issues: list[str] = Field(default_factory=list)

    @property
    def passes(self) -> bool:
        return self.has_action and self.has_context and self.has_result


_ACTION_VERBS = {
    "architected", "automated", "built", "created", "delivered", "designed",
    "developed", "engineered", "implemented", "improved", "integrated", "led",
    "migrated", "optimized", "reduced", "scaled", "secured", "streamlined",
}
_RESULT_MARKERS = {
    "resulting", "improving", "reducing", "increasing", "enabling", "supporting",
    "accelerating", "raising", "lowering", "preventing", "achieving",
}


def assess_star_bullet(text: str) -> StarBulletAssessment:
    words = re.findall(r"[a-zA-Z]+", text.casefold())
    has_action = bool(words and words[0] in _ACTION_VERBS)
    has_result = bool(_RESULT_MARKERS & set(words)) or bool(
        re.search(r"\b\d+(?:\.\d+)?%?\b", text)
    )
    has_context = len(words) >= 8 and bool(
        re.search(r"\b(for|across|within|supporting|to)\b", text, re.I)
    )
    issues = []
    if not has_action:
        issues.append("Start with a concrete ownership/action verb.")
    if not has_context:
        issues.append("Add concise situation or task context.")
    if not has_result:
        issues.append("Add a measurable or specific qualitative result.")
    return StarBulletAssessment(
        has_action=has_action,
        has_context=has_context,
        has_result=has_result,
        issues=issues,
    )
