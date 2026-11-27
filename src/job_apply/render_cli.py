"""Render a local structured candidate profile with a selected resume design."""

from __future__ import annotations

import argparse
from pathlib import Path

from job_apply.candidate import CandidateProfileRepository
from job_apply.documents import export_docx, export_pdf
from job_apply.resume_design import DESIGNS, get_design


def main() -> None:
    parser = argparse.ArgumentParser(description="Render ATS-safe DOCX and PDF resumes.")
    parser.add_argument("--profile", default="data/profile.json")
    parser.add_argument("--output", default="outputs/resume")
    parser.add_argument("--design", choices=sorted(DESIGNS), default="classic_ats")
    parser.add_argument("--docx-only", action="store_true")
    args = parser.parse_args()

    profile = CandidateProfileRepository(Path(args.profile)).load()
    design = get_design(args.design)
    output_stem = Path(args.output).resolve()
    docx_path = export_docx(profile, output_stem.with_suffix(".docx"), design)
    print(docx_path)
    if not args.docx_only:
        pdf_path = export_pdf(profile, output_stem.with_suffix(".pdf"), design)
        print(pdf_path)


if __name__ == "__main__":
    main()
