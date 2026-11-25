from datetime import UTC, datetime
from hashlib import sha256

from job_apply.storage import (
    ApplicationStatus,
    ApprovalRecord,
    SQLiteApplicationStore,
    export_approved_markdown,
)


def test_export_is_idempotent_and_not_counted_as_submitted(tmp_path) -> None:
    store = SQLiteApplicationStore(tmp_path / "state.db")
    content = "# Tailored Resume\n"
    draft_hash = sha256(content.encode()).hexdigest()
    approval = ApprovalRecord(
        draft_hash=draft_hash,
        approved=True,
        approved_at=datetime.now(UTC),
    )

    first = export_approved_markdown(
        output_directory=tmp_path / "output",
        application_operation_id="prepare-1",
        artifact_operation_id="artifact-1",
        job_key="python-engineer",
        content=content,
        draft_hash=draft_hash,
        approval=approval,
        store=store,
    )
    second = export_approved_markdown(
        output_directory=tmp_path / "output",
        application_operation_id="prepare-1",
        artifact_operation_id="artifact-1",
        job_key="python-engineer",
        content=content,
        draft_hash=draft_hash,
        approval=approval,
        store=store,
    )

    assert first.id == second.id
    assert first.status is ApplicationStatus.PREPARED
    assert store.count_artifacts() == 1
    assert store.count_submitted() == 0
    assert (tmp_path / "output" / f"python-engineer-{draft_hash[:12]}.md").exists()
    store.close()


def test_submission_confirmation_changes_metric_denominator(tmp_path) -> None:
    store = SQLiteApplicationStore(tmp_path / "state.db")
    content = "resume"
    draft_hash = sha256(content.encode()).hexdigest()
    application = export_approved_markdown(
        output_directory=tmp_path / "output",
        application_operation_id="prepare-2",
        artifact_operation_id="artifact-2",
        job_key="platform-role",
        content=content,
        draft_hash=draft_hash,
        approval=ApprovalRecord(
            draft_hash=draft_hash,
            approved=True,
            approved_at=datetime.now(UTC),
        ),
        store=store,
    )

    submitted = store.confirm_submitted(application.id)

    assert submitted.status is ApplicationStatus.SUBMITTED
    assert submitted.submitted_at is not None
    assert store.count_submitted() == 1
    store.close()


def test_export_rejects_stale_approval(tmp_path) -> None:
    store = SQLiteApplicationStore(tmp_path / "state.db")
    content = "current draft"
    draft_hash = sha256(content.encode()).hexdigest()

    try:
        export_approved_markdown(
            output_directory=tmp_path / "output",
            application_operation_id="prepare-3",
            artifact_operation_id="artifact-3",
            job_key="role",
            content=content,
            draft_hash=draft_hash,
            approval=ApprovalRecord(
                draft_hash="stale",
                approved=True,
                approved_at=datetime.now(UTC),
            ),
            store=store,
        )
    except ValueError as error:
        assert "not valid" in str(error)
    else:
        raise AssertionError("Stale approval must not export a draft.")
    store.close()
