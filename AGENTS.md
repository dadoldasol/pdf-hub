# AGENTS.md

이 파일은 이 프로젝트에서 Codex/LLM 기반 개발 보조 에이전트가 작업을 시작하기 전에 반드시 읽어야 하는 기준 문서다.

## 프로젝트 개요

이 프로젝트는 PDF 파일을 입력으로 받아 내부 내용을 추출하고, Android Camera HAL, kernel layer, ISP block, chipset 변경사항, code flow, debugging guide 같은 기술 지식을 구조화하는 지식허브를 만든다.

핵심 목표:

- PDF 업로드
- 페이지별 텍스트 추출
- 청크 저장
- 요약/엔티티/관계 추출
- 임베딩 기반 검색
- 원문 PDF 페이지 링크 제공
- 지식 카드 UI 제공
- 엔티티 관계 그래프 탐색

## 현재 프로젝트 구조

```text
.
  AGENTS.md
  docs/
    README.md
    project-overview.md
    architecture.md
    tech-stack.md
    mvp-scope.md
    roadmap.md
    document-map.md
    implementation-plan.md
    technology-decisions.md
    backend/
    pdf/
    llm/
    search/
    graph/
    frontend/
    operations/

  backend/
    README.md
    pyproject.toml
    alembic.ini
    alembic/
    app/
      main.py
      api/
      core/
      db/
      models/
      schemas/
      services/
      workers/
      prompts/
    tests/
```

## 주요 문서

작업 전 필요한 문서를 먼저 확인한다.

| 문서 | 용도 |
|---|---|
| `docs/README.md` | 문서 전체 진입점 |
| `docs/project-overview.md` | 프로젝트 목표와 범위 |
| `docs/architecture.md` | 시스템 구조와 데이터 흐름 |
| `docs/tech-stack.md` | 기술 스택 기준 |
| `docs/mvp-scope.md` | MVP 포함/제외 범위 |
| `docs/implementation-plan.md` | 구현 항목과 API/모듈 계획 |
| `docs/technology-decisions.md` | 주요 기술 선택 기준 |
| `backend/README.md` | 백엔드 실행 기준 |

## 작업 방식

- 작업을 시작하기 전에 이 파일을 읽는다.
- 복잡한 작업은 파일을 수정하기 전에 짧은 계획을 먼저 세운다.
- 코드를 수정하기 전에 관련 파일을 먼저 확인한다.
- 변경은 최소한으로, 목적에 맞게 제한한다.
- 관련 없는 리팩터링을 하지 않는다.
- 명시적으로 요청받지 않은 public API 변경은 하지 않는다.
- 예상보다 작업 범위가 커지면 멈추고 이유를 설명한다.

## 구현 원칙

- MVP 범위는 `docs/mvp-scope.md`를 기준으로 한다.
- 상세 구현은 `docs/implementation-plan.md`를 기준으로 한다.
- 초기 구현은 개인 또는 소규모 팀이 유지할 수 있는 수준으로 단순하게 유지한다.
- PDF 원문 출처 추적을 항상 보존한다.
- LLM 결과는 가능한 한 JSON schema 기반으로 구조화한다.
- 검색 결과에는 가능한 한 `document_id`, `page_number`, `chunk_id`를 포함한다.
- 그래프는 초기에는 PostgreSQL 테이블 기반으로 유지하고, Neo4j는 후순위로 둔다.

## 백엔드 작업 기준

- FastAPI 앱 진입점은 `backend/app/main.py`다.
- API router는 `backend/app/api/` 아래에 둔다.
- DB 모델은 `backend/app/models/` 아래에 둔다.
- Pydantic schema는 `backend/app/schemas/` 아래에 둔다.
- 비즈니스 로직은 `backend/app/services/` 아래에 둔다.
- 긴 처리 작업은 `backend/app/workers/` 아래에 둔다.
- DB schema 변경은 Alembic migration으로 반영한다.
- 파일 저장 경로는 환경 변수 `PDF_STORAGE_DIR` 기준으로 관리한다.

## 변경 전 체크리스트

- [ ] 관련 문서를 읽었는가?
- [ ] 수정할 파일을 먼저 확인했는가?
- [ ] public API 변경 여부를 확인했는가?
- [ ] MVP 범위를 넘지 않는가?
- [ ] 테스트 또는 최소 검증 방법을 정했는가?

## 변경 후 체크리스트

- [ ] 변경 내용이 요청 범위에 맞는가?
- [ ] 불필요한 리팩터링이 섞이지 않았는가?
- [ ] 문서와 코드가 충돌하지 않는가?
- [ ] 가능한 경우 테스트 또는 문법 검증을 수행했는가?
- [ ] 실행하지 못한 검증이 있다면 이유를 남겼는가?

## 프로젝트 로컬 스킬

이 프로젝트에는 반복 작업을 줄이기 위한 repo-local skill 파일이 있다.

위치:

```text
.codex/skills/
  session-start/
  plan/
  scope-check/
  end-session/
  handoff/
  git-commit/
```

사용 기준:

| 스킬 | 사용 시점 |
|---|---|
| `session-start` | 세션 시작 시 현재 상태, 완료/미완료 작업, 다음 작업을 파악할 때 |
| `plan` | 바로 구현하지 않고 작업을 먼저 분해해야 할 때 |
| `scope-check` | 작업 중 MVP/요청 범위에서 벗어났는지 점검할 때 |
| `end-session` | 세션 종료 전 짧은 상태 요약을 남길 때 |
| `handoff` | 다음 세션이 바로 이어받을 수 있는 상세 스냅샷이 필요할 때 |
| `git-commit` | 변경사항을 검토하고 명시 승인 후 안전하게 커밋할 때 |

스킬은 보조 절차다. 실제 구현 범위와 우선순위는 항상 `docs/mvp-scope.md`, `docs/implementation-plan.md`, 최신 사용자 요청을 우선한다.
