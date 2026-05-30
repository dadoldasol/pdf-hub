---
name: handoff
description: Create a complete handoff snapshot for the next session in this PDF Knowledge Hub project, including current state, decisions, changed files, remaining tasks, risks, validation status, and exact recommended next steps. Use when the user says handoff, 인수인계, 다음 세션 준비, 상태 스냅샷, or asks to make continuation easy for another Codex session.
---

# Handoff

Use this skill when the next session should be able to continue without rediscovering the project state.

## Workflow

1. Read `AGENTS.md`.
2. Inspect relevant docs and implementation files.
3. Identify the current project milestone.
4. List important decisions already made.
5. List changed files and their purpose.
6. Record validation status and known gaps.
7. Define exact next steps in priority order.

## Output Format

Return a structured Korean handoff:

- 프로젝트 현재 상태
- 완료된 작업
- 주요 결정 사항
- 변경/생성된 파일
- 검증 결과
- 미검증/리스크
- 다음 작업 순서
- 다음 세션 시작 프롬프트

If the user asks for a persistent artifact, create or update a handoff Markdown file under `docs/operations/` or another agreed location.

