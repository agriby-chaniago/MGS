import json
import logging
import os
import time
from datetime import datetime, timezone

import pika

from analyzers import get_analyzers
from analyzers.base import AnalysisResult as AnalysisResultData
from analyzers.base import BaseAnalyzer
from models.database import SessionLocal
from models.orm import AnalysisResult, AuditStatus
from services.minio_downloader import cleanup_tmp, download_dataset
from services.publisher import publish_analysis_result

logger = logging.getLogger(__name__)

RETRY_DELAYS = [5, 15, 30]


def run_with_retry(analyzer: BaseAnalyzer, dataset_path: str) -> AnalysisResultData:
    last_error = None
    for attempt, delay in enumerate(RETRY_DELAYS):
        try:
            return analyzer.analyze(dataset_path, config={})
        except Exception as e:
            last_error = e
            if attempt < len(RETRY_DELAYS) - 1:
                logger.warning(
                    f"[{analyzer.analyzer_type}] attempt {attempt + 1} failed: {e}. Retry in {delay}s"
                )
                time.sleep(delay)
    return AnalysisResultData(
        analyzer_type=analyzer.analyzer_type,
        status="failed",
        findings=[],
        summary={},
        metrics={},
        error_message=str(last_error),
    )


def process_message(ch, method, properties, body):
    db = SessionLocal()
    audit_id = None
    try:
        payload = json.loads(body)
        audit_id = payload["audit_id"]

        # Force retry: hapus semua result lama agar bisa diulang dari awal
        if payload.get("force"):
            db.query(AnalysisResult).filter(AnalysisResult.audit_id == audit_id).delete()
            db.commit()
            logger.info(f"[{audit_id}] Force retry: cleared existing results")

        # Idempotency: semua analyzer sudah ada result final?
        existing = db.query(AnalysisResult).filter(
            AnalysisResult.audit_id == audit_id,
            AnalysisResult.status.in_(["completed", "failed"]),
        ).count()
        if existing == len(payload["requested_analyzers"]):
            logger.info(f"[{audit_id}] Already processed, ack and skip")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # Status validation sebelum set processing
        audit = db.query(AuditStatus).filter(AuditStatus.id == audit_id).first()
        if not audit or audit.status != "queued":
            status_val = audit.status if audit else "not found"
            logger.warning(f"[{audit_id}] Unexpected status={status_val}, skip")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        local_path = download_dataset(payload["dataset_minio_path"], audit_id)

        audit.status = "processing"
        db.commit()

        # Filter to only the analyzers the tier/request actually asked for —
        # previously this field was read for the idempotency count above but
        # never used to filter, so all 5 always ran regardless of plan.
        requested = set(payload["requested_analyzers"])
        analyzers = [a for a in get_analyzers() if a.analyzer_type in requested]
        for i, analyzer in enumerate(analyzers):
            logger.info(f"[{audit_id}] Running {analyzer.analyzer_type} ({i+1}/{len(analyzers)})")
            started = datetime.now(timezone.utc)
            result = run_with_retry(analyzer, local_path)
            completed = datetime.now(timezone.utc)

            db.add(AnalysisResult(
                audit_id=audit_id,
                analyzer_type=result.analyzer_type,
                status=result.status,
                result_payload={
                    "findings": result.findings,
                    "summary": result.summary,
                    "metrics": result.metrics,
                },
                error_message=result.error_message,
                started_at=started,
                completed_at=completed,
            ))
            db.commit()

            publish_analysis_result({
                "audit_id": audit_id,
                "analyzer_type": result.analyzer_type,
                "status": result.status,
                "result_payload": {
                    "findings": result.findings,
                    "summary": result.summary,
                    "metrics": result.metrics,
                },
                "error_message": result.error_message,
                "completed_at": completed.isoformat(),
            })

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        db.rollback()
        logger.error(f"[{audit_id}] Consumer error: {e}", exc_info=True)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    finally:
        db.close()
        if audit_id:
            cleanup_tmp(f"/tmp/analysis_{audit_id}")


def start_consuming():
    while True:
        try:
            conn = pika.BlockingConnection(pika.ConnectionParameters(
                host=os.getenv("RABBITMQ_HOST", "rabbitmq"),
                port=int(os.getenv("RABBITMQ_PORT", "5672")),
                virtual_host=os.getenv("RABBITMQ_VHOST", "/"),
                credentials=pika.PlainCredentials(
                    os.getenv("RABBITMQ_USER", "guest"),
                    os.getenv("RABBITMQ_PASS", "guest"),
                ),
            ))
            ch = conn.channel()
            ch.queue_declare(queue="audit.jobs", durable=True)
            ch.basic_qos(prefetch_count=1)
            ch.basic_consume(queue="audit.jobs", on_message_callback=process_message)
            logger.info("Analysis consumer started, waiting for messages...")
            ch.start_consuming()
        except Exception as e:
            logger.error(f"Consumer connection lost: {e}. Reconnecting in 5s...")
            time.sleep(5)
