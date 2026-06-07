from pathlib import Path

import fitz
import pytest

from app.services import pdf_processing_service
from app.services.pdf_processing_service import (
    PdfPageExtractionCanceled,
    PdfPageExtractionTimeout,
    PdfProcessingService,
)


def _write_pdf(path: Path, pages: list[str]) -> None:
    document = fitz.open()
    for text in pages:
        page = document.new_page()
        page.insert_text((72, 72), text)
    document.save(path)
    document.close()


def test_extract_pages_and_chunks(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    _write_pdf(pdf_path, ["IFE supports RDI path.", "CSID debugging uses SOF logs."])

    result = PdfProcessingService(chunk_size=100, page_timeout_seconds=0).extract(pdf_path)

    assert result.page_count == 2
    assert [page.page_number for page in result.pages] == [1, 2]
    assert result.pages[0].text == "IFE supports RDI path."
    assert result.pages[0].needs_ocr is False
    assert len(result.chunks) == 2
    assert result.chunks[0].page_number == 1


def test_short_empty_page_is_marked_for_ocr(tmp_path: Path) -> None:
    pdf_path = tmp_path / "empty.pdf"
    _write_pdf(pdf_path, [""])

    result = PdfProcessingService(page_timeout_seconds=0).extract(pdf_path)

    assert result.page_count == 1
    assert result.pages[0].needs_ocr is True
    assert result.chunks == []


def test_page_extraction_timeout_terminates_worker(monkeypatch, tmp_path: Path) -> None:
    class FakeQueue:
        def __init__(self, maxsize: int = 1) -> None:
            self.maxsize = maxsize

    class FakeProcess:
        terminated = False

        def __init__(self, target, args):  # noqa: ANN001
            self.target = target
            self.args = args

        def start(self) -> None:
            return None

        def join(self, timeout=None) -> None:  # noqa: ANN001
            return None

        def is_alive(self) -> bool:
            return True

        def terminate(self) -> None:
            FakeProcess.terminated = True

    class FakeContext:
        def Queue(self, maxsize: int = 1) -> FakeQueue:  # noqa: N802
            return FakeQueue(maxsize=maxsize)

        def Process(self, target, args):  # noqa: ANN001, N802
            return FakeProcess(target, args)

    monkeypatch.setattr(pdf_processing_service, "get_context", lambda method: FakeContext())
    service = PdfProcessingService(page_timeout_seconds=0.01)

    with pytest.raises(PdfPageExtractionTimeout):
        service._extract_page_text_with_timeout(tmp_path / "sample.pdf", 3)

    assert FakeProcess.terminated is True


def test_page_extraction_cancel_terminates_worker(monkeypatch, tmp_path: Path) -> None:
    class FakeQueue:
        def __init__(self, maxsize: int = 1) -> None:
            self.maxsize = maxsize

    class FakeProcess:
        terminated = False

        def __init__(self, target, args):  # noqa: ANN001
            self.target = target
            self.args = args

        def start(self) -> None:
            return None

        def join(self, timeout=None) -> None:  # noqa: ANN001
            return None

        def is_alive(self) -> bool:
            return True

        def terminate(self) -> None:
            FakeProcess.terminated = True

    class FakeContext:
        def Queue(self, maxsize: int = 1) -> FakeQueue:  # noqa: N802
            return FakeQueue(maxsize=maxsize)

        def Process(self, target, args):  # noqa: ANN001, N802
            return FakeProcess(target, args)

    monkeypatch.setattr(pdf_processing_service, "get_context", lambda method: FakeContext())
    service = PdfProcessingService(page_timeout_seconds=30)

    with pytest.raises(PdfPageExtractionCanceled):
        service._extract_page_text_with_timeout(
            tmp_path / "sample.pdf",
            3,
            cancel_check=lambda: True,
        )

    assert FakeProcess.terminated is True


def test_iter_pages_yields_timeout_page_record(monkeypatch, tmp_path: Path) -> None:
    pdf_path = tmp_path / "timeout.pdf"
    _write_pdf(pdf_path, ["page that will time out"])

    def fake_extract_page_text_with_timeout(  # noqa: ARG001
        self,
        pdf_path: Path,
        page_number: int,
        text_extraction_mode: str | None = None,
        cancel_check=None,
    ) -> str:
        raise PdfPageExtractionTimeout(page_number, 0.01)

    monkeypatch.setattr(
        PdfProcessingService,
        "_extract_page_text_with_timeout",
        fake_extract_page_text_with_timeout,
    )

    page = next(
        iter(
            PdfProcessingService(
                fallback_text_extraction_mode="",
                page_timeout_seconds=0.01,
            ).iter_pages(pdf_path)
        )
    )

    assert page.page_number == 1
    assert page.text == ""
    assert page.needs_ocr is True
    assert page.extraction_status == "timeout"
    assert "exceeded" in (page.extraction_error or "")


def test_iter_pages_uses_fallback_mode_after_primary_failure(monkeypatch, tmp_path: Path) -> None:
    pdf_path = tmp_path / "fallback.pdf"
    _write_pdf(pdf_path, ["fallback page"])
    modes: list[str | None] = []

    def fake_extract_page_text_with_timeout(  # noqa: ARG001
        self,
        pdf_path: Path,
        page_number: int,
        text_extraction_mode: str | None = None,
        cancel_check=None,
    ) -> str:
        modes.append(text_extraction_mode)
        if text_extraction_mode == "blocks":
            raise RuntimeError("blocks failed")
        return "fallback text"

    monkeypatch.setattr(
        PdfProcessingService,
        "_extract_page_text_with_timeout",
        fake_extract_page_text_with_timeout,
    )

    page = next(
        iter(
            PdfProcessingService(
                text_extraction_mode="blocks",
                fallback_text_extraction_mode="text",
                page_timeout_seconds=0.01,
            ).iter_pages(pdf_path)
        )
    )

    assert modes == ["blocks", "text"]
    assert page.text == "fallback text"
    assert page.extraction_status == "completed"


def test_iter_pages_skips_requested_pages(tmp_path: Path) -> None:
    pdf_path = tmp_path / "skip.pdf"
    _write_pdf(pdf_path, ["first", "second", "third"])

    pages = list(PdfProcessingService(page_timeout_seconds=0).iter_pages(pdf_path, skip_pages={1, 3}))

    assert [page.page_number for page in pages] == [2]
    assert pages[0].text == "second"


def test_chunk_text_always_advances_when_split_is_inside_overlap() -> None:
    service = PdfProcessingService(chunk_size=100, chunk_overlap=80, page_timeout_seconds=0)
    text = "short\n" + ("x" * 500)

    chunks = service.chunk_text(text)

    assert chunks
    assert "".join(chunk.replace("\n", "") for chunk in chunks).count("x") >= 500
    assert all(len(chunk) <= service.chunk_size for chunk in chunks)
