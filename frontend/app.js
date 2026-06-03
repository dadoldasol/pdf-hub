const API_BASE = localStorage.getItem("kh_api_base") || "http://127.0.0.1:8000";

const state = {
  documents: [],
  entities: [],
  selectedEntityId: null,
  activeJobId: null,
};

const el = {
  apiState: document.querySelector("#apiState"),
  uploadState: document.querySelector("#uploadState"),
  pdfInput: document.querySelector("#pdfInput"),
  fileName: document.querySelector("#fileName"),
  uploadButton: document.querySelector("#uploadButton"),
  jobProgress: document.querySelector("#jobProgress"),
  progressFill: document.querySelector("#progressFill"),
  progressText: document.querySelector("#progressText"),
  cancelJobButton: document.querySelector("#cancelJobButton"),
  jobSteps: document.querySelector("#jobSteps"),
  refreshButton: document.querySelector("#refreshButton"),
  documentList: document.querySelector("#documentList"),
  searchInput: document.querySelector("#searchInput"),
  searchButton: document.querySelector("#searchButton"),
  searchState: document.querySelector("#searchState"),
  searchResults: document.querySelector("#searchResults"),
  entityList: document.querySelector("#entityList"),
  entityCount: document.querySelector("#entityCount"),
  resultCount: document.querySelector("#resultCount"),
  selectedEntityType: document.querySelector("#selectedEntityType"),
  knowledgeCard: document.querySelector("#knowledgeCard"),
  cardState: document.querySelector("#cardState"),
  graphState: document.querySelector("#graphState"),
  graphView: document.querySelector("#graphView"),
  pageDialog: document.querySelector("#pageDialog"),
  pageDialogTitle: document.querySelector("#pageDialogTitle"),
  pageText: document.querySelector("#pageText"),
  closeDialogButton: document.querySelector("#closeDialogButton"),
};

const JOB_STEPS = [
  { status: "queued", label: "대기" },
  { status: "extracting_pdf", label: "PDF 텍스트 추출" },
  { status: "chunking", label: "청크 생성" },
  { status: "embedding", label: "임베딩 생성" },
  { status: "extracting_knowledge", label: "엔티티 추출" },
  { status: "completed", label: "완료" },
  { status: "canceled", label: "중지됨" },
];

function api(path, options = {}) {
  return fetch(`${API_BASE}${path}`, options).then(async (response) => {
    if (!response.ok) {
      const detail = await response.text();
      throw new Error(detail || `${response.status} ${response.statusText}`);
    }
    return response.json();
  });
}

function setText(node, text) {
  node.textContent = text;
}

