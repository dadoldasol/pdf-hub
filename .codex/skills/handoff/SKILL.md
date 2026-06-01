---
name: handoff
description: Create a complete handoff snapshot for the next session in this PDF Knowledge Hub project, including current state, decisions, changed files, remaining tasks, risks, validation status, and exact recommended next steps. Use when the user says handoff, 인수인계, 다음 세션 준비, 상태 스냅샷, or asks to make continuation easy for another Codex session.
---

# Handoff

Use this skill when the next session should be able to continue without rediscovering the project state.

## Workflow

1. Read `AGENTS.md`.
2. Inspect relevant docs and implementation files.
3. Inspect repository state with `git status --short`.
4. Inspect recent commits with `git log --oneline -5`.
5. Identify the current project milestone.
6. List important decisions already made.
7. List changed files and their purpose.
8. Record validation status and known gaps.
9. Define exact next steps in priority order.
10. Create or update a persistent Markdown handoff/history file under `docs/history/`.

## Persistent History File

Always create or update a Markdown file under:

```text
docs/history/YYYY-MM-DD-작업내용.md
```

Rules:

- Use the current local date for `YYYY-MM-DD`.
- Use a short Korean or English slug for `작업내용`.
  - Example: `2026-05-31-frontend-mvp.md`
  - Example: `2026-05-31-e2e-validation.md`
- If `end-session` and `handoff` are both requested for the same session, write both summaries into the same file.
- Include a copy-ready next-session prompt in the file.
- Do not store secrets, `.env` values, local absolute credentials, or large generated outputs.
- Prefer concise, structured notes over transcript-style logs.

Recommended sections:

```markdown
# YYYY-MM-DD 작업 내용

## 세션 요약

## 프로젝트 현재 상태

## 완료한 작업

## 주요 결정 사항

## 변경/생성한 주요 파일

## 검증 결과

## 미검증/리스크

## 다음 작업 순서

## 다음 세션 프롬프트
```

## Output Format

Return a structured Korean handoff:

- 프로젝트 현재 상태
- 완료한 작업
- 주요 결정 사항
- 변경/생성한 파일
- 검증 결과
- 미검증/리스크
- 다음 작업 순서
- 다음 세션 시작 프롬프트
- 저장한 history 파일 경로

If the user asks for a persistent artifact, use `docs/history/` by default.
