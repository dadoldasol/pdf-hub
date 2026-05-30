---
name: scope-check
description: Check whether ongoing work in this PDF Knowledge Hub project is still aligned with the requested task, MVP scope, AGENTS.md rules, and implementation plan. Use when the user says scope-check, 범위 확인, 길을 잃었는지 확인, 중간 점검, or when the work appears to be expanding beyond the original request.
---

# Scope Check

Use this skill during a session to detect drift before continuing.

## Workflow

1. Re-read the user's latest request.
2. Read `AGENTS.md`.
3. Compare current work against:
   - `docs/mvp-scope.md`
   - `docs/implementation-plan.md`
   - files already modified in this session
4. Identify whether the current path is:
   - within scope
   - slightly expanded but acceptable
   - out of scope and should stop
5. Recommend the smallest next action.

## Output Format

Return a Korean scope check:

- 원래 요청
- 현재 진행 중인 작업
- 범위 안/밖 판단
- 계속해도 되는 작업
- 멈추거나 미뤄야 할 작업
- 다음 최소 액션

If scope has expanded materially, stop and explain before editing more files.