function formatDate(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

async function refreshAll() {
  await Promise.all([loadDocuments(), loadEntities()]);
}

async function checkApi() {
  try {
    await api("/health");
    setText(el.apiState, "API 연결됨");
  } catch {
    setText(el.apiState, "API 연결 실패");
  }
}

async function loadDocuments() {
  try {
    state.documents = await api("/api/documents");
    renderDocuments();
  } catch {
    el.documentList.className = "list empty";
    setText(el.documentList, "문서 로드 실패");
  }
}

async function loadEntities() {
  try {
    state.entities = await api("/api/entities");
    renderEntities();
  } catch {
    el.entityList.className = "entity-list empty";
    setText(el.entityList, "엔티티 로드 실패");
  }
}

function renderDocuments() {
  el.documentList.className = state.documents.length ? "list" : "list empty";
  el.documentList.innerHTML = "";
  if (!state.documents.length) {
    setText(el.documentList, "문서 없음");
    return;
  }

  for (const documentItem of state.documents) {
    const row = document.createElement("div");
    row.className = "item";
    row.innerHTML = `
      <div class="item-title">${escapeHtml(documentItem.title)}</div>
      <div class="item-meta">${escapeHtml(documentItem.status)} · ${documentItem.page_count ?? 0}p · ${formatDate(documentItem.created_at)}</div>
    `;
    row.insertAdjacentHTML("beforeend", '<button class="item-delete danger-button" type="button">삭제</button>');
    row.querySelector(".item-delete").addEventListener("click", () => {
      deleteDocument(documentItem.id, documentItem.title);
    });
    el.documentList.append(row);
  }
}

function renderEntities() {
  el.entityCount.textContent = `엔티티 ${state.entities.length}`;
  el.entityList.className = state.entities.length ? "entity-list" : "entity-list empty";
  el.entityList.innerHTML = "";
  if (!state.entities.length) {
    setText(el.entityList, "엔티티 없음");
    return;
  }

  for (const entity of state.entities) {
    const button = document.createElement("button");
    button.className = `entity-row ${entity.id === state.selectedEntityId ? "active" : ""}`;
    button.type = "button";
    button.innerHTML = `
      <span class="entity-name">${escapeHtml(entity.name)}</span>
      <span class="entity-meta">${escapeHtml(entity.entity_type)}</span>
    `;
    button.addEventListener("click", () => selectEntity(entity.id));
    el.entityList.append(button);
  }
}

async function uploadSelectedFile() {
  const file = el.pdfInput.files[0];
  if (!file) {
    setText(el.uploadState, "파일 없음");
    return;
  }

  const body = new FormData();
  body.append("file", file);
  setText(el.uploadState, "업로드 중");
  el.uploadButton.disabled = true;

  try {
    const result = await api("/api/documents/upload", {
      method: "POST",
      body,
    });
    if (result.duplicate) {
      state.activeJobId = null;
      el.jobProgress.hidden = true;
      setText(el.uploadState, "이미 등록됨");
      el.progressText.textContent = "같은 PDF가 이미 등록되어 새 작업을 만들지 않았습니다.";
      await refreshAll();
      return;
    }

    state.activeJobId = result.job_id;
    renderJobProgress({ status: result.status, extra_metadata: {} });
    setText(el.uploadState, "처리 중");
    const job = await waitForJob(result.job_id);
    setText(el.uploadState, job?.status === "canceled" ? "중지됨" : "완료");
    await refreshAll();
  } catch (error) {
    setText(el.uploadState, "실패");
    el.progressText.textContent = error.message || "처리 실패";
  } finally {
    el.uploadButton.disabled = false;
  }
}

async function waitForJob(jobId) {
  while (state.activeJobId === jobId) {
    const job = await api(`/api/jobs/${jobId}`);
    renderJobProgress(job);
    if (job.status === "completed") return job;
    if (job.status === "canceled") return job;
    if (job.status === "failed") throw new Error(job.error_message || "job failed");
    await refreshAll();
    await delay(1200);
  }
  return null;
}

async function deleteDocument(documentId, title) {
  const confirmed = window.confirm(`문서를 삭제할까요?\n\n${title}`);
  if (!confirmed) return;

  try {
    await api(`/api/documents/${documentId}`, { method: "DELETE" });
    state.activeJobId = null;
    el.jobProgress.hidden = true;
    setText(el.uploadState, "삭제됨");
    await refreshAll();
  } catch (error) {
    setText(el.uploadState, "삭제 실패");
    el.progressText.textContent = error.message || "문서 삭제 실패";
  }
}

async function cancelActiveJob() {
  if (!state.activeJobId) return;

  el.cancelJobButton.disabled = true;
  setText(el.uploadState, "중지 요청됨");
  el.progressText.textContent = "중지 요청됨 · 현재 처리 단위가 끝나면 멈춥니다";

  try {
    const job = await api(`/api/jobs/${state.activeJobId}/cancel`, { method: "POST" });
    renderJobProgress(job);
  } catch (error) {
    el.cancelJobButton.disabled = false;
    el.progressText.textContent = error.message || "중지 요청 실패";
  }
}

function renderJobProgress(job) {
  const metadata = job.extra_metadata || {};
  const progress = calculateProgress(job.status, metadata);
  el.jobProgress.hidden = false;
  el.progressFill.style.width = `${Math.round(progress * 100)}%`;
  el.progressText.textContent = formatJobProgress(job.status, metadata, progress);
  el.cancelJobButton.hidden = ["completed", "failed", "canceled"].includes(job.status);
  el.cancelJobButton.disabled = Boolean(metadata.cancel_requested);
  renderJobSteps(job.status);
}

function calculateProgress(status, metadata) {
  if (status === "completed") return 1;
  if (status === "canceled") return ratio(metadata.processed_pages, metadata.total_pages);
  if (status === "failed") return 0;

  const stepIndex = Math.max(
    JOB_STEPS.findIndex((step) => step.status === status),
    0,
  );
  const base = stepIndex / (JOB_STEPS.length - 1);
  const stepWeight = 1 / (JOB_STEPS.length - 1);
  const withinStep = calculateStepProgress(status, metadata);
  return Math.min(base + withinStep * stepWeight, 0.98);
}

function calculateStepProgress(status, metadata) {
  if (status === "extracting_pdf" || status === "chunking") {
    return ratio(metadata.processed_pages, metadata.total_pages);
  }
  if (status === "embedding" || status === "extracting_knowledge") {
    return ratio(metadata.processed_chunks, metadata.total_chunks);
  }
  return 0;
}

function ratio(value, total) {
  const numericValue = Number(value || 0);
  const numericTotal = Number(total || 0);
  if (!numericTotal) return 0;
  return Math.max(0, Math.min(numericValue / numericTotal, 1));
}

function formatJobProgress(status, metadata, progress) {
  const label = JOB_STEPS.find((step) => step.status === status)?.label || status;
  const percent = `${Math.round(progress * 100)}%`;
  const currentPage = metadata.current_page ? `현재 p.${metadata.current_page}` : null;
  const lastPageSeconds = metadata.last_page_seconds
    ? `최근 페이지 ${Number(metadata.last_page_seconds).toFixed(2)}초`
    : null;
  const pageText = metadata.total_pages
    ? `페이지 ${metadata.processed_pages || 0}/${metadata.total_pages}`
    : "페이지 확인 중";
  const chunkText = metadata.total_chunks
    ? `청크 ${metadata.processed_chunks || 0}/${metadata.total_chunks}`
    : "청크 대기";
  const entityText = `엔티티 mention ${metadata.entity_mentions || 0}`;
  if (status === "completed") return `완료 · ${pageText} · ${chunkText} · ${entityText}`;
  if (status === "canceled") return `중지됨 · ${pageText} · ${chunkText}`;
  if (status === "failed") return "실패";
  if (metadata.cancel_requested) return `중지 요청됨 · ${pageText} · ${chunkText}`;
  return [label, percent, currentPage, pageText, chunkText, lastPageSeconds].filter(Boolean).join(" · ");
}

function renderJobSteps(status) {
  const activeIndex = JOB_STEPS.findIndex((step) => step.status === status);
  el.jobSteps.innerHTML = "";
  JOB_STEPS.forEach((step, index) => {
    const item = document.createElement("li");
    const isDone = status === "completed" || (activeIndex > -1 && index < activeIndex);
    const isActive = index === activeIndex;
    item.className = `${isDone ? "done" : ""} ${isActive ? "active" : ""}`.trim();
    item.textContent = step.label;
    el.jobSteps.append(item);
  });
}

async function runSearch() {
  const query = el.searchInput.value.trim();
  if (!query) return;

  setText(el.searchState, "검색 중");
  try {
    const response = await api("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, top_k: 8 }),
    });
    renderSearchResults(response.results);
    setText(el.searchState, "완료");
  } catch {
    setText(el.searchState, "실패");
  }
}

