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


def render_sidebar():
    st.sidebar.header("Dataset History")
    try:
        r = requests.get(f"{API}/api/v1/datasets", timeout=5)
        if r.status_code != 200:
            st.sidebar.caption("Tidak dapat memuat history.")
            return
        datasets = r.json().get("data", [])
    except Exception:
        st.sidebar.caption("Tidak dapat memuat history.")
        return

    if not datasets:
        st.sidebar.caption("Belum ada dataset.")
        return

    for d in datasets:
        label = f"{d['name']}\n{d['total_images']} gambar"
        if st.sidebar.button(label, key=f"hist_{d['id']}", use_container_width=True):
            if st.session_state.get("audit_id") and not st.session_state.get("audit_polling_done"):
                st.sidebar.warning("Audit sedang berjalan.")
            else:
                for key in (
                    "audit_id", "audit_polling_done", "audit_final_status",
                    "audit_done_rows", "audit_cached_notice", "report_summary",
                    "report_results", "pdf_bytes", "report_audit_id_loaded",
                    "pdf_error", "auto_load_report",
                ):
                    st.session_state.pop(key, None)
                st.session_state["dataset_id"]           = d["id"]
                st.session_state["dataset_name"]         = d["name"]
                st.session_state["total_images"]         = d.get("total_images", 0)
                st.session_state["dataset_class_count"]  = d.get("class_count", 0)
                st.session_state["dataset_file_size_mb"] = d.get("file_size_mb", 0)
                st.session_state["upload_done"]          = True
                st.session_state["step"]                 = 2
                st.rerun()


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

    # Read-only mode: dataset sudah diupload — tidak boleh upload ulang di tengah flow
    if st.session_state.get("dataset_id"):
        st.success("Dataset sudah diupload.")
        if not st.session_state.get("audit_id"):
            st.caption("Untuk ganti dataset, klik Audit Dataset Baru di Step 3.")
        dataset_id = st.session_state.get("dataset_id", "-")
        name = st.session_state.get("dataset_name", "-")
        total = st.session_state.get("total_images", 0)
        classes = st.session_state.get("dataset_class_count", 0)
        size = st.session_state.get("dataset_file_size_mb", 0)
        st.markdown(
            f"**Dataset aktif:** {name}  \n"
            f"**ID:** `{dataset_id}`  \n"
            f"**Total gambar:** {total} | **Kelas:** {classes} | **Ukuran:** {size:.1f} MB"
        )
        if st.button("Lanjut ke Audit"):
            st.session_state["step"] = 2
            st.rerun()
        return

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
        # Bug 6: label berbeda untuk cached vs baru
        if d.get("cached"):
            st.info("Dataset ini sudah pernah diupload. Menggunakan data yang ada.")
        else:
            st.success("Upload berhasil.")
        st.markdown("**Dataset ID:**")
        st.code(d["dataset_id"], language=None)
        st.json(d, expanded=False)
        st.session_state["dataset_id"] = d["dataset_id"]
        st.session_state["dataset_name"] = d.get("name", "-")
        st.session_state["dataset_class_count"] = d.get("class_count", 0)
        st.session_state["dataset_file_size_mb"] = d.get("file_size_mb", 0)
        st.session_state["total_images"] = d.get("total_images", 0)
        st.session_state["upload_done"] = True

    # Bug 9: show button if dataset_id exists even when upload_done cleared
    if st.session_state.get("upload_done") or st.session_state.get("dataset_id"):
        if st.button("Lanjut ke Audit"):
            st.session_state["step"] = 2
            st.rerun()


