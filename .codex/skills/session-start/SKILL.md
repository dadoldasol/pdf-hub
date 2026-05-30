---
name: session-start
description: Start a work session for this PDF Knowledge Hub project by reading AGENTS.md, inspecting the current repository state, checking recent docs and backend structure, and summarizing what is done, what is unknown, and what should happen next. Use when the user says session-start, start session, resume work, continue from last session, or asks to understand the current project state before coding.
---

# Session Start

Use this skill at the beginning of a session before making code changes.

## Workflow

1. Read `AGENTS.md`.
2. Inspect the repository structure with `rg --files` or equivalent.
3. Read the most relevant planning documents:
   - `docs/mvp-scope.md`
   - `docs/implementation-plan.md`
   - `docs/architecture.md` when architecture decisions matter
   - `docs/roadmap.md` when sequencing matters
4. Inspect active implementation areas only as needed:
   - `backend/app/main.py`
   - `backend/app/api/`
   - `backend/app/models/`
   - `backend/app/services/`
5. Summarize the current state in Korean.

## Output Format

Return a short status note with:

- 현재 완료된 것
- 현재 미완료인 것
- 바로 다음에 할 수 있는 작업
- 확인이 필요한 리스크 또는 질문

Do not edit files unless the user explicitly asks to continue with implementation.

