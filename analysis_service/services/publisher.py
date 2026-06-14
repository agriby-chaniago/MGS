import json
import os
import pika


def publish_analysis_result(payload: dict):
    conn = pika.BlockingConnection(pika.ConnectionParameters(
        host=os.getenv("RABBITMQ_HOST", "rabbitmq"),
        port=int(os.getenv("RABBITMQ_PORT", "5672")),
        virtual_host=os.getenv("RABBITMQ_VHOST", "/"),
        credentials=pika.PlainCredentials(
            os.getenv("RABBITMQ_USER", "guest"),
            os.getenv("RABBITMQ_PASS", "guest"),
        ),
    ))
    try:
        ch = conn.channel()
        ch.queue_declare(queue="analysis.results", durable=True)
        ch.basic_publish(
            exchange="",
            routing_key="analysis.results",
            body=json.dumps(payload, default=str),
            properties=pika.BasicProperties(delivery_mode=2),
        )
    finally:
        conn.close()
