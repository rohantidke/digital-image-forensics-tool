import io
import base64
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def _b64_to_rl_image(b64_str: str, target_width: float, target_height: float):
    """Helper to convert a data:image base64 string to a ReportLab RLImage."""
    try:
        if "," in b64_str:
            b64_str = b64_str.split(",", 1)[1]
        data = base64.b64decode(b64_str)
        buf = io.BytesIO(data)
        return RLImage(buf, width=target_width, height=target_height)
    except Exception:
        return None

def generate_pdf_report(analysis_result: dict, case_id: str = None, examiner: str = "Digital Forensics Unit") -> bytes:
    """
    Generate an official Digital Image Forensic Examination Report in PDF format.
    Includes evidence hashes, tampering probability index, visual forensic plates,
    metadata findings, and formal examiner sign-off.
    """
    if not case_id:
        case_id = f"CASE-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    meta = analysis_result.get("metadata", {})
    score = analysis_result.get("scoring", {})
    ela = analysis_result.get("ela", {})
    copymove = analysis_result.get("copy_move", {})
    noise = analysis_result.get("noise", {})
    freq = analysis_result.get("frequency", {})
    lum = analysis_result.get("luminance", {})
    stego = analysis_result.get("stego", {})
    carve = analysis_result.get("carving", {})

    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        alignment=1 # Center
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#64748b"),
        alignment=1 # Center
    )

    heading2_style = ParagraphStyle(
        "SecHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=10,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#334155")
    )

    bold_body = ParagraphStyle(
        "ReportBodyBold",
        parent=body_style,
        fontName="Helvetica-Bold"
    )

    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1e293b")
    )

    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=table_cell,
        fontName="Helvetica-Bold"
    )

    elements = []

    # 1. Header Banner
    elements.append(Paragraph("DIGITAL FORENSIC EXAMINATION REPORT", title_style))
    elements.append(Paragraph("VERIPIX ADVANCED IMAGE AUTHENTICITY & TAMPERING ANALYSIS", subtitle_style))
    elements.append(Spacer(1, 10))

    # Case Metadata Box
    case_info_data = [
        [
            Paragraph(f"<b>Case Reference:</b> {case_id}", table_cell),
            Paragraph(f"<b>Date of Examination:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}", table_cell)
        ],
        [
            Paragraph(f"<b>Lead Examiner:</b> {examiner}", table_cell),
            Paragraph("<b>Classification:</b> FORENSIC EVIDENCE REPORT", table_cell)
        ]
    ]
    case_table = Table(case_info_data, colWidths=[270, 270])
    case_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(case_table)
    elements.append(Spacer(1, 10))

    # 2. Evidence Cryptographic Integrity & File Metadata
    elements.append(Paragraph("1. EVIDENCE RECORD & INTEGRITY HASHES", heading2_style))
    hashes = meta.get("hashes", {})
    evidence_data = [
        [Paragraph("File Name", table_cell_bold), Paragraph(str(meta.get("filename", "Unknown")), table_cell)],
        [Paragraph("File Format & Size", table_cell_bold), Paragraph(f"{meta.get('format')} | {meta.get('file_size_formatted')} ({meta.get('file_size_bytes')} bytes)", table_cell)],
        [Paragraph("Dimensions & Megapixels", table_cell_bold), Paragraph(f"{meta.get('dimensions', [0,0])[0]} x {meta.get('dimensions', [0,0])[1]} px ({meta.get('megapixels')} MP) | Mode: {meta.get('color_mode')}", table_cell)],
        [Paragraph("Perceptual Hash (dHash)", table_cell_bold), Paragraph(f"<code>{analysis_result.get('properties', {}).get('perceptual_hash', 'N/A')}</code>", table_cell)],
        [Paragraph("MD5 Hash", table_cell_bold), Paragraph(f"<code>{hashes.get('md5', 'N/A')}</code>", table_cell)],
        [Paragraph("SHA-1 Hash", table_cell_bold), Paragraph(f"<code>{hashes.get('sha1', 'N/A')}</code>", table_cell)],
        [Paragraph("SHA-256 Hash", table_cell_bold), Paragraph(f"<code>{hashes.get('sha256', 'N/A')}</code>", table_cell)],
    ]
    ev_table = Table(evidence_data, colWidths=[160, 380])
    ev_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(ev_table)
    elements.append(Spacer(1, 10))

    # 3. Executive Verdict & Risk Score
    elements.append(Paragraph("2. EXECUTIVE FORENSIC VERDICT", heading2_style))
    score_val = score.get("tamper_score", 0)
    verdict_text = score.get("verdict", "UNKNOWN")
    risk_level = score.get("risk_level", "Medium")

    v_bg = "#fee2e2" if score_val >= 55 else ("#fef3c7" if score_val >= 25 else "#dcfce7")
    v_border = "#ef4444" if score_val >= 55 else ("#f59e0b" if score_val >= 25 else "#10b981")
    v_text_color = "#991b1b" if score_val >= 55 else ("#92400e" if score_val >= 25 else "#166534")

    verdict_data = [
        [
            Paragraph(f"<font color='{v_text_color}'><b>VERDICT: {verdict_text}</b></font>", ParagraphStyle("V1", fontName="Helvetica-Bold", fontSize=13, alignment=1)),
            Paragraph(f"<font color='{v_text_color}'><b>TAMPER RISK: {score_val}% ({risk_level} Risk)</b></font>", ParagraphStyle("V2", fontName="Helvetica-Bold", fontSize=13, alignment=1))
        ],
        [
            Paragraph(f"<b>Investigator Note:</b> {score.get('recommendation')}", table_cell),
            Paragraph(f"<b>Key Findings:</b><br/>• " + "<br/>• ".join(score.get("evidence_summary", [])[:4]), table_cell)
        ]
    ]
    verdict_table = Table(verdict_data, colWidths=[270, 270])
    verdict_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(v_bg)),
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor(v_border)),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor(v_border)),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(verdict_table)
    elements.append(Spacer(1, 10))

    # 4. Forensic Analysis Modules Summary Table
    elements.append(Paragraph("3. MULTI-FACTOR FORENSIC AUDIT MATRIX", heading2_style))
    matrix_data = [
        [Paragraph("Forensic Test Module", table_cell_bold), Paragraph("Observed Status", table_cell_bold), Paragraph("Quantitative Forensic Metric", table_cell_bold)]
    ]

    # Row 1: EXIF
    sw = meta.get("software_detected")
    matrix_data.append([
        Paragraph("Metadata & EXIF Integrity", table_cell),
        Paragraph(f"<font color='red'>Software Flagged</font>" if sw else "<font color='green'>Consistent</font>", table_cell),
        Paragraph(f"Editing tool: {sw}" if sw else f"EXIF tags: {len(meta.get('exif', {}))}, GPS: {'Yes' if meta.get('gps') else 'No'}", table_cell)
    ])

    # Row 2: ELA
    ela_sig = ela.get("has_tamper_signature")
    matrix_data.append([
        Paragraph("Error Level Analysis (ELA)", table_cell),
        Paragraph("<font color='red'>Anomalous</font>" if ela_sig else "<font color='green'>Homogeneous</font>", table_cell),
        Paragraph(f"Mean Err: {ela.get('mean_error')} | Std: {ela.get('std_deviation')} | {ela.get('suspicious_region_count')} anomaly zone(s)", table_cell)
    ])

    # Row 3: Copy-Move
    cm_found = copymove.get("forgery_detected")
    matrix_data.append([
        Paragraph("Copy-Move Clone Detection", table_cell),
        Paragraph("<font color='red'>Clone Detected</font>" if cm_found else "<font color='green'>Clean</font>", table_cell),
        Paragraph(f"{copymove.get('clone_clusters_count')} clone cluster(s) | {copymove.get('matched_pairs_count')} spatial pairs", table_cell)
    ])

    # Row 4: Noise
    n_incon = noise.get("is_noise_inconsistent")
    matrix_data.append([
        Paragraph("Sensor Noise Consistency", table_cell),
        Paragraph("<font color='red'>Disparate</font>" if n_incon else "<font color='green'>Uniform</font>", table_cell),
        Paragraph(f"Noise CV: {noise.get('coefficient_of_variation')} | {noise.get('abnormal_block_percentage')}% abnormal blocks", table_cell)
    ])

    # Row 5: 2D FFT
    freq_art = freq.get("has_periodic_artifacts")
    matrix_data.append([
        Paragraph("Frequency Domain (2D FFT)", table_cell),
        Paragraph("<font color='red'>Periodic Spikes</font>" if freq_art else "<font color='green'>Natural Decay</font>", table_cell),
        Paragraph(f"High-Freq Energy: {freq.get('high_frequency_energy_pct')}% | {freq.get('periodic_peaks_detected')} harmonic peaks", table_cell)
    ])

    # Row 6: Carving & EOF
    eof_pay = carve.get("has_eof_payload")
    matrix_data.append([
        Paragraph("File Carving & EOF Markers", table_cell),
        Paragraph("<font color='red'>Payload Hidden</font>" if eof_pay else "<font color='green'>Standard EOF</font>", table_cell),
        Paragraph(f"Trailing: {carve.get('trailing_payload_bytes')} bytes | Type: {carve.get('detected_payload_type') or 'None'}", table_cell)
    ])

    # Row 7: Steganography LSB
    stego_det = stego.get("is_stego_detected")
    matrix_data.append([
        Paragraph("Steganography (LSB / PoV)", table_cell),
        Paragraph("<font color='red'>Payload Indicated</font>" if stego_det else "<font color='green'>Baseline Noise</font>", table_cell),
        Paragraph(f"LSB Entropy: {stego.get('avg_lsb_entropy')} | Stego Prob: {stego.get('chi_square_tests', {}).get('average_stego_probability', 0)}%", table_cell)
    ])

    matrix_table = Table(matrix_data, colWidths=[150, 110, 280])
    matrix_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(matrix_table)
    elements.append(Spacer(1, 12))

    # Page Break for Visual Evidence Plates
    elements.append(PageBreak())

    # 5. Visual Evidence Plates
    elements.append(Paragraph("4. FORENSIC VISUAL EVIDENCE EXHIBITS", heading2_style))
    elements.append(Paragraph("Side-by-side comparative examination plates generated by the forensic engine:", body_style))
    elements.append(Spacer(1, 8))

    # Plate 1: ELA and Heatmap
    plate1_data = []
    img_w, img_h = 250, 160

    img_orig = _b64_to_rl_image(analysis_result.get("original_image_base64", ""), img_w, img_h)
    img_ela = _b64_to_rl_image(ela.get("ela_image_base64", ""), img_w, img_h)
    img_heat = _b64_to_rl_image(ela.get("heatmap_image_base64", ""), img_w, img_h)
    img_cm = _b64_to_rl_image(copymove.get("annotated_image_base64", ""), img_w, img_h)
    img_noise = _b64_to_rl_image(noise.get("noise_heatmap_base64", ""), img_w, img_h)
    img_fft = _b64_to_rl_image(freq.get("spectrum_image_base64", ""), img_w, img_h)

    # First row of plates: Original vs ELA Heatmap
    row1 = [
        [img_orig if img_orig else Paragraph("Image Unavailable", table_cell),
         img_heat if img_heat else Paragraph("ELA Heatmap Unavailable", table_cell)],
        [Paragraph("<b>Exhibit A: Original Suspect Evidence</b>", table_cell_bold),
         Paragraph("<b>Exhibit B: Error Level Analysis (ELA Heatmap)</b>", table_cell_bold)]
    ]
    t_row1 = Table(row1, colWidths=[270, 270])
    t_row1.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(t_row1)
    elements.append(Spacer(1, 10))

    # Second row of plates: Copy-Move Detection vs Noise Residual
    row2 = [
        [img_cm if img_cm else Paragraph("Copy-Move Plot Unavailable", table_cell),
         img_noise if img_noise else Paragraph("Noise Residual Unavailable", table_cell)],
        [Paragraph("<b>Exhibit C: Copy-Move Cloning Keypoint Vectors</b>", table_cell_bold),
         Paragraph("<b>Exhibit D: Spatial Noise Variance Heatmap</b>", table_cell_bold)]
    ]
    t_row2 = Table(row2, colWidths=[270, 270])
    t_row2.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(t_row2)
    elements.append(Spacer(1, 10))

    # Third row of plates: 2D FFT Spectrum vs Luminance
    img_lum = _b64_to_rl_image(lum.get("gradient_image_base64", ""), img_w, img_h)
    row3 = [
        [img_fft if img_fft else Paragraph("2D FFT Spectrum Unavailable", table_cell),
         img_lum if img_lum else Paragraph("Luminance Vector Field Unavailable", table_cell)],
        [Paragraph("<b>Exhibit E: 2D FFT Magnitude Spectrum (Harmonics)</b>", table_cell_bold),
         Paragraph("<b>Exhibit F: Luminance Gradient & Lighting Vectors</b>", table_cell_bold)]
    ]
    t_row3 = Table(row3, colWidths=[270, 270])
    t_row3.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(t_row3)
    elements.append(Spacer(1, 12))

    # 6. Carving & Forensic Examiner Attestation
    elements.append(Paragraph("5. EXAMINER ATTESTATION & CHAIN OF CUSTODY", heading2_style))
    attestation_text = (
        "I hereby certify that the digital forensic examinations detailed in this report were conducted using "
        "reproducible, scientifically verified algorithms conforming to digital evidence integrity standards. "
        "The cryptographic hashes documented herein uniquely identify the analyzed digital specimen."
    )
    elements.append(Paragraph(attestation_text, body_style))
    elements.append(Spacer(1, 8))

    disclaimer_text = (
        "<b>Forensic Methodological Disclaimer:</b> Digital image forensic analysis evaluates algorithmic heuristics, "
        "compression artifacts, and statistical properties. In accordance with ISO/IEC 27037 standards, algorithmic "
        "findings represent observed anomalies rather than definitive legal conclusions. Absence of camera metadata "
        "or localized compression differences does not conclusively establish intentional malicious manipulation."
    )
    elements.append(Paragraph(disclaimer_text, ParagraphStyle("Disc", parent=body_style, fontSize=7.5, leading=9.5, textColor=colors.HexColor("#64748b"))))
    elements.append(Spacer(1, 12))

    sign_data = [
        [
            Paragraph("<b>Forensic Examiner Signature:</b><br/><br/>________________________________________<br/>Senior Digital Forensic Analyst", table_cell),
            Paragraph(f"<b>Laboratory Seal / Verification:</b><br/><br/>VERIPIX ENGINE v1.0.0<br/>Verification Token: {hashes.get('sha256', '')[:16].upper()}", table_cell)
        ]
    ]
    sign_table = Table(sign_data, colWidths=[270, 270])
    sign_table.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(sign_table)

    # Build PDF
    doc.build(elements)
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()
