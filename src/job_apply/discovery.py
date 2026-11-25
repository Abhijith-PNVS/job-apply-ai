"""Public ATS discovery, deduplication, and liveness checks."""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from urllib.parse import urlsplit, urlunsplit

import httpx
from pydantic import BaseModel, Field


class ATSProvider(StrEnum):
    GREENHOUSE = "greenhouse"
    LEVER = "lever"


class JobSource(BaseModel):
    provider: ATSProvider
    board_token: str
    company: str


class JobPosting(BaseModel):
    source: ATSProvider
    source_id: str
    company: str
    title: str
    location: str = ""
    url: str
    description: str = ""
    posted_at: datetime | None = None
    source_ids: list[str] = Field(default_factory=list)

    def canonical_key(self) -> str:
        parts = [self.company, self.title, self.location]
        return "|".join(_canonical_text(part) for part in parts)


def _canonical_text(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def canonical_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme.casefold(), parts.netloc.casefold(), parts.path.rstrip("/"), "", ""))


class PublicATSClient:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(timeout=20, follow_redirects=True)

    def fetch(self, source: JobSource) -> list[JobPosting]:
        if source.provider is ATSProvider.GREENHOUSE:
            return self._greenhouse(source)
        return self._lever(source)

    def _greenhouse(self, source: JobSource) -> list[JobPosting]:
        response = self.client.get(
            f"https://boards-api.greenhouse.io/v1/boards/{source.board_token}/jobs",
            params={"content": "true"},
        )
        response.raise_for_status()
        postings = []
        for item in response.json().get("jobs", []):
            postings.append(
                JobPosting(
                    source=ATSProvider.GREENHOUSE,
                    source_id=str(item["id"]),
                    company=source.company,
                    title=item["title"],
                    location=item.get("location", {}).get("name", ""),
                    url=item["absolute_url"],
                    description=item.get("content", ""),
                    source_ids=[f"greenhouse:{item['id']}"],
                )
            )
        return postings

    def _lever(self, source: JobSource) -> list[JobPosting]:
        response = self.client.get(
            f"https://api.lever.co/v0/postings/{source.board_token}",
            params={"mode": "json"},
        )
        response.raise_for_status()
        postings = []
        for item in response.json():
            categories = item.get("categories", {})
            postings.append(
                JobPosting(
                    source=ATSProvider.LEVER,
                    source_id=str(item["id"]),
                    company=source.company,
                    title=item["text"],
                    location=categories.get("location", ""),
                    url=item.get("hostedUrl") or item.get("applyUrl", ""),
                    description=item.get("descriptionPlain", ""),
                    source_ids=[f"lever:{item['id']}"],
                )
            )
        return postings


def deduplicate_postings(postings: list[JobPosting]) -> list[JobPosting]:
    by_key: dict[str, JobPosting] = {}
    by_url: dict[str, str] = {}
    for posting in postings:
        key = posting.canonical_key()
        normalized_url = canonical_url(posting.url)
        existing_key = by_url.get(normalized_url, key)
        if existing_key in by_key:
            existing = by_key[existing_key]
            existing.source_ids = sorted(set(existing.source_ids + posting.source_ids))
            if len(posting.description) > len(existing.description):
                existing.description = posting.description
            by_url[normalized_url] = existing_key
            continue
        by_key[key] = posting.model_copy(deep=True)
        by_url[normalized_url] = key
    return list(by_key.values())


def is_posting_live(url: str, client: httpx.Client) -> bool:
    response = client.head(url, follow_redirects=True)
    if response.status_code in {405, 501}:
        response = client.get(url, follow_redirects=True)
    return 200 <= response.status_code < 400


def discover_jobs(sources: list[JobSource], ats: PublicATSClient) -> list[JobPosting]:
    postings = [posting for source in sources for posting in ats.fetch(source)]
    return deduplicate_postings(postings)
