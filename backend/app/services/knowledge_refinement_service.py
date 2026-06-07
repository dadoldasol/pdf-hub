import json
from dataclasses import dataclass, field
from typing import Any
from urllib import error, request

from app.core.config import settings


@dataclass(frozen=True)
class KnowledgeCardRefinement:
    description: str
    summary: str
    features: list[str] = field(default_factory=list)
    implementation_locations: list[str] = field(default_factory=list)
    debug_keywords: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    accepted: bool = True
    confidence: float | None = None


class KnowledgeRefinementService:
    PROMPT_VERSION = "knowledge_refinement.v1"
    RESPONSE_SCHEMA: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "accepted": {"type": "boolean"},
            "description": {"type": "string"},
            "summary": {"type": "string"},
            "features": {"type": "array", "items": {"type": "string"}},
            "implementation_locations": {"type": "array", "items": {"type": "string"}},
            "debug_keywords": {"type": "array", "items": {"type": "string"}},
            "limitations": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number"},
            "rejection_reason": {"type": "string"},
        },
        "required": [
            "accepted",
            "description",
            "summary",
            "features",
            "implementation_locations",
            "debug_keywords",
            "limitations",
            "confidence",
            "rejection_reason",
        ],
    }

    def __init__(self) -> None:
        self.provider = settings.llm_provider.lower()
        self.api_key = settings.openai_api_key
        self.model = settings.entity_validation_model or settings.llm_model
        self.base_url = settings.openai_base_url.rstrip("/")
        self.ollama_base_url = settings.ollama_base_url.rstrip("/")

    def refine_entity(
        self,
        *,
        name: str,
        entity_type: str,
        snippets: list[str],
    ) -> KnowledgeCardRefinement:
        if not self.model:
            raise RuntimeError("ENTITY_VALIDATION_MODEL or LLM_MODEL is required for LLM refinement.")

        if self.provider == "openai" and not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAI LLM refinement.")

        prompt = self._build_prompt(name=name, entity_type=entity_type, snippets=snippets)
        data = self._post_refinement_request(prompt)
        return self._parse_response(data)

    def _build_prompt(self, *, name: str, entity_type: str, snippets: list[str]) -> str:
        evidence = [
            {"index": index + 1, "snippet": snippet}
            for index, snippet in enumerate(snippets[:12])
            if snippet.strip()
        ]
        return (
            "Refine a knowledge card for an entity extracted from an Android camera/ISP technical PDF. "
            "Use only the supplied evidence. Do not invent facts. If the entity is not a meaningful "
            "technical concept, set accepted=false and keep all descriptive fields empty.\n\n"
            f"Return JSON matching this schema:\n{json.dumps(self.RESPONSE_SCHEMA)}\n\n"
            f"Entity name: {name}\n"
            f"Entity type: {entity_type}\n\n"
            f"Evidence snippets:\n{json.dumps(evidence, ensure_ascii=False)}"
        )

    def _post_refinement_request(self, prompt: str) -> dict[str, Any]:
        if self.provider == "ollama":
            return self._post_ollama_chat(self._build_ollama_payload(prompt))
        if self.provider == "openai":
            return self._post_openai_responses(self._build_openai_responses_payload(prompt))
        raise ValueError(f"Unsupported LLM_PROVIDER: {self.provider}")

    def _build_ollama_payload(self, prompt: str) -> dict[str, Any]:
        return {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": self.RESPONSE_SCHEMA,
            "options": {"temperature": 0},
        }

    def _build_openai_responses_payload(self, prompt: str) -> dict[str, Any]:
        return {
            "model": self.model,
            "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "knowledge_card_refinement",
                    "schema": self.RESPONSE_SCHEMA,
                    "strict": True,
                }
            },
        }

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

    def _parse_response(self, data: dict[str, Any]) -> KnowledgeCardRefinement:
        content = self._extract_output_text(data)
        parsed = json.loads(content)
        return KnowledgeCardRefinement(
            accepted=bool(parsed.get("accepted")),
            description=str(parsed.get("description") or ""),
            summary=str(parsed.get("summary") or ""),
            features=self._string_list(parsed.get("features")),
            implementation_locations=self._string_list(parsed.get("implementation_locations")),
            debug_keywords=self._string_list(parsed.get("debug_keywords")),
            limitations=self._string_list(parsed.get("limitations")),
            confidence=self._bounded_confidence(parsed.get("confidence")),
        )

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

    def _string_list(self, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    def _bounded_confidence(self, value: object) -> float | None:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            return None
        return min(max(confidence, 0.0), 1.0)
