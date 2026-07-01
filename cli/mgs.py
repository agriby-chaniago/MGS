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
import os
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import requests

__version__ = "1.0.0"

CONFIG_PATH = Path.home() / ".mgs" / "config.json"

QUICK_START = """\
Belum pernah pakai mgs? Begini caranya:

  1. Buka ModelGate di browser (default: http://localhost:3000), login/daftar.
  2. Upgrade ke Pro/Max — panel "Upgrade" ada di sidebar (API key eksklusif Pro/Max).
  3. Klik "Generate API Key" di sidebar (panel di bawah Upgrade), salin key-nya (mg_live_...).
  4. mgs configure --key mg_live_...
  5. mgs run dataset.zip --pdf
"""

# Respect NO_COLOR (https://no-color.org) and non-TTY output (piping to a
# file/another program) — ANSI codes in a log file are just noise.
_USE_COLOR = sys.stdout.isatty() and "NO_COLOR" not in os.environ


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else text


def dim(text: str) -> str:
    return _c("2", text)


def bold(text: str) -> str:
    return _c("1", text)


def green(text: str) -> str:
    return _c("32", text)


def red(text: str) -> str:
    return _c("31", text)


def yellow(text: str) -> str:
    return _c("33", text)


def cyan(text: str) -> str:
    return _c("36", text)


def ok(msg: str):
    print(f"{green('✓')} {msg}")


def warn(msg: str):
    print(f"{yellow('!')} {msg}", file=sys.stderr)


def fail(msg: str):
    print(f"{red('✗')} {msg}", file=sys.stderr)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        print(QUICK_START, file=sys.stderr)
        sys.exit(1)
    return json.loads(CONFIG_PATH.read_text())


def save_config(cfg: dict):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


def api_headers(cfg: dict) -> dict:
    return {"X-API-Key": cfg["api_key"]}


@contextmanager
def api_call(action: str):
    # Wraps every network call so a down/unreachable server prints one
    # friendly line instead of a raw requests traceback ending the CLI.
    try:
        yield
    except requests.exceptions.ConnectionError:
        fail(f"Gagal {action}: server gak bisa dihubungi (cek base-url / server jalan gak).")
        sys.exit(1)
    except requests.exceptions.Timeout:
        fail(f"Gagal {action}: request timeout.")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        fail(f"Gagal {action}: {e}")
        sys.exit(1)


def _raise_for_status(resp: requests.Response):
    if not resp.ok:
        try:
            detail = resp.json().get("detail", resp.text)
        except ValueError:
            detail = resp.text
        fail(f"Error {resp.status_code}: {detail}")
        sys.exit(1)


@contextmanager
def spinner(message: str):
    # Nothing prints during a blocking `requests.post` otherwise — for a
    # large upload that can take a while, an idle terminal with zero
    # feedback is indistinguishable from a hang. Ticks every 200ms with
    # elapsed seconds so it's obvious something is actually happening.
    stop = threading.Event()

    def _spin():
        frames = "|/-\\"
        start = time.time()
        i = 0
        while not stop.is_set():
            elapsed = int(time.time() - start)
            print(f"\r{cyan(frames[i % len(frames)])} {message} {dim(f'({elapsed}s)')}", end="", flush=True)
            i += 1
            time.sleep(0.2)
        print("\r" + " " * (len(message) + 12) + "\r", end="", flush=True)

    t = threading.Thread(target=_spin, daemon=True)
    t.start()
    try:
        yield
    finally:
        stop.set()
        t.join()


def cmd_configure(args):
    cfg = {"api_key": args.key, "base_url": args.base_url.rstrip("/")}

    # Validate right away instead of silently saving a possibly-wrong key —
    # otherwise the first sign of trouble is a confusing 401 several
    # commands later, disconnected from the actual mistake (typo, expired
    # key, wrong --base-url).
    with api_call("memvalidasi API key"):
        resp = requests.get(f"{cfg['base_url']}/api/v1/datasets", headers=api_headers(cfg), timeout=10)
    if resp.status_code == 401:
        fail("API key gak valid — cek lagi key yang kamu paste (atau generate baru di website).")
        sys.exit(1)
    _raise_for_status(resp)

    save_config(cfg)
    ok(f"API key valid. Config tersimpan di {CONFIG_PATH}")
    print(dim("Coba: mgs run dataset.zip --pdf"))


def cmd_upload(args) -> str:
    cfg = load_config()
    path = Path(args.path)
    if not path.is_file():
        fail(f"File gak ketemu: {path}")
        sys.exit(1)

    name = args.name or path.stem
    size_mb = path.stat().st_size / (1024 * 1024)
    with api_call("upload"):
        with spinner(f"Mengunggah {path.name} ({size_mb:.1f}MB)"):
            with open(path, "rb") as f:
                resp = requests.post(
                    f"{cfg['base_url']}/api/v1/datasets/upload",
                    headers=api_headers(cfg),
                    files={"file": (path.name, f)},
                    data={"name": name},
                )
    _raise_for_status(resp)
    data = resp.json()["data"]
    cached_note = dim(" (cached, sudah pernah diupload)") if data.get("cached") else ""
    ok(
        f"Dataset ID: {bold(data['dataset_id'])}{cached_note}  "
        f"({data['total_images']} gambar, {data['class_count']} kelas, {data['file_size_mb']}MB)"
    )
    return data["dataset_id"]


def cmd_audit(args) -> str:
    cfg = load_config()
    with api_call("membuat audit"):
        resp = requests.post(
            f"{cfg['base_url']}/api/v1/audits",
            headers=api_headers(cfg),
            json={"dataset_id": args.dataset_id, "force": args.force},
        )
    _raise_for_status(resp)
    data = resp.json()["data"]
    cached_note = dim(" (cached, hasil sebelumnya)") if data.get("cached") else ""
    ok(f"Audit ID: {bold(data['id'])}{cached_note}  (status: {data['status']})")
    return data["id"]


