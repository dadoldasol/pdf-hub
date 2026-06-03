import json
from dataclasses import dataclass
from typing import Any
from urllib import error, request

from app.core.config import settings
from app.services.entity_extraction_service import EntityCandidate, EntityExtractionService


@dataclass(frozen=True)
class EntityValidationResult:
    accepted_candidates: list[EntityCandidate]
    rejected_count: int = 0
    llm_used: bool = False
    error_message: str | None = None


class EntityValidationService:
    """Validate rule-generated entity candidates with an optional LLM pass."""

    RESPONSE_SCHEMA: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "candidate_name": {"type": "string"},
                        "accepted": {"type": "boolean"},
                        "name": {"type": "string"},
                        "normalized_name": {"type": "string"},
                        "entity_type": {"type": "string"},
                        "definition": {"type": "string"},
                        "confidence": {"type": "number"},
                        "aliases": {"type": "array", "items": {"type": "string"}},
                        "rejection_reason": {"type": "string"},
                    },
                    "required": [
                        "candidate_name",
                        "accepted",
                        "name",
                        "normalized_name",
                        "entity_type",
                        "definition",
                        "confidence",
                        "aliases",
                        "rejection_reason",
                    ],
                },
            }
        },
        "required": ["entities"],
    }

    def __init__(self) -> None:
        self.enabled = settings.enable_llm_entity_validation
        self.provider = settings.llm_provider.lower()
        self.api_key = settings.openai_api_key
        self.model = settings.entity_validation_model or settings.llm_model
        self.base_url = settings.openai_base_url.rstrip("/")
        self.ollama_base_url = settings.ollama_base_url.rstrip("/")
        self.extractor = EntityExtractionService()

    def validate_candidates(
        self,
        candidates: list[EntityCandidate],
        context: str,
    ) -> EntityValidationResult:
        if not candidates:
            return EntityValidationResult(accepted_candidates=[])

        if not self.enabled:
            return EntityValidationResult(accepted_candidates=candidates)

        if not self.model:
            return EntityValidationResult(
                accepted_candidates=candidates,
                error_message="LLM entity validation is enabled, but ENTITY_VALIDATION_MODEL or LLM_MODEL is missing.",
            )

        if self.provider == "openai" and not self.api_key:
            return EntityValidationResult(
                accepted_candidates=candidates,
                error_message="LLM entity validation is enabled for OpenAI, but OPENAI_API_KEY is missing.",
            )

        try:
            accepted: list[EntityCandidate] = []
            rejected_count = 0
            batch_size = max(settings.entity_validation_batch_size, 1)
            for index in range(0, len(candidates), batch_size):
                candidate_batch = candidates[index : index + batch_size]
                prompt = self._build_prompt(candidate_batch, context)
                data = self._post_validation_request(prompt)
                accepted_batch = self._parse_response(data, candidate_batch)
                accepted.extend(accepted_batch)
                rejected_count += max(len(candidate_batch) - len(accepted_batch), 0)

            return EntityValidationResult(
                accepted_candidates=accepted,
                rejected_count=rejected_count,
                llm_used=True,
            )
        except Exception as exc:
            return EntityValidationResult(
                accepted_candidates=candidates,
                error_message=f"{type(exc).__name__}: {str(exc)}",
            )

    def _build_prompt(self, candidates: list[EntityCandidate], context: str) -> str:
        candidate_lines = [
            {
                "name": candidate.name,
                "normalized_name": candidate.normalized_name,
                "entity_type": candidate.entity_type,
                "confidence": candidate.confidence,
                "source": candidate.source,
                "snippet": candidate.snippet,
            }
            for candidate in candidates[: settings.entity_validation_batch_size]
        ]
        return (
            "Validate entity candidates extracted from an Android camera/ISP technical PDF. "
            "Accept only meaningful technical concepts. Reject document-format words, generic words, "
            "and incidental acronyms. Preserve source-grounded names and do not invent entities.\n\n"
            f"Return JSON matching this schema:\n{json.dumps(self.RESPONSE_SCHEMA)}\n\n"
            f"Context:\n{context[:4000]}\n\n"
            f"Candidates:\n{json.dumps(candidate_lines, ensure_ascii=False)}"
        )

    def _post_validation_request(self, prompt: str) -> dict[str, Any]:
        if self.provider == "ollama":
            return self._post_ollama_chat(self._build_ollama_payload(prompt))
        if self.provider == "openai":
            return self._post_openai_responses(self._build_openai_responses_payload(prompt))
        raise ValueError(f"Unsupported LLM_PROVIDER: {self.provider}")

    def _build_openai_responses_payload(self, prompt: str) -> dict[str, Any]:
        return {
            "model": self.model,
            "input": [
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt}],
                }
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "entity_validation_result",
                    "schema": self.RESPONSE_SCHEMA,
                    "strict": True,
                }
            },
        }

    def _build_ollama_payload(self, prompt: str) -> dict[str, Any]:
        return {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": self.RESPONSE_SCHEMA,
            "options": {"temperature": 0},
        }

    def _post_openai_responses(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/responses",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI Responses API error {exc.code}: {detail}") from exc

    def _post_ollama_chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.ollama_base_url}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=120) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama chat API error {exc.code}: {detail}") from exc

    def _parse_response(
        self,
        data: dict[str, Any],
        candidates: list[EntityCandidate],
    ) -> list[EntityCandidate]:
        by_name = {candidate.name: candidate for candidate in candidates}
        by_normalized = {candidate.normalized_name: candidate for candidate in candidates}
        content = self._extract_output_text(data)
        parsed = json.loads(content)

        accepted: list[EntityCandidate] = []
        for item in parsed.get("entities", []):
            if not item.get("accepted"):
                continue

            candidate = by_name.get(str(item.get("candidate_name", "")))
            if candidate is None:
                normalized_candidate = self.extractor.normalize_name(str(item.get("candidate_name", "")))
                candidate = by_normalized.get(normalized_candidate)
            if candidate is None:
                continue

            normalized_name = self.extractor.normalize_name(str(item.get("normalized_name") or item.get("name")))
            entity_type = str(item.get("entity_type") or candidate.entity_type)
            confidence = self._bounded_confidence(item.get("confidence"), candidate.confidence)
            accepted.append(
                candidate.with_validation(
                    name=str(item.get("name") or candidate.name),
                    normalized_name=normalized_name,
                    entity_type=entity_type,
                    confidence=confidence,
                    description=str(item.get("definition") or "") or None,
                    aliases=tuple(str(alias) for alias in item.get("aliases", []) if str(alias).strip()),
                )
            )

        return accepted

    def _extract_output_text(self, data: dict[str, Any]) -> str:
        if isinstance(data.get("output_text"), str):
            return data["output_text"]

        message = data.get("message")
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            return message["content"]

        for output_item in data.get("output", []):
            for content_item in output_item.get("content", []):
                if content_item.get("type") in {"output_text", "text"}:
                    text = content_item.get("text")
                    if isinstance(text, str):
                        return text

        raise ValueError("Response did not contain output text.")

    def _bounded_confidence(self, value: object, fallback: float) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            confidence = fallback
        return min(max(confidence, 0.0), 1.0)
