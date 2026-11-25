from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from fastapi.testclient import TestClient

from job_apply.browser import (
    BrowserAutofillService,
    FieldKind,
    FillApprovalAuthority,
    FillPlan,
    FormField,
)
from job_apply.dashboard import create_app
from job_apply.storage import ApprovalRecord, SQLiteApplicationStore, export_approved_markdown


class FakeBrowser:
    def __init__(self) -> None:
        self.actions: list[tuple[str, str, str]] = []

    def open(self, url: str) -> None:
        self.actions.append(("open", url, ""))

    def fill_text(self, selector: str, value: str) -> None:
        self.actions.append(("text", selector, value))

    def select(self, selector: str, value: str) -> None:
        self.actions.append(("select", selector, value))

    def upload(self, selector: str, path: Path) -> None:
        self.actions.append(("file", selector, str(path)))

    def screenshot(self) -> bytes:
        return b"screenshot"


def test_browser_fill_requires_approval_for_exact_plan(tmp_path) -> None:
    browser = FakeBrowser()
    authority = FillApprovalAuthority(b"0123456789abcdef0123456789abcdef")
    service = BrowserAutofillService(browser, authority)
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"pdf")
    plan = FillPlan(
        url="https://jobs.example.com/apply",
        draft_hash="draft-1",
        fields=[
            FormField(selector="#name", value="Ada"),
            FormField(selector="#country", value="US", kind=FieldKind.SELECT),
            FormField(selector="#resume", value=str(resume), kind=FieldKind.FILE),
        ],
    )
    approval = authority.issue(plan)

    screenshot = service.fill(plan, approval)

    assert screenshot == b"screenshot"
    assert [action[0] for action in browser.actions] == ["open", "text", "select", "file"]

    changed = plan.model_copy(deep=True)
    changed.fields[0].value = "Different"
    try:
        service.fill(changed, approval)
    except ValueError as error:
        assert "changed" in str(error)
    else:
        raise AssertionError("A changed fill plan must invalidate approval.")


def test_dashboard_reports_only_confirmed_submissions(tmp_path) -> None:
    store = SQLiteApplicationStore(tmp_path / "state.db")
    content = "resume"
    draft_hash = sha256(content.encode()).hexdigest()
    application = export_approved_markdown(
        output_directory=tmp_path / "output",
        application_operation_id="prepare-dashboard",
        artifact_operation_id="artifact-dashboard",
        job_key="role",
        content=content,
        draft_hash=draft_hash,
        approval=ApprovalRecord(
            draft_hash=draft_hash,
            approved=True,
            approved_at=datetime.now(UTC),
        ),
        store=store,
    )
    client = TestClient(create_app(store))

    before = client.get("/api/metrics").json()
    store.confirm_submitted(application.id)
    after = client.get("/api/metrics").json()

    assert before["submitted"] == 0
    assert after["submitted"] == 1
    assert client.get("/").status_code == 200
    store.close()
