import logging
import time
from datetime import datetime, timezone

from app import config
from app.database import SessionLocal
from app.models import Job
from app.services.renderer import run_render_job


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _claim_next_job(db):
    """Atomically claim the oldest queued render job."""
    job = (
        db.query(Job)
        .filter(Job.stage == "QUEUED", Job.status == "PENDING")
        .order_by(Job.created_at.asc())
        .with_for_update()
        .first()
    )
    if not job:
        return None
    job.status = "RUNNING"
    job.worker_id = config.WORKER_ID
    db.commit()
    db.refresh(job)
    return job


def _run_loop():
    while True:
        db = SessionLocal()
        try:
            job = _claim_next_job(db)
            if job:
                logger.info(
                    "%s: claimed job %s (project %s)",
                    config.WORKER_ID,
                    job.id,
                    job.project_id,
                )
                try:
                    run_render_job(db, job)
                    logger.info(
                        "%s: job %s finished with status %s",
                        config.WORKER_ID,
                        job.id,
                        job.status,
                    )
                except Exception as exc:
                    logger.exception("%s: job %s failed", config.WORKER_ID, job.id)
                    try:
                        job.status = "FAILED"
                        job.logs = str(exc)
                        db.commit()
                    except Exception:
                        pass
                continue
        except Exception:
            logger.exception("Worker poll error")
        finally:
            db.close()
        time.sleep(config.WORKER_POLL_INTERVAL)


def main():
    logger.info("Worker %s started", config.WORKER_ID)
    while True:
        try:
            _run_loop()
        except Exception:
            logger.exception("Worker crashed; restarting in 5s")
            time.sleep(5)


if __name__ == "__main__":
    main()
