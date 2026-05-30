---
name: plan
description: Plan a coding or documentation task in this PDF Knowledge Hub project before implementation by decomposing work into small steps, identifying files to inspect, defining expected changes, validation, and scope limits. Use when the user says plan, make a plan, 작업 분해, 계획부터, or asks not to start coding immediately.
---

# Plan

Use this skill when the user wants a plan before edits, or when the task is complex enough that immediate implementation would be risky.

## Workflow

1. Read `AGENTS.md`.
2. Identify the user's concrete goal.
3. Inspect only the files needed to understand the task.
4. Break the task into small steps.
5. Mark which steps require file edits and which are verification-only.
6. Identify likely risks, public API changes, migrations, or scope expansion.
7. Ask a question only if a reasonable assumption would be risky.

## Output Format

Return a concise Korean plan:

- 목표
- 확인한 근거 파일
- 작업 단계
- 변경 예상 파일
- 검증 방법
- 범위 밖으로 둘 항목

Do not implement until the user approves or clearly asks to proceed.

