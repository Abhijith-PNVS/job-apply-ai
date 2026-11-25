from job_apply.candidate import CandidateProfile, CandidateProfileRepository, Experience
from job_apply.documents import export_docx, export_pdf, profile_to_markdown, read_resume


def _profile() -> CandidateProfile:
    return CandidateProfile(
        name="Ada Candidate",
        email="ada@example.com",
        headline="Python Engineer",
        skills=["Python", "Azure"],
        experiences=[
            Experience(
                employer="Example Corp",
                title="Engineer",
                start_date="2022",
                bullets=["Built production Python services."],
            )
        ],
    )


def test_profile_repository_round_trip(tmp_path) -> None:
    repository = CandidateProfileRepository(tmp_path / "profile.json")
    repository.save(_profile())

    loaded = repository.load()

    assert loaded.name == "Ada Candidate"
    assert "Built production Python services." in loaded.evidence_lines()


def test_docx_and_pdf_export_are_readable(tmp_path) -> None:
    profile = _profile()
    docx_path = export_docx(profile, tmp_path / "resume.docx")
    pdf_path = export_pdf(profile, tmp_path / "resume.pdf")

    assert "Ada Candidate" in read_resume(docx_path)
    assert "Python Engineer" in read_resume(pdf_path)
    assert "Example Corp" in profile_to_markdown(profile)
