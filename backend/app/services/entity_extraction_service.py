import re
from dataclasses import dataclass


@dataclass(frozen=True)
class EntityCandidate:
    name: str
    normalized_name: str
    entity_type: str
    confidence: float
    source: str
    snippet: str


class EntityExtractionService:
    KNOWN_TERMS: dict[str, tuple[str, float]] = {
        "IFE": ("ISP_BLOCK", 0.95),
        "BPS": ("ISP_BLOCK", 0.95),
        "IPE": ("ISP_BLOCK", 0.95),
        "CSID": ("ISP_BLOCK", 0.95),
        "VFE": ("ISP_BLOCK", 0.9),
        "RDI": ("FEATURE", 0.85),
        "ISP": ("ISP_BLOCK", 0.85),
        "HAL": ("CAMERA_HAL", 0.85),
        "Camera HAL": ("CAMERA_HAL", 0.95),
        "kernel": ("KERNEL_DRIVER", 0.8),
        "driver": ("KERNEL_DRIVER", 0.75),
        "debug": ("DEBUG_KEYWORD", 0.7),
        "log": ("DEBUG_KEYWORD", 0.65),
        "SOF": ("DEBUG_KEYWORD", 0.85),
    }

    CHIPSET_PATTERN = re.compile(r"\b(?:SM|SDM|MSM|QCM|QCS)\d{3,5}\b", re.IGNORECASE)
    CODE_FILE_PATTERN = re.compile(r"\b[A-Za-z0-9_./-]+\.(?:c|cc|cpp|h|hpp)\b")
    FUNCTION_PATTERN = re.compile(r"\b[a-z][a-z0-9]+(?:_[a-z0-9]+){2,}\b")
    ACRONYM_PATTERN = re.compile(r"\b[A-Z][A-Z0-9_]{2,}\b")

    def extract(self, text: str) -> list[EntityCandidate]:
        candidates: dict[str, EntityCandidate] = {}

        for term, (entity_type, confidence) in self.KNOWN_TERMS.items():
            flags = re.IGNORECASE if not term.isupper() else 0
            pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(term)}(?![A-Za-z0-9_])", flags)
            for match in pattern.finditer(text):
                self._add_candidate(
                    candidates,
                    name=match.group(0),
                    entity_type=entity_type,
                    confidence=confidence,
                    source="dictionary",
                    text=text,
                    start=match.start(),
                    end=match.end(),
                )

        for pattern, entity_type, confidence in [
            (self.CHIPSET_PATTERN, "CHIPSET", 0.8),
            (self.CODE_FILE_PATTERN, "CODE_FILE", 0.8),
            (self.FUNCTION_PATTERN, "FUNCTION", 0.65),
            (self.ACRONYM_PATTERN, "CANDIDATE_TERM", 0.55),
        ]:
            for match in pattern.finditer(text):
                self._add_candidate(
                    candidates,
                    name=match.group(0),
                    entity_type=entity_type,
                    confidence=confidence,
                    source="pattern",
                    text=text,
                    start=match.start(),
                    end=match.end(),
                )

        return sorted(candidates.values(), key=lambda candidate: candidate.normalized_name)

    def normalize_name(self, name: str) -> str:
        return re.sub(r"\s+", " ", name.strip()).upper()

    def _add_candidate(
        self,
        candidates: dict[str, EntityCandidate],
        name: str,
        entity_type: str,
        confidence: float,
        source: str,
        text: str,
        start: int,
        end: int,
    ) -> None:
        normalized_name = self.normalize_name(name)
        existing = candidates.get(normalized_name)
        if existing is not None and existing.confidence >= confidence:
            return

        candidates[normalized_name] = EntityCandidate(
            name=name,
            normalized_name=normalized_name,
            entity_type=entity_type,
            confidence=confidence,
            source=source,
            snippet=self._snippet(text, start, end),
        )

    def _snippet(self, text: str, start: int, end: int, context: int = 120) -> str:
        snippet_start = max(start - context, 0)
        snippet_end = min(end + context, len(text))
        return " ".join(text[snippet_start:snippet_end].split())

