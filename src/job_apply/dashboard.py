"""Minimal localhost dashboard and JSON API."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from job_apply.candidate import CandidateProfileRepository
from job_apply.storage import ApplicationStatus, SQLiteApplicationStore


def create_app(
    store: SQLiteApplicationStore,
    profile_repository: CandidateProfileRepository | None = None,
) -> FastAPI:
    app = FastAPI(title="Job Apply AI")

    @app.get("/", response_class=HTMLResponse)
    def home() -> str:
        return """
        <!doctype html><html><head><title>Job Apply AI</title></head>
        <body><main><h1>Job Apply AI</h1>
        <p>Local application pipeline.</p>
        <p><a href='/api/applications'>Applications JSON</a> ·
        <a href='/api/metrics'>Metrics JSON</a></p></main></body></html>
        """

    @app.get("/api/profile")
    def profile() -> dict[str, object]:
        if profile_repository is None or not profile_repository.path.exists():
            raise HTTPException(status_code=404, detail="Candidate profile not configured.")
        return profile_repository.export_dict()

    @app.get("/api/applications")
    def applications() -> list[dict[str, object]]:
        return [item.model_dump(mode="json") for item in store.list_applications()]

    @app.get("/api/metrics")
    def metrics() -> dict[str, object]:
        applications = store.list_applications()
        statuses = Counter(item.status.value for item in applications)
        submitted = store.count_submitted()
        interviewed = sum(
            item.status in {ApplicationStatus.INTERVIEW, ApplicationStatus.OFFER}
            for item in applications
        )
        return {
            "applications": len(applications),
            "submitted": submitted,
            "interviews": interviewed,
            "interview_conversion_rate": interviewed / submitted if submitted else 0.0,
            "by_status": dict(statuses),
        }

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local Job Apply AI dashboard.")
    parser.add_argument("--database", default="data/job_apply.db")
    parser.add_argument("--profile", default="data/profile.json")
    args = parser.parse_args()
    store = SQLiteApplicationStore(Path(args.database))
    profile = CandidateProfileRepository(Path(args.profile))
    uvicorn.run(create_app(store, profile), host="127.0.0.1", port=8765)


if __name__ == "__main__":
    main()
