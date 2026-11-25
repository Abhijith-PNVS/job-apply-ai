import httpx

from job_apply.discovery import (
    ATSProvider,
    JobPosting,
    JobSource,
    PublicATSClient,
    deduplicate_postings,
    is_posting_live,
)


def test_greenhouse_and_lever_public_sources_are_parsed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "greenhouse" in request.url.host:
            return httpx.Response(
                200,
                json={
                    "jobs": [
                        {
                            "id": 1,
                            "title": "Platform Engineer",
                            "location": {"name": "Remote"},
                            "absolute_url": "https://example.com/jobs/1",
                            "content": "Required: Python",
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json=[
                {
                    "id": "abc",
                    "text": "Platform Engineer",
                    "categories": {"location": "Remote"},
                    "hostedUrl": "https://example.com/jobs/1?source=lever",
                    "descriptionPlain": "Required: Python and Azure",
                }
            ],
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    ats = PublicATSClient(client)
    greenhouse = ats.fetch(
        JobSource(provider=ATSProvider.GREENHOUSE, board_token="acme", company="Acme")
    )
    lever = ats.fetch(
        JobSource(provider=ATSProvider.LEVER, board_token="acme", company="Acme")
    )

    assert greenhouse[0].source_id == "1"
    assert lever[0].source_id == "abc"


def test_dedup_merges_sources_and_keeps_richer_description() -> None:
    postings = [
        JobPosting(
            source=ATSProvider.GREENHOUSE,
            source_id="1",
            source_ids=["greenhouse:1"],
            company="Acme",
            title="Platform Engineer",
            location="Remote",
            url="https://example.com/jobs/1",
            description="Python",
        ),
        JobPosting(
            source=ATSProvider.LEVER,
            source_id="abc",
            source_ids=["lever:abc"],
            company="ACME",
            title="Platform Engineer",
            location="Remote",
            url="https://example.com/jobs/1?source=lever",
            description="Python and Azure production services",
        ),
    ]

    result = deduplicate_postings(postings)

    assert len(result) == 1
    assert result[0].source_ids == ["greenhouse:1", "lever:abc"]
    assert result[0].description == "Python and Azure production services"


def test_liveness_falls_back_to_get_when_head_is_not_supported() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(405 if request.method == "HEAD" else 200)

    client = httpx.Client(transport=httpx.MockTransport(handler))

    assert is_posting_live("https://example.com/job", client)