def render_audit():
    # "Kembali ke Upload" hanya muncul setelah audit dibuat — sebelumnya tidak ada jalan balik
    if st.session_state.get("audit_id"):
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

        use_cache = st.checkbox("Gunakan hasil audit sebelumnya jika ada", value=True)
        if st.button("Buat Audit", disabled=not dataset_id):
            try:
                r = requests.post(
                    f"{API}/api/v1/audits",
                    json={"dataset_id": dataset_id, "force": not use_cache},
                    timeout=30,
                )
                r.raise_for_status()
                audit = r.json()["data"]
                st.session_state["audit_id"] = audit["id"]
                audit_id = audit["id"]
                # Bug 10: cached audit → set state lalu rerun agar render bersih
                if audit.get("cached"):
                    st.session_state["audit_polling_done"] = True
                    st.session_state["audit_final_status"] = "completed"
                    st.session_state["audit_cached_notice"] = True
                    st.rerun()
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

    # Bug 1 + 5: polling loop → st.rerun() setelah selesai, estimasi dikalibrasi
    if audit_id and not st.session_state.get("audit_polling_done"):
        placeholder = st.empty()
        progress_bar = st.empty()
        total_images = st.session_state.get("total_images", 0)
        # Bug 5: formula dikalibrasi ulang post-numpy (~0.005s per image)
        estimated_sec = max(30, total_images * 0.005) if total_images else None
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

            # Bug 8: cache final table rows agar static block tidak fetch API ulang
            st.session_state["audit_done_rows"] = rows
            st.session_state["audit_polling_done"] = True
            st.session_state["audit_final_status"] = status
            # Bug 1: rerun → static block render bersih di run berikutnya
            st.rerun()

        except requests.exceptions.RequestException as e:
            st.session_state["audit_polling_done"] = True
            st.session_state["audit_final_status"] = "failed"
            st.error(f"Koneksi terputus saat polling: {e}")
            st.rerun()

    # Static block — hanya aktif setelah polling selesai (Bug 1: render bersih)
    if st.session_state.get("audit_polling_done"):
        audit_id = st.session_state.get("audit_id", "")
        status = st.session_state.get("audit_final_status", "")

        # Bug 10: tampil notice jika hasil dari cache
        if st.session_state.get("audit_cached_notice"):
            st.info("Menggunakan hasil audit sebelumnya.")

        if audit_id:
            # Bug 8: gunakan cached rows, fallback fetch API hanya jika belum ada
            rows = st.session_state.get("audit_done_rows")
            if not rows:
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
                st.session_state["audit_done_rows"] = rows

            st.markdown(
                f"**Status audit:** {status.upper()}\n\n"
                "| No | Analyzer | Status |\n|---|---|---|\n" +
                "\n".join(rows)
            )

        if status == "completed":
            st.write("")
            st.success("Audit selesai.")
            if st.button("Lihat Laporan"):
                # Bug 4: set flag agar render_report auto-load
                st.session_state["auto_load_report"] = True
                st.session_state["step"] = 3
                st.rerun()
        elif status == "failed":
            st.error("Audit gagal.")
            if st.button("Coba Lagi", key="retry_audit_btn"):
                try:
                    r = requests.post(f"{API}/api/v1/audits/{audit_id}/retry", timeout=10)
                    r.raise_for_status()
                    st.session_state["audit_polling_done"] = False
                    st.session_state.pop("audit_final_status", None)
                    st.session_state.pop("audit_done_rows", None)
                    st.rerun()
                except requests.exceptions.HTTPError as e:
                    detail = ""
                    try:
                        detail = e.response.json().get("detail", e.response.text)
                    except Exception:
                        detail = str(e)
                    st.error(f"Gagal retry: {detail}")
                except requests.exceptions.RequestException as e:
                    st.error(f"Gagal retry: {e}")


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

    # Bug 4 + Bug 2: auto_load flag + already_loaded agar data tidak hilang saat klik tombol lain
    auto_load = st.session_state.pop("auto_load_report", False)
    already_loaded = (
        st.session_state.get("report_audit_id_loaded") == audit_id
        and audit_id
        and st.session_state.get("report_summary") is not None
    )

    if already_loaded:
        st.button("Muat Laporan", disabled=True, key="load_report_btn")
        should_load = False
    else:
        should_load = auto_load or st.button(
            "Muat Laporan", disabled=not audit_id, key="load_report_btn"
        )

    if should_load and audit_id:
        # Fetch summary
        try:
            r = requests.get(f"{API}/api/v1/reports/{audit_id}/summary", timeout=15)
            r.raise_for_status()
            st.session_state["report_summary"] = r.json()["data"]
            st.session_state["report_audit_id_loaded"] = audit_id
        except requests.exceptions.RequestException as e:
            st.error(f"Gagal mengambil laporan: {e}")

        # Fetch detail per-analyzer
        try:
            rr = requests.get(f"{API}/api/v1/reports/{audit_id}", timeout=15)
            rr.raise_for_status()
            st.session_state["report_results"] = rr.json()["data"].get("analysis_results", [])
        except requests.exceptions.RequestException:
            st.session_state["report_results"] = []

        # Bug 3: fetch PDF sekaligus saat load agar download_button langsung tersedia
        try:
            rpdf = requests.get(f"{API}/api/v1/reports/{audit_id}/pdf", timeout=30)
            if rpdf.status_code == 200:
                st.session_state["pdf_bytes"] = rpdf.content
                st.session_state["pdf_error"] = False
            else:
                st.session_state["pdf_bytes"] = None
                st.session_state["pdf_error"] = True
        except Exception:
            st.session_state["pdf_bytes"] = None
            st.session_state["pdf_error"] = True

    # Render dari session_state — persists saat klik tombol lain (Bug 2)
    s = st.session_state.get("report_summary")
    if s:
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

    st.divider()

    # Detail per-analyzer — selalu tampil jika sudah diload
    results = st.session_state.get("report_results")
    if results is not None:
        st.subheader("Detail Per-Analyzer")
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

    st.divider()

    # Bug 3: st.download_button langsung dari cached pdf_bytes — tidak butuh 2 klik
    if st.session_state.get("pdf_bytes"):
        st.download_button(
            label="Download PDF Report",
            data=st.session_state["pdf_bytes"],
            file_name=f"report_{audit_id[:8]}.pdf" if audit_id else "report.pdf",
            mime="application/pdf",
        )
    elif st.session_state.get("pdf_error"):
        st.caption("PDF tidak tersedia untuk laporan ini.")

    st.divider()

    if st.button("Audit Dataset Baru"):
        # Bug 7: full clear list termasuk semua key yang ditambahkan
        for key in (
            "dataset_id", "dataset_name", "dataset_class_count", "dataset_file_size_mb",
            "audit_id", "audit_polling_done", "audit_final_status",
            "upload_done", "total_images", "report_summary", "report_results",
            "pdf_bytes", "report_audit_id_loaded", "pdf_error", "audit_cached_notice",
            "audit_done_rows", "auto_load_report",
        ):
            st.session_state.pop(key, None)
        st.session_state["step"] = 1
        st.rerun()


# ── Main ───────────────────────────────────────────────────────────────────────
step = st.session_state.get("step", 1)
render_sidebar()
render_step_header(step)

if step == 1:
    render_upload()
elif step == 2:
    render_audit()
elif step == 3:
    render_report()
