"""Resume design tokens derived from the supplied ATS-safe samples."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ResumeDesign(BaseModel):
    id: str
    display_name: str
    font_family: str = "Times New Roman"
    name_size_pt: float = 25.0
    contact_size_pt: float = 9.5
    section_size_pt: float = 13.0
    role_size_pt: float = 11.0
    body_size_pt: float = 10.5
    top_margin_in: float = Field(ge=0.25, le=1.0)
    bottom_margin_in: float = Field(ge=0.25, le=1.0)
    left_margin_in: float = Field(ge=0.25, le=1.0)
    right_margin_in: float = Field(ge=0.25, le=1.0)
    line_spacing: float = Field(default=1.0, ge=0.9, le=1.3)
    bullet_left_indent_in: float = Field(default=0.14, ge=0.0, le=0.5)
    bullet_hanging_indent_in: float = Field(default=0.12, ge=0.0, le=0.5)
    section_rule: bool = True
    max_pages: int = 2


CLASSIC_ATS = ResumeDesign(
    id="classic_ats",
    display_name="Classic ATS",
    name_size_pt=25.0,
    contact_size_pt=9.5,
    section_size_pt=13.0,
    role_size_pt=11.0,
    body_size_pt=10.5,
    top_margin_in=0.45,
    bottom_margin_in=0.45,
    left_margin_in=0.5,
    right_margin_in=0.5,
    bullet_left_indent_in=0.14,
    bullet_hanging_indent_in=0.12,
)


DENSE_BACKEND = ResumeDesign(
    id="dense_backend",
    display_name="Dense Backend",
    name_size_pt=25.0,
    contact_size_pt=9.0,
    section_size_pt=11.0,
    role_size_pt=10.5,
    body_size_pt=10.0,
    top_margin_in=0.35,
    bottom_margin_in=0.45,
    left_margin_in=0.49,
    right_margin_in=0.5,
    line_spacing=1.05,
    bullet_left_indent_in=0.10,
    bullet_hanging_indent_in=0.10,
)


DESIGNS = {design.id: design for design in (CLASSIC_ATS, DENSE_BACKEND)}


def get_design(design_id: str) -> ResumeDesign:
    try:
        return DESIGNS[design_id]
    except KeyError as error:
        raise ValueError(f"Unknown resume design: {design_id}") from error
