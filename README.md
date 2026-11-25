# Job Apply AI

A LangGraph-based job application workflow focused on interview conversion.

## Compatibility spike

The first slice proves a deterministic Resume Matcher, a reusable Resume Writer →
Tech God review loop, a revision limit, LangGraph checkpointing, and a resumable
human approval interrupt bound to the exact draft hash.

The storage foundation includes durable SQLite checkpoints, idempotent Markdown
export, and distinct prepared/submitted application states.

Run the offline demonstration without using API credits:

```powershell
uv run --isolated --python 3.14 --with-editable ".[dev]" job-apply-spike --auto-approve
```

Run the focused tests:

```powershell
uv run --isolated --python 3.14 --with-editable ".[dev]" pytest
```

Live mode also requires `OPENAI_API_KEY` and `OPENAI_MODEL` in `.env`:

```powershell
uv run --isolated --python 3.14 --with-editable ".[dev]" job-apply-spike --live
```

The complete design is documented in [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md).
