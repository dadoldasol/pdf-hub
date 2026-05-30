# 개발 로드맵

## 일정 선택

현실적인 MVP 일정은 6주를 권장한다.

4주는 기본 업로드/검색까지는 가능하지만 LLM 추출, 지식 카드, 그래프 UI 품질이 부족해질 가능성이 높다. 8주는 안정적이지만 초기 검증 속도가 느려진다. 6주는 개인 또는 소규모 팀이 기능을 검증하기에 적절하다.

## 1주차: 프로젝트 기반 구축

| 항목 | 내용 |
|---|---|
| 목표 | FastAPI, DB, 파일 저장, 기본 프로젝트 구조 구축 |
| 구현 항목 | FastAPI scaffold, PostgreSQL 연결, Alembic, document upload API, local file storage |
| 산출물 | 실행 가능한 backend, upload API, documents table |
| 완료 기준 | PDF 업로드 후 DB에 document record와 파일 경로가 저장됨 |
| 리스크 | 개발 환경 차이, DB 설정 지연 |

## 2주차: PDF 처리 파이프라인

| 항목 | 내용 |
|---|---|
| 목표 | PDF에서 페이지별 텍스트를 추출하고 저장 |
| 구현 항목 | PyMuPDF 추출, page 저장, chunk 생성, processing job 상태 관리 |
| 산출물 | document_pages, document_chunks 저장 |
| 완료 기준 | PDF 업로드 후 페이지/청크 데이터가 DB에 생성됨 |
| 리스크 | PDF별 텍스트 추출 품질 편차 |

## 3주차: 임베딩과 검색

| 항목 | 내용 |
|---|---|
| 목표 | 청크 임베딩 생성 및 벡터 검색 구현 |
| 구현 항목 | embedding service, pgvector schema, search API, top-k result |
| 산출물 | 자연어 검색 API |
| 완료 기준 | 질문을 입력하면 관련 chunk와 page number가 반환됨 |
| 리스크 | 임베딩 비용, pgvector 설정 문제 |

## 4주차: LLM 추출

| 항목 | 내용 |
|---|---|
| 목표 | 요약, 엔티티, 관계 후보를 구조화해 저장 |
| 구현 항목 | prompt template, JSON schema, entity extraction, summary generation, relation extraction |
| 산출물 | entities, entity_mentions, knowledge_edges |
| 완료 기준 | `IFE` 같은 엔티티가 추출되고 관련 chunk와 연결됨 |
| 리스크 | LLM 출력 불안정, entity 중복 |

## 5주차: Frontend MVP

| 항목 | 내용 |
|---|---|
| 목표 | 사용자가 업로드/검색/지식 카드를 사용할 수 있는 UI 구현 |
| 구현 항목 | 문서 목록, 업로드 화면, 검색 화면, 지식 카드, 엔티티 상세 |
| 산출물 | 기본 웹 UI |
| 완료 기준 | 브라우저에서 PDF 업로드 후 검색 결과와 지식 카드를 확인 가능 |
| 리스크 | API 응답 구조 변경, UI 범위 확대 |

## 6주차: 그래프 뷰와 안정화

| 항목 | 내용 |
|---|---|
| 목표 | 기본 그래프 탐색과 MVP 안정화 |
| 구현 항목 | graph API, graph view, 오류 처리, 테스트, 샘플 PDF 검증 |
| 산출물 | MVP demo |
| 완료 기준 | 엔티티 상세에서 관련 노드/엣지 그래프를 볼 수 있음 |
| 리스크 | 그래프 데이터 품질, 관계 추출 정확도 |

## MVP 이후 확장

| 단계 | 확장 항목 |
|---|---|
| Phase 2 | hybrid search, keyword search 강화, reranking |
| Phase 3 | OCR 고도화, 표 추출 개선, 페이지 이미지 preview |
| Phase 4 | entity merge, chipset comparison, debugging guide 자동 생성 |
| Phase 5 | Neo4j 검토, 고급 그래프 분석, 팀 사용 기능 |

