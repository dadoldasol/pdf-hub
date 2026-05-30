---
name: git-commit
description: Prepare, review, or create a clean Git commit for this PDF Knowledge Hub project by inspecting the working tree, separating unrelated changes, checking docs and tests, proposing a Conventional Commit message, and committing only after explicit user approval. Use when the user says git-commit, commit, 커밋 준비, 커밋 리뷰, 변경사항 커밋, or asks to create a Git commit.
---

# Git Commit

Use this skill when the user asks to prepare, review, or create a Git commit.

## Goal

Create a clean, reviewable Git commit from the current working tree.

## Workflow

1. Inspect repository state:
   - Run `git status --short`.
   - Run `git diff --stat`.
   - Run `git diff`.

2. Identify the change scope:
   - Summarize what changed.
   - Detect unrelated changes.
   - If unrelated changes exist, do not include them automatically.

3. Check local-only and generated files:
   - Never commit secrets.
   - Check that `.env`, `.venv/`, `backend/.env`, `backend/.venv/`, `backend/storage/`, logs, caches, and generated local files are not staged.
   - Never commit large generated files unless explicitly required.

4. Check documentation:
   - If code behavior changed, verify that relevant docs were updated.
   - If docs are missing, update docs or mention that docs were not needed.

5. Run available checks:
   - Prefer project-specific commands from `AGENTS.md`.
   - For backend changes, prefer:
     - `backend/.venv/Scripts/pytest.exe`
     - `backend/.venv/Scripts/ruff.exe check app tests`
   - Otherwise try common commands:
     - tests
     - lint
     - type check
     - build

6. Prepare a commit message:
   - Use Conventional Commit style.
   - Examples:
     - `feat: add PDF ingestion pipeline`
     - `fix: handle empty PDF pages`
     - `docs: document local database setup`
     - `refactor: split embedding service`
     - `test: cover PDF chunking`
     - `chore: add project gitignore`

7. Before committing, show:
   - changed files
   - summary
   - unrelated changes, if any
   - checks run
   - proposed commit message

8. Commit only after approval:
   - Run `git add` only for the intended files.
   - Run `git commit` only if the user explicitly approves.

## Rules

- Never commit secrets.
- Never commit large generated files unless explicitly required.
- Never commit unrelated changes.
- Never amend, rebase, reset, or force push unless explicitly requested.
- Do not run `git push` unless explicitly requested.
- If tests fail, do not commit unless the user explicitly accepts the failure.
- If `git` is unavailable in the shell, explain the blocker and provide the exact commands for the user to run.

