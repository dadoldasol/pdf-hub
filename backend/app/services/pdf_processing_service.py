from dataclasses import dataclass
from pathlib import Path

import fitz


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str
    needs_ocr: bool


@dataclass(frozen=True)
class ExtractedChunk:
    chunk_index: int
    page_number: int
    text: str


@dataclass(frozen=True)
class ExtractedPdf:
    page_count: int
    pages: list[ExtractedPage]
    chunks: list[ExtractedChunk]


class PdfProcessingService:
    def __init__(
        self,
        chunk_size: int = 1600,
        chunk_overlap: int = 200,
        min_text_length_for_ocr: int = 20,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_text_length_for_ocr = min_text_length_for_ocr

    def extract(self, pdf_path: Path) -> ExtractedPdf:
        pages: list[ExtractedPage] = []
        chunks: list[ExtractedChunk] = []
        chunk_index = 0

        with fitz.open(pdf_path) as document:
            for page_idx, page in enumerate(document, start=1):
                text = page.get_text("text").strip()
                needs_ocr = len(text) < self.min_text_length_for_ocr
                extracted_page = ExtractedPage(
                    page_number=page_idx,
                    text=text,
                    needs_ocr=needs_ocr,
                )
                pages.append(extracted_page)

                for chunk_text in self.chunk_text(text):
                    chunks.append(
                        ExtractedChunk(
                            chunk_index=chunk_index,
                            page_number=page_idx,
                            text=chunk_text,
                        )
                    )
                    chunk_index += 1

            return ExtractedPdf(page_count=document.page_count, pages=pages, chunks=chunks)

    def chunk_text(self, text: str) -> list[str]:
        normalized = "\n".join(line.rstrip() for line in text.splitlines()).strip()
        if not normalized:
            return []

        if len(normalized) <= self.chunk_size:
            return [normalized]

        chunks: list[str] = []
        start = 0
        text_length = len(normalized)

        while start < text_length:
            end = min(start + self.chunk_size, text_length)
            if end < text_length:
                split_at = normalized.rfind("\n\n", start, end)
                if split_at == -1 or split_at <= start:
                    split_at = normalized.rfind("\n", start, end)
                if split_at == -1 or split_at <= start:
                    split_at = normalized.rfind(" ", start, end)
                if split_at > start:
                    end = split_at

            chunk = normalized[start:end].strip()
            if chunk:
                chunks.append(chunk)

            if end >= text_length:
                break

            start = max(end - self.chunk_overlap, 0)

        return chunks

