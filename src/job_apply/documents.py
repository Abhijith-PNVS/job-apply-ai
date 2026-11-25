"""Local resume import and export adapters."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from pypdf import PdfReader
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen.canvas import Canvas

from job_apply.candidate import CandidateProfile


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
        return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text)
    reader = PdfReader(resolved)
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def profile_to_markdown(profile: CandidateProfile) -> str:
    lines = [f"# {profile.name}"]
    contact = " | ".join(filter(None, [profile.email, profile.phone, profile.location]))
    if contact:
        lines.extend(["", contact])
    if profile.headline:
        lines.extend(["", f"## {profile.headline}"])
    if profile.summary:
        lines.extend(["", profile.summary])
    if profile.skills:
        lines.extend(["", "## Skills", "", ", ".join(profile.skills)])
    if profile.experiences:
        lines.extend(["", "## Experience"])
        for item in profile.experiences:
            period = f"{item.start_date} – {item.end_date or 'Present'}"
            lines.extend(["", f"### {item.title} — {item.employer}", period])
            lines.extend(f"- {bullet}" for bullet in item.bullets)
    if profile.projects:
        lines.extend(["", "## Projects"])
        for project in profile.projects:
            lines.extend(["", f"### {project.name}", project.description])
    return "\n".join(lines).rstrip() + "\n"


def export_docx(profile: CandidateProfile, output_path: Path) -> Path:
    output = output_path.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    document = Document()
    document.add_heading(profile.name, 0)
    contact = " | ".join(filter(None, [profile.email, profile.phone, profile.location]))
    if contact:
        document.add_paragraph(contact)
    if profile.summary:
        document.add_heading("Summary", level=1)
        document.add_paragraph(profile.summary)
    if profile.skills:
        document.add_heading("Skills", level=1)
        document.add_paragraph(", ".join(profile.skills))
    if profile.experiences:
        document.add_heading("Experience", level=1)
        for item in profile.experiences:
            document.add_heading(f"{item.title} — {item.employer}", level=2)
            document.add_paragraph(f"{item.start_date} – {item.end_date or 'Present'}")
            for bullet in item.bullets:
                document.add_paragraph(bullet, style="List Bullet")
    document.save(output)
    return output


def export_pdf(profile: CandidateProfile, output_path: Path) -> Path:
    output = output_path.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas = Canvas(str(output), pagesize=LETTER)
    width, height = LETTER
    text = canvas.beginText(54, height - 54)
    text.setFont("Helvetica", 10)
    for line in profile_to_markdown(profile).splitlines():
        if text.getY() < 54:
            canvas.drawText(text)
            canvas.showPage()
            text = canvas.beginText(54, height - 54)
            text.setFont("Helvetica", 10)
        text.textLine(line[:110])
    canvas.drawText(text)
    canvas.save()
    return output
