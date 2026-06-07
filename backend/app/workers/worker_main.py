import argparse
import os
import time
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.job import ProcessingJob
from app.workers.ingestion_worker import run_ingestion_job
from app.workers.refinement_worker import run_llm_refinement_job


def claim_next_queued_job(worker_id: str | None = None) -> UUID | None:
    """Claim one queued ingestion job so API requests never run long PDF work."""
    db = SessionLocal()
    try:
        job = db.scalar(
            select(ProcessingJob)
            .where(ProcessingJob.status == "queued")
            .order_by(ProcessingJob.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if job is None:
            db.rollback()
            return None

        metadata = dict(job.extra_metadata or {})
        metadata["worker_id"] = worker_id or default_worker_id()
        metadata["claimed_at"] = datetime.now(UTC).isoformat()
        metadata["stage"] = "claimed"
        job.extra_metadata = metadata
        job.status = "claimed"
        db.commit()
        return job.id
    finally:
        db.close()


def run_worker_once(worker_id: str | None = None) -> bool:
    job_id = claim_next_queued_job(worker_id)
    if job_id is None:
        return False

    if get_job_type(job_id) == "llm_refinement":
        run_llm_refinement_job(job_id)
    else:
        run_ingestion_job(job_id)
    return True


def get_job_type(job_id: UUID) -> str:
    db = SessionLocal()
    try:
        job = db.get(ProcessingJob, job_id)
        if job is None:
            return "ingestion"
        return str((job.extra_metadata or {}).get("job_type") or "ingestion")
    finally:
        db.close()


def run_worker_loop(
    *,
    worker_id: str | None = None,
    poll_interval_seconds: float | None = None,
) -> None:
    interval = settings.ingestion_worker_poll_interval_seconds
    if poll_interval_seconds is not None:
        interval = poll_interval_seconds

    while True:
        did_work = run_worker_once(worker_id)
        if not did_work:
            time.sleep(interval)


def default_worker_id() -> str:
    return f"pdf-hub-worker-{os.getpid()}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the PDF Knowledge Hub ingestion worker.")
    parser.add_argument("--once", action="store_true", help="Process at most one queued job and exit.")
    parser.add_argument("--worker-id", default=default_worker_id(), help="Identifier stored in job metadata.")
    args = parser.parse_args()

    if args.once:
        run_worker_once(args.worker_id)
        return

    run_worker_loop(worker_id=args.worker_id)


if __name__ == "__main__":
    main()
