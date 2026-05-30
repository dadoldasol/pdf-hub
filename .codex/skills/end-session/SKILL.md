---
name: end-session
description: End a work session for this PDF Knowledge Hub project by recording a concise status summary, changed files, validation performed, known limitations, and next recommended action. Use when the user says end-session, 세션 종료, 오늘 여기까지, 마무리 기록, or asks to finish the current work cleanly.
---

# End Session

Use this skill before ending a session. Keep the output short and practical.

## Workflow

1. Read `AGENTS.md`.
2. Inspect the files changed or created during the session.
3. Check whether validation was run.
4. Identify any commands that failed or could not be run.
5. Summarize next actions.

## Output Format

Return a Korean closing note:

- 이번 세션에서 완료한 것
- 변경/생성된 주요 파일
- 실행한 검증
- 실행하지 못한 검증과 이유
- 남은 작업
- 다음 세션에서 바로 시작할 작업

Do not create a long handoff document unless the user requests `handoff`.

