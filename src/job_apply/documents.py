"""Local resume import and sample-derived ATS-safe export adapters."""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable, ListFlowable, ListItem, Paragraph, SimpleDocTemplate,
    Spacer, Table, TableStyle,
)

from job_apply.candidate import CandidateProfile
from job_apply.resume_design import CLASSIC_ATS, ResumeDesign


SUPPORTED_INPUTS = {".txt", ".md", ".docx", ".pdf"}


def read_resume(path: Path) -> str:
    resolved = path.resolve()
    suffix = resolved.suffix.casefold()
    if suffix not in SUPPORTED_INPUTS:
        raise ValueError(f"Unsupported resume format: {suffix}")
    if suffix in {".txt", ".md"}:
        return resolved.read_text(encoding="utf-8")
    if suffix == ".docx":
        document = Document(resolved)
        text = [paragraph.text for paragraph in document.paragraphs if paragraph.text]
        for table in document.tables:
            for row in table.rows:
                text.append(" | ".join(cell.text for cell in row.cells if cell.text))
        return "\n".join(text)
    reader = PdfReader(resolved)
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def profile_to_markdown(profile: CandidateProfile) -> str:
    lines = [f"# {profile.name}"]
    contact = " | ".join(filter(None, [profile.location, profile.phone, profile.email]))
    if contact:
        lines.extend(["", contact])
    if profile.summary:
        lines.extend(["", "## Professional Summary", "", profile.summary])
    if profile.skills:
        lines.extend(["", "## Technical Skills", "", ", ".join(profile.skills)])
    if profile.experiences:
        lines.extend(["", "## Professional Experience"])
        for item in profile.experiences:
            period = f"{item.start_date} – {item.end_date or 'Present'}"
            lines.extend(["", f"### {item.employer} — {period}"])
            role = item.title + (f" — {item.location}" if item.location else "")
            lines.append(f"*{role}*")
            lines.extend(f"- {bullet}" for bullet in item.rendered_bullets())
    if profile.projects:
        lines.extend(["", "## Projects"])
        for project in profile.projects:
            lines.extend(["", f"### {project.name}", project.description])
    if profile.education:
        lines.extend(["", "## Education"])
        for item in profile.education:
            credential = item.credential + (f", {item.field}" if item.field else "")
            lines.append(f"- {item.institution} — {credential}")
    return "\n".join(lines).rstrip() + "\n"


def _font(run, design: ResumeDesign, size: float, *, bold=False, italic=False) -> None:
    run.font.name = design.font_family
    run._element.rPr.rFonts.set(qn("w:eastAsia"), design.font_family)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic


def _section_heading(document: Document, title: str, design: ResumeDesign) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(5)
    paragraph.paragraph_format.space_after = Pt(2)
    paragraph.paragraph_format.keep_with_next = True
    _font(paragraph.add_run(title.upper()), design, design.section_size_pt, bold=True)
    if design.section_rule:
        borders = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "6")
        bottom.set(qn("w:space"), "1")
        bottom.set(qn("w:color"), "000000")
        borders.append(bottom)
        paragraph._p.get_or_add_pPr().append(borders)


def _right_tab_paragraph(
    document: Document, left: str, right: str, design: ResumeDesign,
    *, bold: bool = False, italic: bool = False,
) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(2 if bold else 0)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.keep_with_next = True
    usable_width = 8.5 - design.left_margin_in - design.right_margin_in
    paragraph.paragraph_format.tab_stops.add_tab_stop(
        Inches(usable_width), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.SPACES
    )
    _font(paragraph.add_run(left), design, design.role_size_pt, bold=bold, italic=italic)
    paragraph.add_run("\t")
    _font(paragraph.add_run(right), design, design.role_size_pt, bold=bold, italic=italic)


def _body_paragraph(document: Document, text: str, design: ResumeDesign) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = design.line_spacing
    _font(paragraph.add_run(text), design, design.body_size_pt)


def _bullet_paragraph(document: Document, text: str, design: ResumeDesign) -> None:
    paragraph = document.add_paragraph(style="List Bullet")
    paragraph.paragraph_format.left_indent = Inches(design.bullet_left_indent_in)
    paragraph.paragraph_format.first_line_indent = Inches(-design.bullet_hanging_indent_in)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = design.line_spacing
    _font(paragraph.add_run(text), design, design.body_size_pt)


def export_docx(
    profile: CandidateProfile, output_path: Path, design: ResumeDesign = CLASSIC_ATS,
) -> Path:
    output = output_path.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    document = Document()
    section = document.sections[0]
    section.page_width, section.page_height = Inches(8.5), Inches(11)
    section.top_margin = Inches(design.top_margin_in)
    section.bottom_margin = Inches(design.bottom_margin_in)
    section.left_margin = Inches(design.left_margin_in)
    section.right_margin = Inches(design.right_margin_in)
    normal = document.styles["Normal"]
    normal.font.name = design.font_family
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), design.font_family)
    normal.font.size = Pt(design.body_size_pt)

    name = document.add_paragraph()
    name.alignment = WD_ALIGN_PARAGRAPH.CENTER
    name.paragraph_format.space_after = Pt(0)
    _font(name.add_run(profile.name.upper()), design, design.name_size_pt)
    contact_text = " | ".join(filter(None, [profile.location, profile.phone, profile.email]))
    if contact_text:
        contact = document.add_paragraph()
        contact.alignment = WD_ALIGN_PARAGRAPH.CENTER
        contact.paragraph_format.space_after = Pt(2)
        _font(contact.add_run(contact_text), design, design.contact_size_pt)
    if profile.summary:
        _section_heading(document, "Professional Summary", design)
        _body_paragraph(document, profile.summary, design)
    if profile.skills:
        _section_heading(document, "Technical Skills", design)
        _bullet_paragraph(document, ", ".join(profile.skills), design)
    if profile.experiences:
        _section_heading(document, "Professional Experience", design)
        for item in profile.experiences:
            _right_tab_paragraph(
                document, item.employer.upper(),
                f"{item.start_date} – {item.end_date or 'Present'}", design, bold=True,
            )
            _right_tab_paragraph(document, item.title, item.location or "", design, italic=True)
            for bullet in item.rendered_bullets():
                _bullet_paragraph(document, bullet, design)
    if profile.projects:
        _section_heading(document, "Projects", design)
        for project in profile.projects:
            _right_tab_paragraph(document, project.name, "", design, bold=True)
            _body_paragraph(document, project.description, design)
    if profile.education:
        _section_heading(document, "Education", design)
        for item in profile.education:
            _right_tab_paragraph(
                document, item.institution, item.graduation_date or "", design, bold=True
            )
            credential = item.credential + (f", {item.field}" if item.field else "")
            _body_paragraph(document, credential, design)
    document.save(output)
    return output


