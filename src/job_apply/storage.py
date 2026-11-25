"""Local idempotent artifact and application persistence."""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel


class ApplicationStatus(StrEnum):
    PREPARED = "prepared"
    SUBMITTED = "submitted"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    OFFER = "offer"


class ApprovalRecord(BaseModel):
    draft_hash: str
    approved: bool
    approved_at: datetime


class PreparedApplication(BaseModel):
    id: str
    operation_id: str
    job_key: str
    draft_hash: str
    artifact_path: str
    status: ApplicationStatus
    prepared_at: datetime
    submitted_at: datetime | None = None


class SQLiteApplicationStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path.resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._setup()

    def close(self) -> None:
        self._connection.close()

    def _setup(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id TEXT PRIMARY KEY,
                operation_id TEXT NOT NULL UNIQUE,
                job_key TEXT NOT NULL,
                draft_hash TEXT NOT NULL,
                artifact_path TEXT NOT NULL,
                status TEXT NOT NULL,
                prepared_at TEXT NOT NULL,
                submitted_at TEXT
            );
            CREATE TABLE IF NOT EXISTS artifacts (
                operation_id TEXT PRIMARY KEY,
                application_id TEXT NOT NULL,
                draft_hash TEXT NOT NULL,
                path TEXT NOT NULL UNIQUE,
                content_hash TEXT NOT NULL,
                FOREIGN KEY(application_id) REFERENCES applications(id)
            );
            CREATE TABLE IF NOT EXISTS application_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY(application_id) REFERENCES applications(id)
            );
            """
        )
        self._connection.commit()

    def prepare_application(
        self,
        *,
        operation_id: str,
        job_key: str,
        draft_hash: str,
        artifact_path: Path,
    ) -> PreparedApplication:
        existing = self._connection.execute(
            "SELECT * FROM applications WHERE operation_id = ?", (operation_id,)
        ).fetchone()
        resolved_path = str(artifact_path.resolve())
        if existing:
            record = self._row_to_application(existing)
            expected = (job_key, draft_hash, resolved_path)
            actual = (record.job_key, record.draft_hash, record.artifact_path)
            if actual != expected:
                raise ValueError("Operation ID was reused with different application data.")
            return record

        application_id = hashlib.sha256(operation_id.encode("utf-8")).hexdigest()[:32]
        prepared_at = datetime.now(UTC)
        self._connection.execute(
            """
            INSERT INTO applications
                (id, operation_id, job_key, draft_hash, artifact_path, status, prepared_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                application_id,
                operation_id,
                job_key,
                draft_hash,
                resolved_path,
                ApplicationStatus.PREPARED.value,
                prepared_at.isoformat(),
            ),
        )
        self._connection.commit()
        return self.get_application(application_id)

    def record_artifact(
        self,
        *,
        operation_id: str,
        application_id: str,
        draft_hash: str,
        path: Path,
        content_hash: str,
    ) -> None:
        existing = self._connection.execute(
            "SELECT * FROM artifacts WHERE operation_id = ?", (operation_id,)
        ).fetchone()
        payload = (application_id, draft_hash, str(path.resolve()), content_hash)
        if existing:
            actual = (
                existing["application_id"],
                existing["draft_hash"],
                existing["path"],
                existing["content_hash"],
            )
            if actual != payload:
                raise ValueError("Operation ID was reused with different artifact data.")
            return
        self._connection.execute(
            """
            INSERT INTO artifacts
                (operation_id, application_id, draft_hash, path, content_hash)
            VALUES (?, ?, ?, ?, ?)
            """,
            (operation_id, *payload),
        )
        self._connection.commit()

    def confirm_submitted(
        self, application_id: str, *, submitted_at: datetime | None = None
    ) -> PreparedApplication:
        submitted_at = submitted_at or datetime.now(UTC)
        cursor = self._connection.execute(
            """
            UPDATE applications
            SET status = ?, submitted_at = ?
            WHERE id = ?
            """,
            (ApplicationStatus.SUBMITTED.value, submitted_at.isoformat(), application_id),
        )
        if cursor.rowcount == 0:
            raise KeyError(application_id)
        self._connection.commit()
        return self.get_application(application_id)

    def get_application(self, application_id: str) -> PreparedApplication:
        row = self._connection.execute(
            "SELECT * FROM applications WHERE id = ?", (application_id,)
        ).fetchone()
        if not row:
            raise KeyError(application_id)
        return self._row_to_application(row)

    def count_submitted(self) -> int:
        row = self._connection.execute(
            "SELECT COUNT(*) AS count FROM applications WHERE submitted_at IS NOT NULL"
        ).fetchone()
        return int(row["count"])

    def count_artifacts(self) -> int:
        row = self._connection.execute(
            "SELECT COUNT(*) AS count FROM artifacts"
        ).fetchone()
        return int(row["count"])

    def list_applications(self) -> list[PreparedApplication]:
        rows = self._connection.execute(
            "SELECT * FROM applications ORDER BY prepared_at DESC"
        ).fetchall()
        return [self._row_to_application(row) for row in rows]

    def update_status(
        self, application_id: str, status: ApplicationStatus
    ) -> PreparedApplication:
        cursor = self._connection.execute(
            "UPDATE applications SET status = ? WHERE id = ?",
            (status.value, application_id),
        )
        if cursor.rowcount == 0:
            raise KeyError(application_id)
        self._connection.commit()
        return self.get_application(application_id)

    def record_event(
        self,
        application_id: str,
        event_type: str,
        *,
        occurred_at: datetime | None = None,
        metadata: str = "{}",
    ) -> None:
        self.get_application(application_id)
        self._connection.execute(
            """
            INSERT INTO application_events
                (application_id, event_type, occurred_at, metadata)
            VALUES (?, ?, ?, ?)
            """,
            (
                application_id,
                event_type,
                (occurred_at or datetime.now(UTC)).isoformat(),
                metadata,
            ),
        )
        self._connection.commit()

    def list_events(self, application_id: str) -> list[dict[str, str]]:
        rows = self._connection.execute(
            """
            SELECT event_type, occurred_at, metadata
            FROM application_events
            WHERE application_id = ?
            ORDER BY occurred_at
            """,
            (application_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _row_to_application(row: sqlite3.Row) -> PreparedApplication:
        return PreparedApplication(
            id=row["id"],
            operation_id=row["operation_id"],
            job_key=row["job_key"],
            draft_hash=row["draft_hash"],
            artifact_path=row["artifact_path"],
            status=ApplicationStatus(row["status"]),
            prepared_at=datetime.fromisoformat(row["prepared_at"]),
            submitted_at=(
                datetime.fromisoformat(row["submitted_at"])
                if row["submitted_at"]
                else None
            ),
        )


def export_approved_markdown(
    *,
    output_directory: Path,
    application_operation_id: str,
    artifact_operation_id: str,
    job_key: str,
    content: str,
    draft_hash: str,
    approval: ApprovalRecord,
    store: SQLiteApplicationStore,
) -> PreparedApplication:
    """Write one approved artifact and prepare one replay-safe application record."""

    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    if content_hash != draft_hash:
        raise ValueError("Draft hash does not match the content being exported.")
    if not approval.approved or approval.draft_hash != draft_hash:
        raise ValueError("Approval is not valid for this draft.")

    root = output_directory.resolve()
    root.mkdir(parents=True, exist_ok=True)
    safe_job = re_sub_non_filename(job_key)
    target = (root / f"{safe_job}-{draft_hash[:12]}.md").resolve()
    if root not in target.parents:
        raise ValueError("Export target escaped the configured output directory.")

    application = store.prepare_application(
        operation_id=application_operation_id,
        job_key=job_key,
        draft_hash=draft_hash,
        artifact_path=target,
    )
    if target.exists():
        existing_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        if existing_hash != content_hash:
            raise ValueError("Existing artifact content conflicts with this operation.")
    else:
        temporary = target.with_suffix(".tmp")
        temporary.write_bytes(content.encode("utf-8"))
        temporary.replace(target)
    store.record_artifact(
        operation_id=artifact_operation_id,
        application_id=application.id,
        draft_hash=draft_hash,
        path=target,
        content_hash=content_hash,
    )
    return application


def re_sub_non_filename(value: str) -> str:
    safe = "".join(character if character.isalnum() else "-" for character in value)
    return "-".join(part for part in safe.split("-") if part) or "job"
