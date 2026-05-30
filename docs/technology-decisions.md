# 기술 선택 기준

## 1. PostgreSQL + pgvector vs SQLite + LanceDB/ChromaDB

| 항목 | PostgreSQL + pgvector | SQLite + LanceDB/ChromaDB |
|---|---|---|
| 장점 | metadata와 vector를 한 DB에서 관리, 확장성 좋음 | 로컬 개발이 간단, 설치 부담 낮음 |
| 단점 | 초기 세팅 필요 | 운영 확장과 관계 데이터 관리가 약함 |
| 추천 기본값 | PostgreSQL + pgvector | 빠른 prototype일 때만 |

선택 기준:

- 장기적으로 API 서버와 UI를 운영할 계획이면 PostgreSQL + pgvector
- 하루 이틀짜리 로컬 prototype이면 SQLite + LanceDB

나중에 바꿔야 하는 시점:

- 문서/청크/엔티티 관계가 늘어나고 transaction 관리가 필요하면 PostgreSQL로 전환한다.

## 2. OpenAI API vs 로컬 LLM

| 항목 | OpenAI API | 로컬 LLM |
|---|---|---|
| 장점 | 품질 안정적, 구축 빠름, JSON 추출에 강함 | 데이터 외부 전송 없음, 장기 비용 통제 |
| 단점 | API 비용, 보안 검토 필요 | 인프라 부담, 모델 품질 튜닝 필요 |
| 추천 기본값 | OpenAI API | 보안상 외부 전송 불가할 때 |

선택 기준:

- 빠른 MVP와 품질 검증이 목적이면 OpenAI API
- 사내 보안 정책상 문서 외부 전송이 불가능하면 로컬 LLM

나중에 바꿔야 하는 시점:

- 월 비용이 부담된다.
- 문서 보안 정책이 강화된다.
- 추출 task가 정형화되어 작은 모델로도 충분해진다.

## 3. PyMuPDF vs pdfplumber

| 항목 | PyMuPDF | pdfplumber |
|---|---|---|
| 장점 | 빠름, 페이지 렌더링 가능, 기본 추출 우수 | 표와 layout 분석에 유리 |
| 단점 | 복잡한 표 추출은 약함 | 속도가 느릴 수 있음 |
| 추천 기본값 | 기본 텍스트 추출 | 표 추출 보조 |

선택 기준:

- 대부분의 페이지 텍스트 추출은 PyMuPDF
- 표가 중요한 페이지는 pdfplumber를 추가 적용

나중에 바꿔야 하는 시점:

- 표 기반 정보가 핵심 기능이 되면 pdfplumber 처리 비중을 늘린다.

## 4. Tesseract vs PaddleOCR

| 항목 | Tesseract | PaddleOCR |
|---|---|---|
| 장점 | 설치와 사용이 비교적 단순 | 표, 복잡한 layout, 다국어 OCR 품질이 좋을 수 있음 |
| 단점 | 복잡한 문서 OCR 품질 한계 | 설치/운영 부담 큼 |
| 추천 기본값 | Tesseract fallback | OCR 품질이 중요해질 때 |

선택 기준:

- MVP에서는 OCR을 핵심 경로에 넣지 않는다.
- 텍스트 없는 페이지를 감지하고 Tesseract fallback만 제공한다.

나중에 바꿔야 하는 시점:

- 이미지 기반 PDF 비율이 높다.
- 표/도식 OCR 정확도가 중요하다.
- Tesseract 결과가 검색 품질을 크게 떨어뜨린다.

## 5. PostgreSQL graph table vs Neo4j

| 항목 | PostgreSQL graph table | Neo4j |
|---|---|---|
| 장점 | 기존 DB와 통합, 운영 단순 | 그래프 탐색과 알고리즘에 강함 |
| 단점 | 복잡한 graph query는 불편 | 별도 운영 필요 |
| 추천 기본값 | PostgreSQL graph table | 그래프가 핵심 제품이 된 이후 |

선택 기준:

- 1-hop 관계 탐색과 카드 표시 중심이면 PostgreSQL
- path query, graph algorithm, relation reasoning이 필요하면 Neo4j

나중에 바꿔야 하는 시점:

- `IFE -> CSID -> chipset -> debugging keyword` 같은 multi-hop 탐색이 주요 기능이 된다.
- PostgreSQL recursive query가 유지보수하기 어려워진다.

## 6. React SPA vs Next.js

| 항목 | React SPA | Next.js |
|---|---|---|
| 장점 | 내부 도구 구현이 단순 | routing, server 기능, 배포 구조가 좋음 |
| 단점 | SEO/서버 기능 약함 | 구조가 조금 더 무거움 |
| 추천 기본값 | 빠른 MVP면 React SPA | 장기 운영이면 Next.js |

선택 기준:

- 개인용/내부용 MVP는 React SPA
- 인증, 공유 링크, 서버 렌더링, 배포 체계가 필요하면 Next.js

나중에 바꿔야 하는 시점:

- 화면 수가 많아진다.
- 사용자별 권한이나 공유 페이지가 필요하다.
- 프론트엔드 라우팅과 데이터 fetching 구조를 표준화해야 한다.