def _pdf_styles(design: ResumeDesign) -> dict[str, ParagraphStyle]:
    return {
        "name": ParagraphStyle(
            "Name", fontName="Times-Roman", fontSize=design.name_size_pt,
            leading=design.name_size_pt + 1, alignment=TA_CENTER, spaceAfter=1,
        ),
        "contact": ParagraphStyle(
            "Contact", fontName="Times-Roman", fontSize=design.contact_size_pt,
            leading=design.contact_size_pt + 1, alignment=TA_CENTER, spaceAfter=4,
        ),
        "section": ParagraphStyle(
            "Section", fontName="Times-Bold", fontSize=design.section_size_pt,
            leading=design.section_size_pt + 1, alignment=TA_LEFT, spaceBefore=5, spaceAfter=1,
        ),
        "body": ParagraphStyle(
            "Body", fontName="Times-Roman", fontSize=design.body_size_pt,
            leading=design.body_size_pt * design.line_spacing + 1, alignment=TA_LEFT,
        ),
        "role": ParagraphStyle(
            "Role", fontName="Times-Italic", fontSize=design.role_size_pt,
            leading=design.role_size_pt + 1,
        ),
        "company": ParagraphStyle(
            "Company", fontName="Times-Bold", fontSize=design.role_size_pt,
            leading=design.role_size_pt + 1,
        ),
        "right": ParagraphStyle(
            "Right", fontName="Times-Bold", fontSize=design.role_size_pt,
            leading=design.role_size_pt + 1, alignment=TA_RIGHT,
        ),
    }


def export_pdf(
    profile: CandidateProfile, output_path: Path, design: ResumeDesign = CLASSIC_ATS,
) -> Path:
    output = output_path.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    styles = _pdf_styles(design)
    document = SimpleDocTemplate(
        str(output), pagesize=LETTER,
        topMargin=design.top_margin_in * inch,
        bottomMargin=design.bottom_margin_in * inch,
        leftMargin=design.left_margin_in * inch,
        rightMargin=design.right_margin_in * inch,
    )
    story = [Paragraph(escape(profile.name.upper()), styles["name"])]
    contact = " | ".join(filter(None, [profile.location, profile.phone, profile.email]))
    if contact:
        story.append(Paragraph(escape(contact), styles["contact"]))

    def section(title: str) -> None:
        story.append(Paragraph(escape(title.upper()), styles["section"]))
        if design.section_rule:
            story.append(HRFlowable(width="100%", thickness=0.7, color=colors.black, spaceAfter=2))

    if profile.summary:
        section("Professional Summary")
        story.append(Paragraph(escape(profile.summary), styles["body"]))
    if profile.skills:
        section("Technical Skills")
        story.append(ListFlowable(
            [ListItem(Paragraph(escape(", ".join(profile.skills)), styles["body"]))],
            bulletType="bullet", leftIndent=design.bullet_left_indent_in * inch,
        ))
    if profile.experiences:
        section("Professional Experience")
        for item in profile.experiences:
            period = f"{item.start_date} – {item.end_date or 'Present'}"
            story.append(_pdf_pair(
                item.employer.upper(), period, document.width, styles["company"], styles["right"], 3
            ))
            story.append(_pdf_pair(
                item.title, item.location or "", document.width, styles["role"], styles["role"], 0
            ))
            story.append(ListFlowable(
                [
                    ListItem(Paragraph(escape(bullet), styles["body"]))
                    for bullet in item.rendered_bullets()
                ],
                bulletType="bullet", leftIndent=design.bullet_left_indent_in * inch,
                bulletFontName="Times-Roman", bulletFontSize=design.body_size_pt, spaceAfter=1,
            ))
    if profile.projects:
        section("Projects")
        for project in profile.projects:
            story.extend([
                Paragraph(escape(project.name), styles["company"]),
                Paragraph(escape(project.description), styles["body"]),
            ])
    if profile.education:
        section("Education")
        for item in profile.education:
            story.append(_pdf_pair(
                item.institution, item.graduation_date or "", document.width,
                styles["company"], styles["right"], 2,
            ))
            credential = item.credential + (f", {item.field}" if item.field else "")
            story.append(Paragraph(escape(credential), styles["role"]))
    story.append(Spacer(1, 1))
    document.build(story)
    return output


def _pdf_pair(
    left: str, right: str, width: float, left_style: ParagraphStyle,
    right_style: ParagraphStyle, top_padding: float,
) -> Table:
    return Table(
        [[Paragraph(escape(left), left_style), Paragraph(escape(right), right_style)]],
        colWidths=[width * 0.72, width * 0.28],
        style=TableStyle([
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), top_padding),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]),
    )
