# Job Apply AI

A LangGraph-based job application workflow focused on interview conversion.

## Compatibility spike

The first slice proves a deterministic Resume Matcher, a reusable Resume Writer →
Tech God review loop, a revision limit, LangGraph checkpointing, and a resumable
human approval interrupt bound to the exact draft hash.

The storage foundation includes durable SQLite checkpoints, idempotent Markdown
export, and distinct prepared/submitted application states.

Implemented product foundations:

- Structured local candidate profile with JSON persistence
- TXT, Markdown, DOCX, and PDF resume import
- DOCX and PDF resume export
- Public Greenhouse and Lever discovery adapters
- Canonical job deduplication and posting-liveness checks
- Explainable job-quality and company hiring signals
- Local FastAPI dashboard and pipeline metrics
- Exact-state approval for visible Playwright autofill; no submit operation exists
- Deterministic A/B assignment and minimum-sample outcome summaries

Run the offline demonstration without using API credits:

```powershell
uv run --isolated --python 3.14 --with-editable ".[dev]" job-apply-spike --auto-approve
```

Run the focused tests:

```powershell
uv run --isolated --python 3.14 --with-editable ".[dev]" pytest
```

Run the local dashboard:

```powershell
uv run --isolated --python 3.14 --with-editable ".[dev]" job-apply-dashboard
```

Visible browser autofill requires Chromium once:

```powershell
uv run --isolated --python 3.14 --with-editable ".[dev]" playwright install chromium
```

The browser adapter fills only a previously approved exact field plan and leaves
the visible form open for human review. It has no submit method.

Live mode also requires `OPENAI_API_KEY` and `OPENAI_MODEL` in `.env`:

```powershell
uv run --isolated --python 3.14 --with-editable ".[dev]" job-apply-spike --live
```

The complete design is documented in [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md).
