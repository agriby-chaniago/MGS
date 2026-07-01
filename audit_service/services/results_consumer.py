import json
import logging
import os
import time

import pika

from models.database import SessionLocal
from models.orm import Audit, AnalysisResultReadOnly
from services.state_machine import transition
from services.ws_manager import broadcast_threadsafe

logger = logging.getLogger(__name__)


def process_result_message(ch, method, properties, body):
    db = SessionLocal()
    audit_id = None
    try:
        payload = json.loads(body)
        audit_id = payload["audit_id"]

        # New hook point (WebSocket workstream): broadcast this individual
        # analyzer's completion immediately, before the aggregate-status
        # checks below — this is what makes progress "live" per-analyzer
        # instead of only firing once at final completion.
        broadcast_threadsafe(audit_id, {
            "type": "analyzer_update",
            "analyzer_type": payload.get("analyzer_type"),
            "status": payload.get("status"),
        })

        audit = db.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            logger.warning(f"[{audit_id}] Audit not found, ack and skip")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # Idempotency: audit sudah terminal? Jangan re-transition (transition() akan raise ValueError)
        if audit.status in ("completed", "failed"):
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        total_analyzers = len(audit.requested_analyzers)  # JSONB → sudah list

        total_done = db.query(AnalysisResultReadOnly).filter(
            AnalysisResultReadOnly.audit_id == audit_id,
            AnalysisResultReadOnly.status.in_(["completed", "failed"]),
        ).count()

        if total_done < total_analyzers:
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        failed_count = db.query(AnalysisResultReadOnly).filter(
            AnalysisResultReadOnly.audit_id == audit_id,
            AnalysisResultReadOnly.status == "failed",
        ).count()

        if failed_count == 0:
            transition(audit, "completed", db)
        else:
            audit.error_message = f"{failed_count} analyzer(s) failed"
            transition(audit, "failed", db)

        db.commit()
        logger.info(f"[{audit_id}] Audit marked {audit.status}")
        broadcast_threadsafe(audit_id, {"type": "audit_completed", "status": audit.status})
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        db.rollback()
        logger.error(f"[{audit_id}] Results consumer error: {e}", exc_info=True)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    finally:
        db.close()


def start_results_consuming():
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
            ch.queue_declare(queue="analysis.results", durable=True)
            ch.basic_qos(prefetch_count=1)
            ch.basic_consume(queue="analysis.results", on_message_callback=process_result_message)
            logger.info("Audit results consumer started, waiting for messages...")
            ch.start_consuming()
        except Exception as e:
            logger.error(f"Results consumer connection lost: {e}. Reconnecting in 5s...")
            time.sleep(5)
