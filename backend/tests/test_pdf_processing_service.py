from pathlib import Path

import fitz

from app.services.pdf_processing_service import PdfProcessingService


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

    result = PdfProcessingService(chunk_size=100).extract(pdf_path)

    assert result.page_count == 2
    assert [page.page_number for page in result.pages] == [1, 2]
    assert result.pages[0].text == "IFE supports RDI path."
    assert result.pages[0].needs_ocr is False
    assert len(result.chunks) == 2
    assert result.chunks[0].page_number == 1


def test_short_empty_page_is_marked_for_ocr(tmp_path: Path) -> None:
    pdf_path = tmp_path / "empty.pdf"
    _write_pdf(pdf_path, [""])

    result = PdfProcessingService().extract(pdf_path)

    assert result.page_count == 1
    assert result.pages[0].needs_ocr is True
    assert result.chunks == []

