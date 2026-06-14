import os
import time
import threading

import requests
import streamlit as st

API = os.getenv("API_BASE_URL", "http://localhost")
ANALYZERS = ["corruption", "empty", "resolution", "distribution", "duplicate"]
KOMPONEN = {
    "I": ("Integrity (I)", "1 - corruption_rate", 0.30),
    "U": ("Uniqueness (U)", "1 - duplicate_rate (pHash)", 0.25),
    "D": ("Distribution (D)", "1 - gini_coefficient", 0.25),
    "Q": ("Resolution (Q)", "% gambar dalam ±1 sigma median", 0.20),
}

st.set_page_config(page_title="ModelGate", layout="wide")
st.title("ModelGate — CV Dataset Quality Audit")


def render_step_header(step):
    labels = {1: "1. Upload Dataset", 2: "2. Jalankan Audit", 3: "3. Laporan"}
    unlocked = {
        1: True,
        2: bool(st.session_state.get("dataset_id")),
        3: bool(st.session_state.get("audit_polling_done")),
    }

    cols = st.columns(3)
    for i, col in enumerate(cols, 1):
        label = labels[i]
        with col:
            if i == step:
                st.markdown(
                    f"<div style='text-align:center; font-weight:600; "
                    f"border-bottom: 2px solid #ff4b4b; padding-bottom:8px; "
                    f"color: #ff4b4b'>{label}</div>",
                    unsafe_allow_html=True,
                )
            elif unlocked[i]:
                if st.button(label, key=f"nav_step_{i}", use_container_width=True):
                    st.session_state["step"] = i
                    st.rerun()
            else:
                st.markdown(
                    f"<div style='text-align:center; color:#555; padding-bottom:8px'>{label}</div>",
                    unsafe_allow_html=True,
                )
    st.divider()


def upload_with_progress(file_bytes, filename, name):
    result = {"r": None, "err": None}

    def _req():
        try:
            result["r"] = requests.post(
                f"{API}/api/v1/datasets/upload",
                files={"file": (filename, file_bytes, "application/zip")},
                data={"name": name},
                timeout=600,
            )
        except Exception as e:
            result["err"] = e

    t = threading.Thread(target=_req, daemon=True)
    t.start()

    size_mb = len(file_bytes) / (1024 * 1024)
    estimated_sec = max(15, size_mb / 5)
    bar = st.progress(0.0, text="Mengupload dataset...")
    elapsed = 0.0
    while t.is_alive():
        pct = min(0.95, elapsed / estimated_sec)
        bar.progress(pct, text=f"Mengupload... {elapsed:.0f}s / estimasi {estimated_sec:.0f}s")
        time.sleep(0.5)
        elapsed += 0.5
    t.join()
    bar.progress(1.0, text="Upload selesai.")
    return result["r"], result["err"]


def render_upload():
    st.header("Upload Dataset ZIP")
    st.info(
        "Format ZIP: satu root folder berisi subfolder per kelas. "
        "Contoh: `dataset.zip/cats/`, `dataset.zip/dogs/`"
    )

    file = st.file_uploader("Pilih file ZIP", type=["zip"])

    if st.button("Upload", disabled=not file):
        name = os.path.splitext(file.name)[0]
        file_bytes = file.getvalue()

        r, err = upload_with_progress(file_bytes, file.name, name)

        if err is not None:
            st.error(f"Upload gagal: {err}")
            return

        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            detail = ""
            try:
                detail = r.json().get("detail", r.text)
            except Exception:
                detail = r.text
            st.error(f"Upload gagal: {detail}")
            return

        d = r.json()["data"]
        st.success("Upload berhasil.")
        st.markdown("**Dataset ID:**")
        st.code(d["dataset_id"], language=None)
        st.json(d)
        st.session_state["dataset_id"] = d["dataset_id"]
        st.session_state["total_images"] = d.get("total_images", 0)
        st.session_state["upload_done"] = True

    if st.session_state.get("upload_done"):
        if st.button("Lanjut ke Audit"):
            st.session_state["step"] = 2
            st.rerun()


