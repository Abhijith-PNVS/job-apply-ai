from docx import Document
from pypdf import PdfReader

from job_apply.candidate import (
    CandidateProfile,
    CandidateProfileRepository,
    Education,
    Experience,
)
from job_apply.documents import export_docx, export_pdf, profile_to_markdown, read_resume
from job_apply.resume_design import CLASSIC_ATS, DENSE_BACKEND
from job_apply.star import StarBullet


def _profile() -> CandidateProfile:
    return CandidateProfile(
        name="Ada Candidate",
        email="ada@example.com",
        headline="Python Engineer",
        summary="Backend engineer building reliable distributed services.",
        skills=["Python", "Azure"],
        experiences=[
            Experience(
                employer="Example Corp",
                title="Engineer",
                start_date="2022",
                bullets=["Built production Python services."],
                star_bullets=[
                    StarBullet(
                        situation="a distributed service workflow",
                        task="failure recovery",
                        action="Implemented idempotent retries",
                        result="safer recovery from partial failures",
                    )
                ],
            )
        ],
        education=[
            Education(
                institution="Example University",
                credential="M.S.",
                field="Computer Science",
                graduation_date="2022",
            )
        ],
    )


def test_profile_repository_round_trip(tmp_path) -> None:
    repository = CandidateProfileRepository(tmp_path / "profile.json")
    repository.save(_profile())

    loaded = repository.load()

    assert loaded.name == "Ada Candidate"
    assert "Built production Python services." in loaded.evidence_lines()
    assert any("safer recovery" in item for item in loaded.evidence_lines())


def test_docx_and_pdf_export_are_readable(tmp_path) -> None:
    profile = _profile()
    docx_path = export_docx(profile, tmp_path / "resume.docx")
    pdf_path = export_pdf(profile, tmp_path / "resume.pdf")

    assert "ADA CANDIDATE" in read_resume(docx_path)
    assert "Engineer" in read_resume(pdf_path)
    assert "Example Corp" in profile_to_markdown(profile)


def test_sample_derived_docx_design_tokens_are_applied(tmp_path) -> None:
    path = export_docx(_profile(), tmp_path / "classic.docx", CLASSIC_ATS)
    document = Document(path)
    section = document.sections[0]

    assert round(section.left_margin.inches, 2) == 0.5
    assert round(section.top_margin.inches, 2) == 0.45
    assert document.paragraphs[0].runs[0].font.name == "Times New Roman"
    assert document.paragraphs[0].runs[0].font.size.pt == 25.0
    assert "PROFESSIONAL SUMMARY" in [p.text for p in document.paragraphs]


def test_both_designs_generate_ats_readable_pdf_within_two_pages(tmp_path) -> None:
    for design in (CLASSIC_ATS, DENSE_BACKEND):
        path = export_pdf(_profile(), tmp_path / f"{design.id}.pdf", design)
        reader = PdfReader(path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)

        assert len(reader.pages) <= design.max_pages
        assert "ADA CANDIDATE" in text
        assert "Example Corp".upper() in text.upper()
