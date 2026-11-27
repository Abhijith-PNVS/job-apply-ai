# Resume Design System

## Source evidence

This design system was derived from two local sample resumes supplied on 2026-11-25. The private source files remain outside Git.

| Attribute | Java Backend DOCX | Applied AI PDF |
|---|---:|---:|
| Page size | US Letter, 8.5 × 11 in | US Letter, 612 × 792 pt |
| Pages | Two sections/pages | Two pages |
| Main font | Times New Roman | Embedded EB Garamond |
| Name | 25 pt | 25 pt |
| Contact | 9 pt | 9.5 pt |
| Section heading | 11 pt bold uppercase | 13 pt bold uppercase with rule |
| Body | 10 pt | 10.5 pt |
| Role/company | 10–10.5 pt | 11 pt bold/italic |
| Side margins | Approximately 0.49–0.50 in | Approximately 0.50 in visually |
| Layout | Dense single column | Single column with stronger hierarchy |

The Applied AI sample has the clearer hierarchy and spacing. The Java sample fits more technical content. EB Garamond is embedded in the PDF but is not installed on the current Windows machine; editable output therefore uses Times New Roman for predictable DOCX/PDF rendering.

## Available designs

### `classic_ats` — default

- Times New Roman.
- 25 pt centered name and 9.5 pt centered contact line.
- 13 pt uppercase ruled section headings.
- 10.5 pt body and 11 pt company/role lines.
- 0.5 in side margins and approximately 0.45 in vertical margins.
- Best for senior, AI, architecture, and leadership-oriented resumes.

### `dense_backend`

- Times New Roman.
- 25 pt name and 9 pt contact line.
- 11 pt uppercase ruled section headings.
- 10 pt body and 10.5 pt company/role lines.
- Approximately 0.49 in side margins and 0.35 in top margin.
- Best when technical skills, projects, or detailed backend work require more space.

Both formats remain:

- US Letter and no more than two pages.
- Single-column in semantic reading order.
- Free of icons, charts, photos, rating bars, headers, and footers.
- Built from normal text, paragraphs, bullets, tabs, and minimal alignment tables.
- Readable through PDF text extraction and editable in Word.

## Section order

Default order:

1. Name and contact.
2. Professional Summary.
3. Technical Skills.
4. Professional Experience.
5. Projects when they materially strengthen the target role.
6. Education.
7. Certifications when relevant.

The editor may move Projects before Experience only for early-career profiles where projects are stronger evidence than employment.

## Experience header

- Employer is bold and left aligned.
- Dates are bold and right aligned on the same line.
- Role is italic and left aligned.
- Location is italic and right aligned on the same line.
- The first bullet follows immediately; subsequent roles have compact separation.

## STAR-derived bullet rule

Every new or rewritten role bullet uses a compressed STAR structure suitable for a resume:

```text
Action + situation/task context + result (+ relevant technology)
```

Rules:

1. Start with a concrete ownership/action verb.
2. Include enough situation or task context to explain why the work mattered.
3. State the candidate's specific action, implementation, or decision.
4. End with a measurable result when supported.
5. Use a specific qualitative result when no verified metric exists.
6. Never invent metrics, scale, ownership, technology, or outcomes.
7. Ask the candidate when a result is important but unknown.
8. Prefer one sentence and one to two rendered lines.
9. Remove responsibility-only language such as “responsible for.”
10. Avoid repeating the same action, technology list, or result across bullets.

Example:

```text
Designed reusable Java 17/Spring Boot validation services for seller-item onboarding, resulting in faster and more reliable catalog setup.
```

STAR fields are stored independently when available so the reviewer can challenge situation, task, action, and result separately before rendering the final sentence.

## Density rules

- Current or most relevant role: normally 6–10 bullets.
- Earlier relevant roles: normally 4–6 bullets.
- Projects: normally 2–3 bullets.
- Bullets should prioritize distinct architecture, implementation, reliability, security, testing, operations, and impact evidence.
- Page two should not be artificially filled; unused space is preferable to weak or repetitive content.

## Implementation

- Design tokens: `src/job_apply/resume_design.py`
- STAR contracts: `src/job_apply/star.py`
- DOCX/PDF exporters: `src/job_apply/documents.py`
- Writer prompt rule: `src/job_apply/agents.py`