def render_audit():
    col_back, _ = st.columns([1, 5])
    with col_back:
        if st.button("Kembali ke Upload"):
            st.session_state["step"] = 1
            st.rerun()

    st.header("Jalankan Audit")

    audit_id = st.session_state.get("audit_id")

    if not st.session_state.get("audit_polling_done") and not audit_id:
        dataset_id = st.text_input(
            "Dataset ID",
            value=st.session_state.get("dataset_id", ""),
            placeholder="Paste dataset_id dari step Upload",
        )

        if st.button("Buat Audit", disabled=not dataset_id):
            try:
                r = requests.post(
                    f"{API}/api/v1/audits",
                    json={"dataset_id": dataset_id},
                    timeout=30,
                )
                r.raise_for_status()
                audit = r.json()["data"]
                st.session_state["audit_id"] = audit["id"]
                audit_id = audit["id"]
                if audit.get("cached"):
                    st.info("Audit untuk dataset ini sudah ada. Menggunakan hasil sebelumnya.")
                    st.session_state["audit_polling_done"] = True
                    st.session_state["audit_final_status"] = "completed"
                else:
                    st.success("Audit dibuat. ID:")
                    st.code(audit["id"], language=None)
                    st.session_state["audit_polling_done"] = False
            except requests.exceptions.HTTPError as e:
                detail = ""
                try:
                    detail = e.response.json().get("detail", e.response.text)
                except Exception:
                    detail = str(e)
                st.error(f"Gagal membuat audit: {detail}")
                return
            except requests.exceptions.RequestException as e:
                st.error(f"Gagal membuat audit: {e}")
                return

    if audit_id and not st.session_state.get("audit_polling_done"):
        placeholder = st.empty()
        progress_bar = st.empty()
        result_box = st.empty()
        total_images = st.session_state.get("total_images", 0)
        estimated_sec = max(60, total_images * 0.04) if total_images else None
        try:
            start_time = time.time()
            while True:
                r = requests.get(f"{API}/api/v1/audits/{audit_id}", timeout=10)
                r.raise_for_status()
                status = r.json()["data"]["status"]

                done = {}
                try:
                    rr = requests.get(f"{API}/api/v1/reports/{audit_id}", timeout=10)
                    if rr.status_code == 200:
                        for res in rr.json()["data"].get("analysis_results", []):
                            done[res["analyzer_type"]] = res["status"]
                except Exception:
                    pass

                elapsed = int(time.time() - start_time)
                elapsed_str = f"{elapsed // 60}m {elapsed % 60}s" if elapsed >= 60 else f"{elapsed}s"

                if estimated_sec:
                    est_min = int(estimated_sec) // 60
                    est_sec = int(estimated_sec) % 60
                    est_str = f"{est_min}m {est_sec}s" if est_min > 0 else f"{est_sec}s"
                    pct = min(0.95, elapsed / estimated_sec)
                    time_info = f"waktu berjalan: {elapsed_str} / estimasi: ~{est_str}"
                else:
                    pct = None
                    time_info = f"waktu berjalan: {elapsed_str}"

                running_found = False
                rows = []
                for i, name in enumerate(ANALYZERS, 1):
                    if name in done:
                        label = "SELESAI" if done[name] == "completed" else "GAGAL"
                    elif status == "processing" and not running_found:
                        label = "BERJALAN"
                        running_found = True
                    else:
                        label = "MENUNGGU"
                    rows.append(f"| {i} | {name.upper()} | {label} |")

                placeholder.markdown(
                    f"**Status audit:** {status.upper()} — {time_info}\n\n"
                    "| No | Analyzer | Status |\n|---|---|---|\n" +
                    "\n".join(rows)
                )
                if pct is not None:
                    progress_bar.progress(pct, text=f"{pct*100:.0f}%")

                if status in ("completed", "failed"):
                    break
                time.sleep(1)

            st.session_state["audit_polling_done"] = True
            st.session_state["audit_final_status"] = status
            progress_bar.progress(1.0, text="100%")

            if status == "completed":
                result_box.success("Audit selesai.")
            else:
                result_box.error("Audit gagal. Periksa logs untuk detail.")

        except requests.exceptions.RequestException as e:
            st.session_state["audit_polling_done"] = True
            st.session_state["audit_final_status"] = "failed"
            st.error(f"Koneksi terputus saat polling: {e}")

    if st.session_state.get("audit_polling_done"):
        audit_id = st.session_state.get("audit_id", "")
        status = st.session_state.get("audit_final_status", "")

        if audit_id:
            placeholder = st.empty()
            done = {}
            try:
                rr = requests.get(f"{API}/api/v1/reports/{audit_id}", timeout=10)
                if rr.status_code == 200:
                    for res in rr.json()["data"].get("analysis_results", []):
                        done[res["analyzer_type"]] = res["status"]
            except Exception:
                pass

            rows = []
            for i, name in enumerate(ANALYZERS, 1):
                if name in done:
                    label = "SELESAI" if done[name] == "completed" else "GAGAL"
                else:
                    label = "MENUNGGU"
                rows.append(f"| {i} | {name.upper()} | {label} |")

            placeholder.markdown(
                f"**Status audit:** {status.upper()}\n\n"
                "| No | Analyzer | Status |\n|---|---|---|\n" +
                "\n".join(rows)
            )

        if status == "completed":
            st.success("Audit selesai.")
            if st.button("Lihat Laporan"):
                st.session_state["step"] = 3
                st.rerun()
        else:
            st.error("Audit gagal.")


