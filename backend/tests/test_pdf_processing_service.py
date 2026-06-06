from pathlib import Path

import fitz
import pytest

from app.services import pdf_processing_service
from app.services.pdf_processing_service import PdfPageExtractionTimeout, PdfProcessingService


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
