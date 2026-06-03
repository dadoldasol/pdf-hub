from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import fitz

from app.core.config import settings


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str
    needs_ocr: bool
    extraction_seconds: float = 0.0


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
        text_extraction_mode: str | None = None,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_text_length_for_ocr = min_text_length_for_ocr
        self.text_extraction_mode = text_extraction_mode or settings.pdf_text_extraction_mode

    def extract(self, pdf_path: Path) -> ExtractedPdf:
        pages: list[ExtractedPage] = []
        chunks: list[ExtractedChunk] = []
        chunk_index = 0

        for extracted_page in self.iter_pages(pdf_path):
            pages.append(extracted_page)
            for chunk_text in self.chunk_text(extracted_page.text):
                chunks.append(
                    ExtractedChunk(
                        chunk_index=chunk_index,
                        page_number=extracted_page.page_number,
                        text=chunk_text,
                    )
                )
                chunk_index += 1

        return ExtractedPdf(page_count=self.get_page_count(pdf_path), pages=pages, chunks=chunks)

    def get_page_count(self, pdf_path: Path) -> int:
        with fitz.open(pdf_path) as document:
            return document.page_count

    def iter_pages(self, pdf_path: Path, before_page: Callable[[int], None] | None = None) -> Iterator[ExtractedPage]:
        with fitz.open(pdf_path) as document:
            for page_idx, page in enumerate(document, start=1):
                if before_page is not None:
                    before_page(page_idx)
                started_at = perf_counter()
                text = self._extract_text(page).strip()
                yield ExtractedPage(
                    page_number=page_idx,
                    text=text,
                    needs_ocr=len(text) < self.min_text_length_for_ocr,
                    extraction_seconds=perf_counter() - started_at,
                )

    def _extract_text(self, page: fitz.Page) -> str:
        if self.text_extraction_mode == "blocks":
            blocks = page.get_text("blocks")
            text_blocks = [
                (block[1], block[0], block[4])
                for block in blocks
                if len(block) >= 7 and block[6] == 0 and str(block[4]).strip()
            ]
            text_blocks.sort(key=lambda block: (block[0], block[1]))
            return "\n".join(block[2].rstrip() for block in text_blocks)

        return page.get_text("text")

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