def cmd_status(args):
    cfg = load_config()
    with api_call("cek status"):
        resp = requests.get(f"{cfg['base_url']}/api/v1/audits/{args.audit_id}", headers=api_headers(cfg))
    _raise_for_status(resp)
    print(f"Status: {bold(resp.json()['data']['status'])}")


def _watch_progress_poll(cfg: dict, audit_id: str) -> str:
    print(dim("Menunggu audit selesai (polling)..."))
    while True:
        with api_call("polling status"):
            resp = requests.get(f"{cfg['base_url']}/api/v1/audits/{audit_id}", headers=api_headers(cfg))
        _raise_for_status(resp)
        status = resp.json()["data"]["status"]
        print(f"  [{status}]", end="\r")
        if status in ("completed", "failed"):
            print()
            return status
        time.sleep(1)


async def _watch_progress_ws(cfg: dict, audit_id: str) -> str:
    # Lazy import: `websockets` is an optional dependency (cli/requirements.txt)
    # — if it's not installed, _watch_progress below falls back to polling
    # instead of crashing the whole CLI at import time.
    import websockets

    # Same live-progress channel the React frontend uses. Auth via ?token=
    # since this isn't a normal HTTP request with headers — the CLI's only
    # credential is an API key, which auth_service's /internal/verify tries
    # here alongside JWT (see auth_service/routers/internal.py comment).
    ws_url = cfg["base_url"].replace("http", "ws", 1) + f"/ws/audits/{audit_id}?token={cfg['api_key']}"
    print(dim("Menunggu audit selesai (live)..."))
    async with websockets.connect(ws_url) as ws:
        async for raw in ws:
            msg = json.loads(raw)
            if msg["type"] == "snapshot":
                # Sent immediately on connect — covers the audit already
                # finishing before this handshake completed (no replay).
                for analyzer, status in msg["analyzer_statuses"].items():
                    _print_analyzer_line(analyzer, status)
                if msg["audit_status"] in ("completed", "failed"):
                    return msg["audit_status"]
            elif msg["type"] == "analyzer_update":
                _print_analyzer_line(msg["analyzer_type"], msg["status"])
            elif msg["type"] == "audit_completed":
                return msg["status"]
    return "failed"  # connection closed without a final message


def _print_analyzer_line(analyzer: str, status: str):
    icon = green("✓") if status == "completed" else red("✗") if status == "failed" else yellow("…")
    print(f"  {icon} {analyzer}")


def _watch_progress(cfg: dict, audit_id: str) -> str:
    try:
        return asyncio.run(_watch_progress_ws(cfg, audit_id))
    except Exception as e:
        warn(f"WebSocket gagal ({e}), fallback ke polling...")
        return _watch_progress_poll(cfg, audit_id)


GRADE_COLOR = {"A": green, "B": cyan, "C": yellow, "D": yellow, "F": red}


def _print_summary(data: dict):
    score = data.get("health_score")
    grade = data.get("grade") or "-"
    colorize = GRADE_COLOR.get(grade, bold)
    print()
    print(f"  Health Score: {bold(f'{score:.4f}' if score is not None else '-')}   Grade: {colorize(bold(grade))}")
    components = data.get("components")
    if components:
        labels = {"I": "Integrity", "U": "Uniqueness", "D": "Distribution", "Q": "Quality"}
        for key, label in labels.items():
            val = components.get(key, 0)
            bar_len = 20
            filled = int(val * bar_len)
            bar = "█" * filled + dim("░" * (bar_len - filled))
            print(f"  {label:<13} {bar} {val:.2f}")
    print()


def cmd_report(args):
    cfg = load_config()
    with api_call("mengambil laporan"):
        resp = requests.get(f"{cfg['base_url']}/api/v1/reports/{args.audit_id}/summary", headers=api_headers(cfg))
    _raise_for_status(resp)
    _print_summary(resp.json()["data"])

    if args.pdf:
        with api_call("membuat PDF"):
            with spinner("Membuat PDF"):
                pdf_resp = requests.get(
                    f"{cfg['base_url']}/api/v1/reports/{args.audit_id}/pdf", headers=api_headers(cfg)
                )
        if pdf_resp.status_code == 403:
            warn("PDF export hanya untuk paket Pro/Max.")
            return
        _raise_for_status(pdf_resp)
        out_path = f"report_{args.audit_id}.pdf"
        Path(out_path).write_bytes(pdf_resp.content)
        ok(f"PDF disimpan: {bold(out_path)}")


def cmd_run(args):
    """One-shot: upload -> audit -> watch -> report. The `mgs run <zip>` demo command."""
    cfg = load_config()
    dataset_id = cmd_upload(argparse.Namespace(path=args.path, name=args.name))
    audit_id = cmd_audit(argparse.Namespace(dataset_id=dataset_id, force=args.force))
    status = _watch_progress(cfg, audit_id)
    if status == "failed":
        fail("Audit gagal.")
        sys.exit(1)
    cmd_report(argparse.Namespace(audit_id=audit_id, pdf=args.pdf))


def main():
    parser = argparse.ArgumentParser(
        prog="mgs",
        description="ModelGate CLI",
        epilog=QUICK_START,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"mgs {__version__}")
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
    try:
        args.func(args)
    except KeyboardInterrupt:
        print()
        warn("Dibatalkan.")
        sys.exit(130)


if __name__ == "__main__":
    main()
