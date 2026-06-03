import hashlib
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings


class StorageService:
    def __init__(self, storage_dir: Path | None = None) -> None:
        self.storage_dir = storage_dir or settings.pdf_storage_dir

    async def save_upload(self, file: UploadFile) -> tuple[Path, int, str]:
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        suffix = Path(file.filename or "document.pdf").suffix or ".pdf"
        filename = f"{uuid.uuid4()}{suffix}"
        destination = self.storage_dir / filename

        size = 0
        digest = hashlib.sha256()
        with destination.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                digest.update(chunk)
                output.write(chunk)

        return destination, size, digest.hexdigest()

    def delete_file(self, path: Path) -> None:
        if path.exists() and path.is_file():
            path.unlink()
