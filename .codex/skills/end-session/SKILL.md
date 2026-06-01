---
name: end-session
description: End a work session for this PDF Knowledge Hub project by recording a concise status summary, changed files, validation performed, known limitations, and next recommended action. Use when the user says end-session, 세션 종료, 오늘 여기까지, 마무리 기록, or asks to finish the current work cleanly.
---

# End Session

Use this skill before ending a session. Keep the conversational response short and practical.

## Workflow

1. Read `AGENTS.md`.
2. Inspect the repository state with `git status --short`.
3. Inspect recent commits when relevant with `git log --oneline -5`.
4. Identify files changed or created during the session.
5. Check whether validation was run.
6. Identify any commands that failed or could not be run.
7. Summarize next actions.
8. Create a persistent Markdown history file under `docs/history/`.

## Persistent History File

Always create or update a Markdown file for the session under:

```text
docs/history/YYYY-MM-DD-작업내용.md
```

Rules:

- Use the current local date for `YYYY-MM-DD`.
- Use a short Korean or English slug for `작업내용`.
  - Example: `2026-05-31-frontend-mvp.md`
  - Example: `2026-05-31-backend-mvp.md`
- If the file already exists, update it instead of creating a duplicate.
- Include the next-session prompt in the same file.
- Do not store secrets, `.env` values, local absolute credentials, or large generated outputs.
- Keep the file useful for the next Codex session, not as a full transcript.

Recommended sections:

```markdown
# YYYY-MM-DD 작업 내용

## 세션 요약

## 완료한 작업

## 변경/생성한 주요 파일

## 검증 결과

## 실행하지 못한 검증

## 남은 작업

## 다음 세션에서 바로 시작할 작업

## 다음 세션 프롬프트
```

## Output Format

Return a Korean closing note:

- 이번 세션에서 완료한 것
- 변경/생성한 주요 파일
- 실행한 검증
- 실행하지 못한 검증과 이유
- 남은 작업
- 다음 세션에서 바로 시작할 작업
- 저장한 history 파일 경로

Do not create a long handoff section in the chat unless the user requests `handoff`.
