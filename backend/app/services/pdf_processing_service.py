from collections.abc import Callable, Iterator
from dataclasses import dataclass
from multiprocessing import get_context
from multiprocessing.queues import Queue
from pathlib import Path
from queue import Empty
from time import perf_counter

import fitz

from app.core.config import settings


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str
    needs_ocr: bool
    extraction_seconds: float = 0.0
    extraction_status: str = "completed"
    extraction_error: str | None = None


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


class PdfPageExtractionTimeout(Exception):
    def __init__(self, page_number: int, timeout_seconds: float) -> None:
        super().__init__(f"PDF page {page_number} extraction exceeded {timeout_seconds:g} seconds.")
        self.page_number = page_number
        self.timeout_seconds = timeout_seconds


class PdfPageExtractionCanceled(Exception):
    def __init__(self, page_number: int) -> None:
        super().__init__(f"PDF page {page_number} extraction was canceled.")
        self.page_number = page_number


class PdfProcessingService:
    def __init__(
        self,
        chunk_size: int = 1600,
        chunk_overlap: int = 200,
        min_text_length_for_ocr: int = 20,
        text_extraction_mode: str | None = None,
        fallback_text_extraction_mode: str | None = None,
        page_timeout_seconds: float | None = None,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_text_length_for_ocr = min_text_length_for_ocr
        self.text_extraction_mode = text_extraction_mode or settings.pdf_text_extraction_mode
        self.fallback_text_extraction_mode = (
            settings.pdf_text_extraction_fallback_mode
            if fallback_text_extraction_mode is None
            else fallback_text_extraction_mode
        )
        self.page_timeout_seconds = (
            settings.pdf_page_extraction_timeout_seconds
            if page_timeout_seconds is None
            else page_timeout_seconds
        )

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

    def iter_pages(
        self,
        pdf_path: Path,
        before_page: Callable[[int], None] | None = None,
        skip_pages: set[int] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> Iterator[ExtractedPage]:
        with fitz.open(pdf_path) as document:
            page_count = document.page_count

        skipped_pages = skip_pages or set()
        for page_idx in range(1, page_count + 1):
            if page_idx in skipped_pages:
                continue
            if before_page is not None:
                before_page(page_idx)
            started_at = perf_counter()
            try:
                text = self._extract_page_text_with_fallback(
                    pdf_path,
                    page_idx,
                    cancel_check=cancel_check,
                ).strip()
                yield ExtractedPage(
                    page_number=page_idx,
                    text=text,
                    needs_ocr=len(text) < self.min_text_length_for_ocr,
                    extraction_seconds=perf_counter() - started_at,
                )
            except PdfPageExtractionTimeout as exc:
                yield ExtractedPage(
                    page_number=page_idx,
                    text="",
                    needs_ocr=True,
                    extraction_seconds=perf_counter() - started_at,
                    extraction_status="timeout",
                    extraction_error=str(exc),
                )
            except PdfPageExtractionCanceled:
                raise
            except Exception as exc:
                yield ExtractedPage(
                    page_number=page_idx,
                    text="",
                    needs_ocr=True,
                    extraction_seconds=perf_counter() - started_at,
                    extraction_status="failed",
                    extraction_error=f"{type(exc).__name__}: {exc}",
                )

    def _extract_page_text_with_fallback(
        self,
        pdf_path: Path,
        page_number: int,
        cancel_check: Callable[[], bool] | None = None,
    ) -> str:
        try:
            return self._extract_page_text_with_timeout(
                pdf_path,
                page_number,
                text_extraction_mode=self.text_extraction_mode,
                cancel_check=cancel_check,
            )
        except PdfPageExtractionCanceled:
            raise
        except Exception as primary_exc:
            fallback_mode = self.fallback_text_extraction_mode
            if not fallback_mode or fallback_mode == self.text_extraction_mode:
                raise

            try:
                return self._extract_page_text_with_timeout(
                    pdf_path,
                    page_number,
                    text_extraction_mode=fallback_mode,
                    cancel_check=cancel_check,
                )
            except PdfPageExtractionCanceled:
                raise
            except Exception as fallback_exc:
                raise RuntimeError(
                    f"primary {self.text_extraction_mode} extraction failed: {primary_exc}; "
                    f"fallback {fallback_mode} extraction failed: {fallback_exc}"
                ) from fallback_exc

    def _extract_page_text_with_timeout(
        self,
        pdf_path: Path,
        page_number: int,
        text_extraction_mode: str | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> str:
        extraction_mode = text_extraction_mode or self.text_extraction_mode
        if self.page_timeout_seconds <= 0:
            if cancel_check is not None and cancel_check():
                raise PdfPageExtractionCanceled(page_number)
            return _extract_page_text(str(pdf_path), page_number, extraction_mode)

        context = get_context("spawn")
        queue: Queue = context.Queue(maxsize=1)
        process = context.Process(
            target=_extract_page_text_worker,
            args=(str(pdf_path), page_number, extraction_mode, queue),
        )
        process.start()
        started_at = perf_counter()
        while process.is_alive():
            if cancel_check is not None and cancel_check():
                process.terminate()
                process.join()
                raise PdfPageExtractionCanceled(page_number)

            elapsed = perf_counter() - started_at
            remaining = self.page_timeout_seconds - elapsed
            if remaining <= 0:
                process.terminate()
                process.join()
                raise PdfPageExtractionTimeout(page_number, self.page_timeout_seconds)

            process.join(min(0.5, remaining))

        try:
            status, payload = queue.get_nowait()
        except Empty as exc:
            raise RuntimeError(f"PDF page {page_number} extraction worker exited without output.") from exc

        if status == "error":
            raise RuntimeError(f"PDF page {page_number} extraction failed: {payload}")

        return str(payload)

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


def _extract_page_text_worker(
    pdf_path: str,
    page_number: int,
    text_extraction_mode: str,
    queue: Queue,
) -> None:
    try:
        queue.put(("ok", _extract_page_text(pdf_path, page_number, text_extraction_mode)))
    except Exception as exc:
        queue.put(("error", f"{type(exc).__name__}: {exc}"))


def _extract_page_text(pdf_path: str, page_number: int, text_extraction_mode: str) -> str:
    with fitz.open(pdf_path) as document:
        page = document.load_page(page_number - 1)
        if text_extraction_mode == "blocks":
            blocks = page.get_text("blocks")
            text_blocks = [
                (block[1], block[0], block[4])
                for block in blocks
                if len(block) >= 7 and block[6] == 0 and str(block[4]).strip()
            ]
            text_blocks.sort(key=lambda block: (block[0], block[1]))
            return "\n".join(block[2].rstrip() for block in text_blocks)

        return page.get_text("text")
