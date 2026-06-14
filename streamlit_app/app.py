import os
import time

import requests
import streamlit as st

API = os.getenv("API_BASE_URL", "http://localhost")

st.set_page_config(page_title="ModelGate", layout="wide")
st.title("ModelGate — CV Dataset Quality Audit")

tab_upload, tab_audit, tab_report = st.tabs(["Upload Dataset", "Run Audit", "View Report"])

# ── Tab 1: Upload ──────────────────────────────────────────────────────────────
with tab_upload:
    st.header("Upload Dataset ZIP")
    st.info("Format ZIP: satu root folder berisi subfolder per kelas. Contoh: `dataset.zip/cats/`, `dataset.zip/dogs/`")

    file = st.file_uploader("Pilih file ZIP", type=["zip"])

    if st.button("Upload", disabled=not file):
        name = os.path.splitext(file.name)[0]
        try:
            with st.spinner("Mengupload dataset..."):
                r = requests.post(
                    f"{API}/api/v1/datasets/upload",
                    files={"file": (file.name, file.getvalue(), "application/zip")},
                    data={"name": name},
                    timeout=300,
                )
                r.raise_for_status()
            d = r.json()["data"]
            st.success(f"Upload berhasil!")
            st.code(d["dataset_id"], language=None)
            st.json(d)
            st.session_state["dataset_id"] = d["dataset_id"]
        except requests.exceptions.HTTPError as e:
            detail = ""
            try:
                detail = e.response.json().get("detail", e.response.text)
            except Exception:
                detail = str(e)
            st.error(f"Upload gagal: {detail}")
        except requests.exceptions.RequestException as e:
            st.error(f"Upload gagal: {e}")

# ── Tab 2: Audit ───────────────────────────────────────────────────────────────
with tab_audit:
    st.header("Run Audit")

    dataset_id = st.text_input(
        "Dataset ID",
        value=st.session_state.get("dataset_id", ""),
        placeholder="Paste dataset_id dari Tab Upload",
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
            st.success(f"Audit dibuat!")
            st.code(audit["id"], language=None)
            st.session_state["audit_id"] = audit["id"]
        except requests.exceptions.RequestException as e:
            st.error(f"Gagal membuat audit: {e}")

    st.divider()

    audit_id = st.text_input(
        "Audit ID (untuk poll status)",
        value=st.session_state.get("audit_id", ""),
        placeholder="Paste audit_id",
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Cek Status"):
            try:
                r = requests.get(f"{API}/api/v1/audits/{audit_id}", timeout=10)
                r.raise_for_status()
                a = r.json()["data"]
                status = a["status"]
                icon = {"completed": "🟢", "failed": "🔴", "processing": "🟡", "queued": "🟡"}.get(status, "⚪")
                st.metric("Status", f"{icon} {status.upper()}")
            except requests.exceptions.RequestException as e:
                st.error(f"Gagal cek status: {e}")

    with col2:
        if st.button("Auto-poll sampai selesai"):
            if not audit_id:
                st.warning("Isi Audit ID dulu")
            else:
                try:
                    status = None
                    with st.spinner("Menganalisis dataset... (bisa 10-60 detik)"):
                        while True:
                            r = requests.get(f"{API}/api/v1/audits/{audit_id}", timeout=10)
                            r.raise_for_status()
                            status = r.json()["data"]["status"]
                            if status in ("completed", "failed"):
                                break
                            time.sleep(3)

                    if status == "completed":
                        st.success("Audit selesai!")
                        st.session_state["audit_id"] = audit_id
                    else:
                        st.error("Audit gagal. Lihat logs untuk detail.")
                except requests.exceptions.RequestException as e:
                    st.error(f"Error saat polling: {e}")

# ── Tab 3: Report ──────────────────────────────────────────────────────────────
with tab_report:
    st.header("Report")

    audit_id_r = st.text_input(
        "Audit ID",
        value=st.session_state.get("audit_id", ""),
        placeholder="Paste audit_id",
        key="report_audit_id",
    )

    if st.button("Lihat Report"):
        try:
            r = requests.get(f"{API}/api/v1/reports/{audit_id_r}/summary", timeout=15)
            r.raise_for_status()
            s = r.json()["data"]

            score = s.get("health_score")
            grade = s.get("grade", "-")

            col1, col2, col3 = st.columns(3)
            col1.metric("Health Score", f"{score:.4f}" if score is not None else "-")
            col2.metric("Grade", grade)
            col3.metric("Status Audit", s.get("audit_status", "-").upper())

            if score is not None:
                if score >= 0.80:
                    st.success("✅ LULUS (Health Score ≥ 0.80)")
                else:
                    st.error("❌ TIDAK LULUS (Health Score < 0.80)")

            if s.get("components"):
                st.subheader("Komponen Health Score")
                c = s["components"]
                cols = st.columns(4)
                cols[0].metric("I — Integrity", c["I"], help="1 - corruption_rate")
                cols[1].metric("U — Uniqueness", c["U"], help="1 - duplicate_rate (pHash)")
                cols[2].metric("D — Distribution", c["D"], help="1 - gini_coefficient")
                cols[3].metric("Q — Resolution", c["Q"], help="% gambar dalam ±1σ median resolution")

        except requests.exceptions.RequestException as e:
            st.error(f"Gagal mengambil report: {e}")

    st.divider()

    if st.button("Lihat Detail Per-Analyzer"):
        try:
            r = requests.get(f"{API}/api/v1/reports/{audit_id_r}", timeout=15)
            r.raise_for_status()
            results = r.json()["data"].get("analysis_results", [])

            for res in results:
                status_icon = "✅" if res["status"] == "completed" else "❌"
                with st.expander(f"{status_icon} {res['analyzer_type'].upper()}"):
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

    if st.button("Download PDF Report"):
        try:
            r = requests.get(f"{API}/api/v1/reports/{audit_id_r}/pdf", timeout=30)
            r.raise_for_status()
            st.download_button(
                label="Klik untuk download PDF",
                data=r.content,
                file_name=f"report_{audit_id_r[:8]}.pdf",
                mime="application/pdf",
            )
        except requests.exceptions.RequestException as e:
            st.error(f"Gagal generate PDF: {e}")
