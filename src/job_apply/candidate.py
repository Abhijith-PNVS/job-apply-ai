"""Structured candidate profile and local JSON persistence."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from job_apply.star import StarBullet


class Experience(BaseModel):
    employer: str
    title: str
    start_date: str
    end_date: str | None = None
    location: str | None = None
    bullets: list[str] = Field(default_factory=list)
    star_bullets: list[StarBullet] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)

    def rendered_bullets(self) -> list[str]:
        return [*self.bullets, *(bullet.render() for bullet in self.star_bullets)]


class Project(BaseModel):
    name: str
    description: str
    technologies: list[str] = Field(default_factory=list)
    url: str | None = None


class Education(BaseModel):
    institution: str
    credential: str
    field: str | None = None
    graduation_date: str | None = None


class Certification(BaseModel):
    name: str
    issuer: str
    issued_date: str | None = None
    credential_id: str | None = None
    url: str | None = None


class CandidateProfile(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    headline: str | None = None
    summary: str | None = None
    target_titles: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    experiences: list[Experience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    voice_samples: list[str] = Field(default_factory=list)
    avoid_claims: list[str] = Field(default_factory=list)

    def evidence_lines(self) -> list[str]:
        lines = [*self.skills]
        for experience in self.experiences:
            lines.extend(experience.rendered_bullets())
            lines.extend(experience.technologies)
        for project in self.projects:
            lines.append(project.description)
            lines.extend(project.technologies)
        return [line for line in lines if line.strip()]


class CandidateProfileRepository:
    def __init__(self, path: Path) -> None:
        self.path = path.resolve()

    def save(self, profile: CandidateProfile) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def load(self) -> CandidateProfile:
        return CandidateProfile.model_validate_json(self.path.read_text(encoding="utf-8"))

    def export_dict(self) -> dict[str, object]:
        return json.loads(self.path.read_text(encoding="utf-8"))
