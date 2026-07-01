#!/usr/bin/env python3
"""ModelGate CLI — programmatic access via API key (Pro/Max only).

Usage:
    mgs configure --key mg_live_... [--base-url http://localhost:8080]
    mgs run dataset.zip [--pdf]
    mgs upload dataset.zip
    mgs audit <dataset_id>
    mgs status <audit_id>
    mgs report <audit_id> [--pdf]
"""
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

import requests
import websockets

CONFIG_PATH = Path.home() / ".mgs" / "config.json"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        print("Belum configure. Jalankan: mgs configure --key <api_key>", file=sys.stderr)
        sys.exit(1)
    return json.loads(CONFIG_PATH.read_text())


def save_config(cfg: dict):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


def api_headers(cfg: dict) -> dict:
    return {"X-API-Key": cfg["api_key"]}


def _raise_for_status(resp: requests.Response):
    if not resp.ok:
        try:
            detail = resp.json().get("detail", resp.text)
        except ValueError:
            detail = resp.text
        print(f"Error {resp.status_code}: {detail}", file=sys.stderr)
        sys.exit(1)


def cmd_configure(args):
    save_config({"api_key": args.key, "base_url": args.base_url.rstrip("/")})
    print(f"Config tersimpan di {CONFIG_PATH}")


def cmd_upload(args) -> str:
    cfg = load_config()
    name = args.name or Path(args.path).stem
    with open(args.path, "rb") as f:
        resp = requests.post(
            f"{cfg['base_url']}/api/v1/datasets/upload",
            headers=api_headers(cfg),
            files={"file": (Path(args.path).name, f)},
            data={"name": name},
        )
    _raise_for_status(resp)
    data = resp.json()["data"]
    cached_note = " (cached, sudah pernah diupload)" if data.get("cached") else ""
    print(
        f"Dataset ID: {data['dataset_id']}{cached_note}  "
        f"({data['total_images']} gambar, {data['class_count']} kelas, {data['file_size_mb']}MB)"
    )
    return data["dataset_id"]


def cmd_audit(args) -> str:
    cfg = load_config()
    resp = requests.post(
        f"{cfg['base_url']}/api/v1/audits",
        headers=api_headers(cfg),
        json={"dataset_id": args.dataset_id, "force": args.force},
    )
    _raise_for_status(resp)
    data = resp.json()["data"]
    cached_note = " (cached, hasil sebelumnya)" if data.get("cached") else ""
    print(f"Audit ID: {data['id']}{cached_note}  (status: {data['status']})")
    return data["id"]


def cmd_status(args):
    cfg = load_config()
    resp = requests.get(f"{cfg['base_url']}/api/v1/audits/{args.audit_id}", headers=api_headers(cfg))
    _raise_for_status(resp)
    print(f"Status: {resp.json()['data']['status']}")


def _watch_progress_poll(cfg: dict, audit_id: str) -> str:
    print("Menunggu audit selesai (polling)...")
    while True:
        resp = requests.get(f"{cfg['base_url']}/api/v1/audits/{audit_id}", headers=api_headers(cfg))
        _raise_for_status(resp)
        status = resp.json()["data"]["status"]
        print(f"  [{status}]", end="\r")
        if status in ("completed", "failed"):
            print()
            return status
        time.sleep(1)


async def _watch_progress_ws(cfg: dict, audit_id: str) -> str:
    # Same live-progress channel the React frontend uses. Auth via ?token=
    # since this isn't a normal HTTP request with headers — the CLI's only
    # credential is an API key, which auth_service's /internal/verify tries
    # here alongside JWT (see auth_service/routers/internal.py comment).
    ws_url = cfg["base_url"].replace("http", "ws", 1) + f"/ws/audits/{audit_id}?token={cfg['api_key']}"
    print("Menunggu audit selesai (live)...")
    async with websockets.connect(ws_url) as ws:
        async for raw in ws:
            msg = json.loads(raw)
            if msg["type"] == "snapshot":
                # Sent immediately on connect — covers the audit already
                # finishing before this handshake completed (no replay).
                for analyzer, status in msg["analyzer_statuses"].items():
                    print(f"  [{analyzer}] {status}")
                if msg["audit_status"] in ("completed", "failed"):
                    return msg["audit_status"]
            elif msg["type"] == "analyzer_update":
                print(f"  [{msg['analyzer_type']}] {msg['status']}")
            elif msg["type"] == "audit_completed":
                return msg["status"]
    return "failed"  # connection closed without a final message


def _watch_progress(cfg: dict, audit_id: str) -> str:
    try:
        return asyncio.run(_watch_progress_ws(cfg, audit_id))
    except Exception as e:
        print(f"WebSocket gagal ({e}), fallback ke polling...", file=sys.stderr)
        return _watch_progress_poll(cfg, audit_id)


def cmd_report(args):
    cfg = load_config()
    resp = requests.get(f"{cfg['base_url']}/api/v1/reports/{args.audit_id}/summary", headers=api_headers(cfg))
    _raise_for_status(resp)
    print(json.dumps(resp.json()["data"], indent=2))

    if args.pdf:
        pdf_resp = requests.get(f"{cfg['base_url']}/api/v1/reports/{args.audit_id}/pdf", headers=api_headers(cfg))
        if pdf_resp.status_code == 403:
            print("PDF export hanya untuk paket Pro/Max.", file=sys.stderr)
            return
        _raise_for_status(pdf_resp)
        out_path = f"report_{args.audit_id}.pdf"
        Path(out_path).write_bytes(pdf_resp.content)
        print(f"PDF disimpan: {out_path}")


def cmd_run(args):
    """One-shot: upload -> audit -> watch -> report. The `mgs run <zip>` demo command."""
    cfg = load_config()
    dataset_id = cmd_upload(argparse.Namespace(path=args.path, name=args.name))
    audit_id = cmd_audit(argparse.Namespace(dataset_id=dataset_id, force=args.force))
    status = _watch_progress(cfg, audit_id)
    if status == "failed":
        print("Audit gagal.", file=sys.stderr)
        sys.exit(1)
    cmd_report(argparse.Namespace(audit_id=audit_id, pdf=args.pdf))


def main():
    parser = argparse.ArgumentParser(prog="mgs", description="ModelGate CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("configure", help="Simpan API key")
    p.add_argument("--key", required=True)
    p.add_argument("--base-url", default="http://localhost:8080")
    p.set_defaults(func=cmd_configure)

    p = sub.add_parser("upload", help="Upload dataset ZIP")
    p.add_argument("path")
    p.add_argument("--name", default=None)
    p.set_defaults(func=cmd_upload)

    p = sub.add_parser("audit", help="Buat audit dari dataset_id")
    p.add_argument("dataset_id")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser("status", help="Cek status audit")
    p.add_argument("audit_id")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("report", help="Ambil laporan/health score")
    p.add_argument("audit_id")
    p.add_argument("--pdf", action="store_true", help="Sekalian download PDF")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("run", help="One-shot: upload + audit + tunggu + laporan")
    p.add_argument("path")
    p.add_argument("--name", default=None)
    p.add_argument("--force", action="store_true")
    p.add_argument("--pdf", action="store_true")
    p.set_defaults(func=cmd_run)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
