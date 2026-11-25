"""Approval-bound visible browser autofill; submission is intentionally absent."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field


class FieldKind(StrEnum):
    TEXT = "text"
    SELECT = "select"
    FILE = "file"


class FormField(BaseModel):
    selector: str
    value: str
    kind: FieldKind = FieldKind.TEXT


class FillPlan(BaseModel):
    url: str
    draft_hash: str
    fields: list[FormField] = Field(default_factory=list)

    def state_hash(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class FillApproval(BaseModel):
    state_hash: str
    expires_at: datetime
    signature: str


class BrowserDriver(Protocol):
    def open(self, url: str) -> None: ...
    def fill_text(self, selector: str, value: str) -> None: ...
    def select(self, selector: str, value: str) -> None: ...
    def upload(self, selector: str, path: Path) -> None: ...
    def screenshot(self) -> bytes: ...


class FillApprovalAuthority:
    def __init__(self, secret: bytes) -> None:
        if len(secret) < 16:
            raise ValueError("Approval secret must contain at least 16 bytes.")
        self.secret = secret

    def issue(self, plan: FillPlan, *, ttl_minutes: int = 15) -> FillApproval:
        expires_at = datetime.now(UTC) + timedelta(minutes=ttl_minutes)
        state_hash = plan.state_hash()
        signature = self._sign(state_hash, expires_at)
        return FillApproval(
            state_hash=state_hash,
            expires_at=expires_at,
            signature=signature,
        )

    def verify(self, plan: FillPlan, approval: FillApproval) -> None:
        now = datetime.now(UTC)
        if approval.expires_at <= now:
            raise ValueError("Fill approval has expired.")
        if approval.state_hash != plan.state_hash():
            raise ValueError("Fill plan changed after approval.")
        expected = self._sign(approval.state_hash, approval.expires_at)
        if not hmac.compare_digest(expected, approval.signature):
            raise ValueError("Fill approval signature is invalid.")

    def _sign(self, state_hash: str, expires_at: datetime) -> str:
        message = f"{state_hash}|{expires_at.isoformat()}".encode("utf-8")
        return hmac.new(self.secret, message, hashlib.sha256).hexdigest()


class BrowserAutofillService:
    def __init__(self, driver: BrowserDriver, authority: FillApprovalAuthority) -> None:
        self.driver = driver
        self.authority = authority

    def fill(self, plan: FillPlan, approval: FillApproval) -> bytes:
        self.authority.verify(plan, approval)
        self.driver.open(plan.url)
        for field in plan.fields:
            if field.kind is FieldKind.FILE:
                self.driver.upload(field.selector, Path(field.value).resolve())
            elif field.kind is FieldKind.SELECT:
                self.driver.select(field.selector, field.value)
            else:
                self.driver.fill_text(field.selector, field.value)
        return self.driver.screenshot()


class PlaywrightVisibleDriver:
    """Synchronous visible Chromium driver. It never exposes a submit operation."""

    def __init__(self) -> None:
        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=False)
        self._page = self._browser.new_page()

    def open(self, url: str) -> None:
        self._page.goto(url)

    def fill_text(self, selector: str, value: str) -> None:
        self._page.locator(selector).fill(value)

    def select(self, selector: str, value: str) -> None:
        self._page.locator(selector).select_option(value)

    def upload(self, selector: str, path: Path) -> None:
        self._page.locator(selector).set_input_files(str(path))

    def screenshot(self) -> bytes:
        return self._page.screenshot(full_page=True)

    def close(self) -> None:
        self._browser.close()
        self._playwright.stop()
