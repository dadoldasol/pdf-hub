# 로컬 개발 환경

이 문서는 PDF Knowledge Hub를 로컬에서 실행하기 위한 최소 개발 환경을 정의한다.

## 1. 기본 개발 방식

MVP 단계에서는 Docker Compose로 PostgreSQL + pgvector를 실행하고, backend는 로컬 Python 가상환경에서 실행한다.

```text
PostgreSQL + pgvector: Docker Compose
FastAPI backend: local Python venv
Frontend: local Node.js static server
```

## 2. 필요 도구

| 도구 | 용도 |
|---|---|
| Docker Desktop | PostgreSQL + pgvector 실행 |
| Python 3.11+ | FastAPI backend 실행 |
| Node.js | Frontend static server 실행 |
| PowerShell | Windows 로컬 명령 실행 |
| PostgreSQL client 선택 | DB 접속 확인용. 없어도 backend migration은 가능 |

## 3. PostgreSQL + pgvector 실행

프로젝트 루트에서 실행한다.

```powershell
docker compose up -d postgres
```

상태 확인:

```powershell
docker compose ps
```

로그 확인:

```powershell
docker compose logs -f postgres
```

DB 접속 정보:

| 항목 | 값 |
|---|---|
| host | `localhost` |
| port | `5432` |
| database | `pdf_hub` |
| user | `postgres` |
| password | `postgres` |

backend의 기본 연결 문자열:

```text
postgresql+psycopg://postgres:postgres@localhost:5432/pdf_hub
```

## 4. pgvector 확인

컨테이너 안에서 확인한다.

```powershell
docker compose exec postgres psql -U postgres -d pdf_hub -c "CREATE EXTENSION IF NOT EXISTS vector;"
docker compose exec postgres psql -U postgres -d pdf_hub -c "\dx vector"
```

MVP migration에도 `CREATE EXTENSION IF NOT EXISTS vector`가 포함되어 있으므로, 일반적으로는 `alembic upgrade head` 시 자동 생성된다.

## 5. Backend 환경 변수

backend 디렉토리에서 `.env.example`을 `.env`로 복사한다.

```powershell
Copy-Item backend\.env.example backend\.env
```

초기 `.env`에서 최소 확인할 값:

```text
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/pdf_hub
PDF_STORAGE_DIR=./storage/pdfs
```

## 6. Backend 의존성 설치

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

현재 시스템에서 `python` 명령이 잡히지 않으면 Python 3.11+ 설치 후 PATH를 설정한다.

## 7. DB Migration

backend 디렉토리에서 실행한다.

```powershell
alembic upgrade head
```

성공하면 다음 테이블이 생성된다.

- `documents`
- `document_pages`
- `document_chunks`
- `entities`
- `entity_mentions`
- `knowledge_nodes`
- `knowledge_edges`
- `processing_jobs`

## 8. Backend 실행

backend 디렉토리에서 실행한다.

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

PDF 업로드는 처리 job을 `queued` 상태로 만든 뒤 바로 반환한다. 실제 PDF 추출/청크/임베딩 처리는 별도 터미널에서 ingestion worker를 실행해야 진행된다.

```powershell
.\.venv\Scripts\python.exe -m app.workers.worker_main
```

로컬에서 대기 중인 job 하나만 처리하고 종료하려면 다음을 사용한다.

```powershell
.\.venv\Scripts\python.exe -m app.workers.worker_main --once
```

확인:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/docs
```

## 9. Frontend 실행

프로젝트 루트에서 실행한다.

```powershell
node frontend\server.js
```

확인:

```text
http://127.0.0.1:5173
```

backend 또는 frontend를 재실행하려면 해당 터미널에서 `Ctrl+C`로 중지한 뒤 같은 명령을 다시 실행한다.

## 10. 종료

DB 컨테이너 중지:

```powershell
docker compose stop postgres
```

DB 데이터까지 삭제:

```powershell
docker compose down -v
```

주의: `down -v`는 PostgreSQL volume을 삭제하므로 로컬 DB 데이터가 모두 사라진다.
