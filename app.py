import os
import io
import json
import uuid
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from engine.analyzer import ForensicAnalyzer, compare_two_images
from engine.db import (
    init_db,
    get_investigations,
    get_investigation_by_id,
    delete_investigation,
    get_dashboard_stats
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
SAMPLES_DIR = os.path.join(BASE_DIR, "samples")
EVIDENCE_DIR = os.path.join(BASE_DIR, "evidence_store")

os.makedirs(EVIDENCE_DIR, exist_ok=True)
init_db()

app = FastAPI(
    title="VeriPix - Professional Digital Image Forensic Suite",
    description="Enterprise-grade digital image forensics, tampering detection, and evidence auditing toolkit",
    version="2.0.0"
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# In-memory session cache for latest analysis to avoid reprocessing for PDF generation
SESSION_ANALYZER = None

def validate_image_bytes(file_bytes: bytes, filename: str):
    """Validate image file size and magic bytes header."""
    max_size = 25 * 1024 * 1024 # 25 MB limit
    if len(file_bytes) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum permissible size of 25MB (Size: {len(file_bytes)/(1024*1024):.2f}MB)."
        )
    if len(file_bytes) < 32:
        raise HTTPException(status_code=400, detail="Uploaded file is too small or empty.")

    # Check magic byte signatures
    is_jpeg = file_bytes.startswith(b"\xFF\xD8\xFF")
    is_png = file_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    is_webp = len(file_bytes) > 12 and file_bytes[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP"
    is_bmp = file_bytes.startswith(b"BM")
    is_tiff = file_bytes.startswith(b"II*\x00") or file_bytes.startswith(b"MM\x00*")

    if not (is_jpeg or is_png or is_webp or is_bmp or is_tiff):
        raise HTTPException(
            status_code=400,
            detail="Unsupported or corrupted file format. Supported evidence formats: JPEG/JPG, PNG, WebP, TIFF, BMP."
        )

@app.get("/", response_class=HTMLResponse)
def index_page():
    """Render the primary Forensic Workbench UI."""
    index_file = os.path.join(TEMPLATES_DIR, "index.html")
    with open(index_file, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Handle browser favicon request cleanly."""
    return Response(status_code=204)

# ----------------- Dashboard & Database Endpoints -----------------

@app.get("/api/stats")
def fetch_dashboard_stats():
    """Fetch live statistical metrics from the SQLite database."""
    try:
        stats = get_dashboard_stats()
        return JSONResponse(content=stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}")

@app.get("/api/investigations")
def list_investigations(
    search: str = Query("", description="Search by filename, SHA-256 or ID"),
    status: str = Query("", description="Filter by status (POTENTIAL_ANOMALY, INCONCLUSIVE, NO_ANOMALY)"),
    limit: int = Query(50, description="Max records to return")
):
    """Retrieve historical investigation records with search and filter."""
    try:
        records = get_investigations(limit=limit, search=search, status_filter=status)
        return JSONResponse(content={"investigations": records, "count": len(records)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query investigations: {str(e)}")

@app.get("/api/investigations/{inv_id}")
def get_investigation_details(inv_id: str):
    """Retrieve full details of a specific past investigation."""
    global SESSION_ANALYZER
    record = get_investigation_by_id(inv_id)
    if not record:
        raise HTTPException(status_code=404, detail="Investigation record not found.")

    findings = record.get("findings", {})
    # Hydrate SESSION_ANALYZER if requested for PDF export
    SESSION_ANALYZER = type('DummyAnalyzer', (), {
        'filename': record.get('filename'),
        'results': findings,
        'investigation_id': inv_id,
        'generate_pdf': lambda case_id=None, examiner="Digital Forensics Unit": ForensicAnalyzer(
            b"", record.get('filename')
        ).generate_pdf(case_id or inv_id, examiner)
    })()

    return JSONResponse(content=record)

@app.delete("/api/investigations/{inv_id}")
def remove_investigation(inv_id: str):
    """Delete an investigation record from the database."""
    success = delete_investigation(inv_id)
    if not success:
        raise HTTPException(status_code=404, detail="Investigation not found or already deleted.")
    return JSONResponse(content={"deleted": True, "id": inv_id})

@app.get("/api/investigations/{inv_id}/json")
def export_investigation_json(inv_id: str):
    """Download structured JSON forensic audit log."""
    record = get_investigation_by_id(inv_id)
    if not record:
        raise HTTPException(status_code=404, detail="Investigation record not found.")

    clean_findings = record.get("findings", {})
    json_bytes = json.dumps(clean_findings, indent=4).encode("utf-8")
    filename = f"Forensic_Audit_{inv_id}.json"

    return StreamingResponse(
        io.BytesIO(json_bytes),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

# ----------------- Sample & Analysis Endpoints -----------------

@app.get("/api/samples")
def list_preset_samples():
    """List available preset sample images for demonstration."""
    sample_files = [
        {"id": "sample_authentic.jpg", "name": "Authentic Photograph", "desc": "Clean landscape capture with valid Canon EOS EXIF & GPS"},
        {"id": "sample_copy_move_forged.jpg", "name": "Copy-Move Cloning", "desc": "Hot air balloon cloned and duplicated in sky with matching noise"},
        {"id": "sample_spliced_tampered.jpg", "name": "Spliced Composite", "desc": "Foreign patch inserted + Adobe Photoshop software tag"},
        {"id": "sample_stego_hidden.png", "name": "Steganography LSB", "desc": "Covert data embedded into pixel Least Significant Bits (PoVs equalized)"},
        {"id": "sample_eof_carved.jpg", "name": "Hidden EOF Payload", "desc": "Secret ZIP archive appended past JPEG End-of-Image delimiter"}
    ]
    return JSONResponse(content={"samples": sample_files})

@app.get("/api/sample/{sample_id}")
def analyze_preset_sample(sample_id: str):
    """Analyze a preset sample image directly."""
    global SESSION_ANALYZER
    sample_path = os.path.join(SAMPLES_DIR, sample_id)
    if not os.path.exists(sample_path):
        raise HTTPException(status_code=404, detail="Sample not found.")

    with open(sample_path, "rb") as f:
        file_bytes = f.read()

    analyzer = ForensicAnalyzer(file_bytes, sample_id)
    results = analyzer.run_full_analysis(persist=True)
    SESSION_ANALYZER = analyzer

    return JSONResponse(content=results)

@app.post("/api/analyze")
def analyze_uploaded_image(
    file: UploadFile = File(...),
    ela_quality: int = Form(95),
    ela_scale: int = Form(25)
):
    """Analyze an uploaded suspect image with all forensic modules."""
    global SESSION_ANALYZER
    try:
        file_bytes = file.file.read()
        validate_image_bytes(file_bytes, file.filename or "suspect.jpg")

        # Save an evidence copy securely into evidence_store
        clean_fn = f"{uuid.uuid4().hex[:8]}_{os.path.basename(file.filename or 'suspect.jpg')}"
        evidence_path = os.path.join(EVIDENCE_DIR, clean_fn)
        with open(evidence_path, "wb") as ef:
            ef.write(file_bytes)

        analyzer = ForensicAnalyzer(file_bytes, file.filename or "uploaded_suspect.jpg")
        results = analyzer.run_full_analysis(ela_quality=ela_quality, ela_scale=ela_scale, persist=True)
        SESSION_ANALYZER = analyzer

        return JSONResponse(content=results)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forensic analysis failed: {str(e)}")

@app.post("/api/recompute-ela")
def recompute_ela_endpoint(
    quality: int = Form(95),
    scale_factor: int = Form(25)
):
    """Dynamically recompute ELA with user-adjusted sliders."""
    global SESSION_ANALYZER
    if not SESSION_ANALYZER or not hasattr(SESSION_ANALYZER, "recompute_ela"):
        raise HTTPException(status_code=400, detail="No active image analysis session.")

    try:
        ela_res = SESSION_ANALYZER.recompute_ela(quality=quality, scale_factor=scale_factor)
        return JSONResponse(content=ela_res)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ELA recomputation failed: {str(e)}")

@app.post("/api/compare")
def compare_images_endpoint(
    file1: UploadFile = File(...),
    file2: UploadFile = File(...)
):
    """
    Compare two suspect images for duplicates, visual similarity,
    cryptographic hash match, and pixel difference heatmap.
    """
    try:
        bytes1 = file1.file.read()
        bytes2 = file2.file.read()

        validate_image_bytes(bytes1, file1.filename)
        validate_image_bytes(bytes2, file2.filename)

        comparison_res = compare_two_images(
            bytes1, bytes2,
            name1=file1.filename or "image_1",
            name2=file2.filename or "image_2"
        )
        return JSONResponse(content=comparison_res)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image comparison failed: {str(e)}")

@app.post("/api/generate-report")
def download_pdf_report(
    case_id: str = Form(""),
    examiner: str = Form("Digital Forensics Unit")
):
    """Generate and stream official forensic PDF report."""
    global SESSION_ANALYZER
    if not SESSION_ANALYZER or not SESSION_ANALYZER.results:
        raise HTTPException(status_code=400, detail="No active image analysis available for report generation.")

    try:
        inv_id = case_id or getattr(SESSION_ANALYZER, "investigation_id", f"CASE-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
        pdf_bytes = SESSION_ANALYZER.generate_pdf(case_id=inv_id, examiner=examiner)
        filename = f"Forensic_Report_{getattr(SESSION_ANALYZER, 'filename', 'suspect')}.pdf"

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation error: {str(e)}")

def find_available_port(start_port=8000, max_port=8090):
    """Find a free TCP port starting from start_port."""
    import socket
    for port in range(start_port, max_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start_port

if __name__ == "__main__":
    import uvicorn
    import sys
    import webbrowser
    import threading
    import time

    sys.path.insert(0, BASE_DIR)
    os.chdir(BASE_DIR)

    port = find_available_port(8000)
    url = f"http://127.0.0.1:{port}"

    print(f"[*] Starting VeriPix Digital Forensic Server at {url}")
    print(f"[*] Working Directory: {BASE_DIR}")
    if port != 8000:
        print(f"[*] Note: Port 8000 was busy; automatically switched to port {port}.")

    # Automatically open browser after 1.5 seconds
    def open_browser():
        time.sleep(1.5)
        webbrowser.open(url)

    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(app, host="127.0.0.1", port=port)
