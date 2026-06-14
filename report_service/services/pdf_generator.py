from fpdf import FPDF


def generate_pdf(report: dict) -> bytes:
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "ModelGate - Dataset Audit Report", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Audit ID   : {report['audit_id']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Dataset ID : {report['dataset_id']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Status     : {report['audit_status']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Completed  : {report['completed_at'] or '-'}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    if report["health_score"] is not None:
        lulus = "LULUS" if report["health_score"] >= 0.80 else "TIDAK LULUS"
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(
            0, 10,
            f"Health Score: {report['health_score']:.4f}  Grade: {report['grade']}  ({lulus})",
            new_x="LMARGIN", new_y="NEXT",
        )
        pdf.set_font("Helvetica", "", 10)
        if report["components"]:
            comp = report["components"]
            pdf.cell(
                0, 6,
                f"  I={comp['I']}  U={comp['U']}  D={comp['D']}  Q={comp['Q']}",
                new_x="LMARGIN", new_y="NEXT",
            )
        pdf.ln(4)

    for result in report["analysis_results"]:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(
            0, 8,
            f"Analyzer: {result['analyzer_type'].upper()}  [{result['status'].upper()}]",
            new_x="LMARGIN", new_y="NEXT",
        )
        pdf.set_font("Helvetica", "", 9)
        if result["result_payload"]:
            summary = result["result_payload"].get("summary", {})
            for k, v in summary.items():
                if isinstance(v, dict):
                    continue
                pdf.cell(0, 5, f"  {k}: {v}", new_x="LMARGIN", new_y="NEXT")
        if result["error_message"]:
            pdf.cell(0, 5, f"  Error: {result['error_message']}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    return bytes(pdf.output())