function renderSearchResults(results) {
  el.resultCount.textContent = `결과 ${results.length}`;
  el.searchResults.className = results.length ? "result-list" : "result-list empty";
  el.searchResults.innerHTML = "";
  if (!results.length) {
    setText(el.searchResults, "검색 결과 없음");
    return;
  }

  for (const result of results) {
    const row = document.createElement("div");
    row.className = "result-item";
    const tags = result.related_entities
      .map((name) => `<span class="tag">${escapeHtml(name)}</span>`)
      .join("");
    row.innerHTML = `
      <div class="result-title">${escapeHtml(result.document_title || "Untitled")} · p.${result.page_number ?? "-"}</div>
      <div class="result-meta">score ${Number(result.score || 0).toFixed(3)}</div>
      <div>${escapeHtml(result.snippet)}</div>
      <div class="result-tags">${tags}</div>
    `;
    row.addEventListener("click", () => openPage(result.document_id, result.page_number));
    el.searchResults.append(row);
  }
}

async function selectEntity(entityId) {
  state.selectedEntityId = entityId;
  renderEntities();
  await Promise.all([loadKnowledgeCard(entityId), loadGraph(entityId)]);
}

async function loadKnowledgeCard(entityId) {
  setText(el.cardState, "로드 중");
  try {
    const card = await api(`/api/entities/${entityId}/knowledge-card`);
    el.selectedEntityType.textContent = card.entity.entity_type;
    renderKnowledgeCard(card);
    setText(el.cardState, "완료");
  } catch {
    setText(el.cardState, "실패");
  }
}