def render_report():
    col_back, _ = st.columns([1, 5])
    with col_back:
        if st.button("Kembali ke Audit"):
            st.session_state["step"] = 2
            st.rerun()

    st.header("Laporan Audit")

    audit_id = st.text_input(
        "Audit ID",
        value=st.session_state.get("audit_id", ""),
        placeholder="Paste audit_id",
        key="report_audit_id",
    )

    if st.button("Muat Laporan", disabled=not audit_id):
        try:
            r = requests.get(f"{API}/api/v1/reports/{audit_id}/summary", timeout=15)
            r.raise_for_status()
            s = r.json()["data"]

            score = s.get("health_score")
            grade = s.get("grade", "-")

            st.subheader("Health Score")
            col1, col2 = st.columns([1, 3])
            col1.metric("Score", f"{score:.4f}" if score is not None else "-")
            col1.metric("Grade", grade)
            col1.metric("Status Audit", s.get("audit_status", "-").upper())

            if score is not None:
                col2.progress(float(score), text=f"{score * 100:.1f}%")
                if score >= 0.80:
                    st.success("LULUS — Health Score >= 0.80")
                else:
                    st.error("TIDAK LULUS — Health Score < 0.80")

            if s.get("components"):
                st.subheader("Komponen Health Score")
                c = s.get("components", {})
                for key, (label, desc, weight) in KOMPONEN.items():
                    val = float(c.get(key, 0))
                    col1, col2, col3 = st.columns([2, 5, 1])
                    col1.markdown(f"**{label}**  \n*bobot {int(weight * 100)}%*  \n{desc}")
                    col2.progress(val)
                    col3.markdown(f"**{val:.4f}**")

        except requests.exceptions.RequestException as e:
            st.error(f"Gagal mengambil laporan: {e}")

    st.divider()

    if st.button("Detail Per-Analyzer", disabled=not audit_id):
        try:
            r = requests.get(f"{API}/api/v1/reports/{audit_id}", timeout=15)
            r.raise_for_status()
            results = r.json()["data"].get("analysis_results", [])

            for res in results:
                status_label = "SELESAI" if res["status"] == "completed" else "GAGAL"
                with st.expander(f"[{status_label}] {res['analyzer_type'].upper()}"):
                    if res.get("result_payload"):
                        payload = res["result_payload"]
                        if payload.get("summary"):
                            st.subheader("Summary")
                            st.json(payload["summary"])
                        if payload.get("metrics"):
                            st.subheader("Metrics")
                            st.json(payload["metrics"])
                        if payload.get("findings"):
                            st.subheader(f"Findings ({len(payload['findings'])} items)")
                            st.json(payload["findings"][:20])
                    if res.get("error_message"):
                        st.error(res["error_message"])

        except requests.exceptions.RequestException as e:
            st.error(f"Gagal mengambil detail: {e}")

    st.divider()

    if st.button("Download PDF", disabled=not audit_id):
        try:
            r = requests.get(f"{API}/api/v1/reports/{audit_id}/pdf", timeout=30)
            r.raise_for_status()
            st.download_button(
                label="Klik untuk download PDF",
                data=r.content,
                file_name=f"report_{audit_id[:8]}.pdf",
                mime="application/pdf",
            )
        except requests.exceptions.RequestException as e:
            st.error(f"Gagal generate PDF: {e}")

    st.divider()

    if st.button("Audit Dataset Baru"):
        for key in ("dataset_id", "audit_id", "audit_polling_done", "audit_final_status", "upload_done"):
            st.session_state.pop(key, None)
        st.session_state["step"] = 1
        st.rerun()


# ── Main ───────────────────────────────────────────────────────────────────────
step = st.session_state.get("step", 1)
render_step_header(step)

if step == 1:
    render_upload()
elif step == 2:
    render_audit()
elif step == 3:
    render_report()