function renderKnowledgeCard(card) {
  const sources = card.source_pages
    .map(
      (source) => `
        <div class="source-item">
          <div class="source-meta">${escapeHtml(source.document_title)} · p.${source.page_number} · ${Number(source.confidence || 0).toFixed(2)}</div>
          <div>${escapeHtml(source.snippet || "")}</div>
          <button class="source-action" type="button" data-document-id="${source.document_id}" data-page-number="${source.page_number}">페이지 열기</button>
        </div>
      `,
    )
    .join("");

  el.knowledgeCard.className = "knowledge-card";
  el.knowledgeCard.innerHTML = `
    <div class="knowledge-title">
      <h3>${escapeHtml(card.entity.name)}</h3>
      <span class="state-pill">${escapeHtml(card.entity.entity_type)}</span>
    </div>
    <div>${escapeHtml(card.summary || "")}</div>
    <div class="source-list">${sources || '<div class="source-item empty">출처 없음</div>'}</div>
  `;

  el.knowledgeCard.querySelectorAll(".source-action").forEach((button) => {
    button.addEventListener("click", () => {
      openPage(button.dataset.documentId, Number(button.dataset.pageNumber));
    });
  });
}

async function loadGraph(entityId) {
  setText(el.graphState, "로드 중");
  try {
    const graph = await api(`/api/graph/entities/${entityId}`);
    renderGraph(graph);
    setText(el.graphState, "완료");
  } catch {
    setText(el.graphState, "실패");
  }
}

function renderGraph(graph) {
  const svg = el.graphView;
  const width = svg.clientWidth || 520;
  const height = svg.clientHeight || 330;
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.innerHTML = "";

  if (!graph.nodes.length) {
    const text = svgText(width / 2, height / 2, "그래프 없음");
    svg.append(text);
    return;
  }

  const center = { x: width / 2, y: height / 2 };
  const radius = Math.max(88, Math.min(width, height) * 0.34);
  const positions = new Map();

  graph.nodes.forEach((node, index) => {
    if (index === 0) {
      positions.set(node.id, center);
      return;
    }
    const angle = ((index - 1) / Math.max(graph.nodes.length - 1, 1)) * Math.PI * 2 - Math.PI / 2;
    positions.set(node.id, {
      x: center.x + Math.cos(angle) * radius,
      y: center.y + Math.sin(angle) * radius,
    });
  });

  for (const edge of graph.edges) {
    const source = positions.get(edge.source_node_id);
    const target = positions.get(edge.target_node_id);
    if (!source || !target) continue;
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", source.x);
    line.setAttribute("y1", source.y);
    line.setAttribute("x2", target.x);
    line.setAttribute("y2", target.y);
    line.setAttribute("class", "graph-edge");
    svg.append(line);
  }

  graph.nodes.forEach((node, index) => {
    const position = positions.get(node.id);
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", position.x);
    circle.setAttribute("cy", position.y);
    circle.setAttribute("r", index === 0 ? 34 : 28);
    circle.setAttribute("class", `graph-node ${index === 0 ? "graph-source" : ""}`);
    svg.append(circle);
    svg.append(svgText(position.x, position.y + 4, node.name));
  });
}

function svgText(x, y, value) {
  const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
  text.setAttribute("x", x);
  text.setAttribute("y", y);
  text.setAttribute("class", "graph-label");
  text.textContent = value;
  return text;
}

async function openPage(documentId, pageNumber) {
  if (!documentId || !pageNumber) return;
  try {
    const page = await api(`/api/documents/${documentId}/pages/${pageNumber}`);
    el.pageDialogTitle.textContent = `p.${page.page_number}`;
    el.pageText.textContent = page.text || "";
    el.pageDialog.showModal();
  } catch {
    el.pageDialogTitle.textContent = "페이지 로드 실패";
    el.pageText.textContent = "";
    el.pageDialog.showModal();
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

el.pdfInput.addEventListener("change", () => {
  const file = el.pdfInput.files[0];
  el.fileName.textContent = file ? file.name : "선택된 파일 없음";
});
el.uploadButton.addEventListener("click", uploadSelectedFile);
el.cancelJobButton.addEventListener("click", cancelActiveJob);
el.refreshButton.addEventListener("click", refreshAll);
el.searchButton.addEventListener("click", runSearch);
el.searchInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") runSearch();
});
el.closeDialogButton.addEventListener("click", () => el.pageDialog.close());

checkApi();
refreshAll();
